"""Integration tests for the session-based estimation flow.

Each test uses httpx.AsyncClient with ASGITransport so the full ASGI stack
is exercised without a running server. External dependencies (Anthropic client,
metadata extractor) are mocked at their import-site names so the routing,
session management, and sliding-window logic run for real.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.main import app
from app.config import MAX_TURNS
from app.services.sessions import ProjectMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeStream:
    """Minimal sync context manager that mimics Anthropic's MessageStream."""

    def __init__(self, text: str = "Estimation: 10 person-days."):
        self._text = text

    def __enter__(self):
        self.text_stream = iter([self._text])
        return self

    def __exit__(self, *_):
        return False


def _fake_client(text: str = "Estimation: 10 person-days.", file_id: str = "file_test") -> MagicMock:
    """Return a pre-wired mock for app.routers.sessions.client."""
    mc = MagicMock()
    mc.beta.messages.stream.return_value = _FakeStream(text)
    mc.beta.files.upload.return_value = MagicMock(id=file_id)
    mc.beta.files.delete.return_value = None
    return mc


def _blank_metadata() -> ProjectMetadata:
    return ProjectMetadata()


def _parse(content: bytes) -> tuple[str, dict]:
    """Split b'<text>\\x00<json>' into (text, metadata_dict)."""
    text, meta_json = content.decode().split("\x00", 1)
    return text, json.loads(meta_json)


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


async def _post_estimate(
    client: httpx.AsyncClient,
    session_id: str,
    transcript: str,
    attachments: list[tuple] | None = None,
) -> httpx.Response:
    """Send a multipart /estimate request. Always forces multipart/form-data."""
    parts: list[tuple] = [("transcript", (None, transcript.encode(), "text/plain"))]
    if attachments:
        parts.extend(attachments)
    return await client.post(
        f"/api/v1/sessions/{session_id}/estimate",
        files=parts,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Test 1 – metadata accumulates correctly across two turns
# ---------------------------------------------------------------------------

async def test_metadata_accumulates_across_turns(http_client):
    """
    Turn 1 extracts a project name.
    Turn 2 adds technologies.
    Assert that the metadata at the end of turn 2 contains both facts,
    showing that extract_and_merge merges rather than replaces.
    """
    turn1_meta = ProjectMetadata(project_name="Acme Portal")
    turn2_meta = ProjectMetadata(
        project_name="Acme Portal",
        mentioned_technologies=["React", "FastAPI"],
    )

    with (
        patch("app.routers.sessions.client", _fake_client()),
        patch("app.routers.sessions.extract_and_merge") as mock_extract,
    ):
        mock_extract.side_effect = [turn1_meta, turn2_meta]

        r = await http_client.post("/api/v1/sessions")
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        # --- Turn 1 ---
        r1 = await _post_estimate(http_client, session_id, "We are building the Acme Portal.")
        assert r1.status_code == 200
        _, meta1 = _parse(r1.content)
        assert meta1["project_name"] == "Acme Portal"
        assert meta1["mentioned_technologies"] == []  # not yet extracted

        # --- Turn 2 ---
        r2 = await _post_estimate(http_client, session_id, "We will use React and FastAPI.")
        assert r2.status_code == 200
        _, meta2 = _parse(r2.content)
        # project_name preserved from turn 1
        assert meta2["project_name"] == "Acme Portal"
        # technologies added in turn 2
        assert "React" in meta2["mentioned_technologies"]
        assert "FastAPI" in meta2["mentioned_technologies"]

        assert mock_extract.call_count == 2


# ---------------------------------------------------------------------------
# Test 2 – PDF attachment is uploaded and referenced as a document block
# ---------------------------------------------------------------------------

async def test_pdf_attachment_forwarded_to_llm(http_client):
    """
    When a PDF is attached:
    - it must be uploaded via client.beta.files.upload
    - the resulting file_id must appear as a 'document' block in the
      messages list sent to the LLM
    - the file must be deleted afterwards (Files API cleanup)
    """
    file_id = "file_pdf_001"
    mock_client = _fake_client(file_id=file_id)

    captured_messages: list[list[dict]] = []

    def _capture_stream(*args, **kwargs):
        captured_messages.append(kwargs["messages"])
        return _FakeStream("Based on the spec, estimate is 20 days.")

    mock_client.beta.messages.stream.side_effect = _capture_stream

    with (
        patch("app.routers.sessions.client", mock_client),
        patch("app.routers.sessions.extract_and_merge", return_value=_blank_metadata()),
    ):
        r = await http_client.post("/api/v1/sessions")
        session_id = r.json()["session_id"]

        pdf_bytes = b"%PDF-1.4 1 0 obj<</Type/Catalog>>endobj"  # minimal valid-looking PDF
        r = await _post_estimate(
            http_client,
            session_id,
            transcript="Estimate based on the attached specification.",
            attachments=[("attachments", ("spec.pdf", pdf_bytes, "application/pdf"))],
        )
        assert r.status_code == 200

        # The file must have been uploaded exactly once
        mock_client.beta.files.upload.assert_called_once()
        upload_call = mock_client.beta.files.upload.call_args
        fname, _fobj, mime = upload_call.kwargs["file"]
        assert fname == "spec.pdf"
        assert mime == "application/pdf"

        # The file_id must appear as a document block in the user message
        assert len(captured_messages) == 1
        user_message = captured_messages[0][-1]
        assert user_message["role"] == "user"
        content_blocks: list[dict] = user_message["content"]
        doc_blocks = [b for b in content_blocks if b.get("type") == "document"]
        assert len(doc_blocks) == 1, "Expected exactly one document block"
        assert doc_blocks[0]["source"]["file_id"] == file_id

        # The file must be deleted after the response (cleanup in finally)
        mock_client.beta.files.delete.assert_called_once_with(file_id)


# ---------------------------------------------------------------------------
# Test 3 – 8 turns never exceed the MAX_TURNS sliding window
# ---------------------------------------------------------------------------

async def test_sliding_window_caps_history_at_max_turns(http_client):
    """
    After sending 8 turns to one session (MAX_TURNS = 6 by default):
    - The messages list passed to the LLM on each turn equals
      min(turn-1, MAX_TURNS)*2 + 1  (windowed history + current user).
    - From turn 7 onwards the list is capped at MAX_TURNS*2 + 1.
    - The oldest visible user message in the last turn is turn 3,
      confirming turns 1–2 were evicted.
    """
    mock_client = _fake_client()
    captured: list[list[dict]] = []

    def _capture(*args, **kwargs):
        captured.append(kwargs["messages"])
        return _FakeStream("OK.")

    mock_client.beta.messages.stream.side_effect = _capture

    with (
        patch("app.routers.sessions.client", mock_client),
        patch("app.routers.sessions.extract_and_merge", return_value=_blank_metadata()),
    ):
        r = await http_client.post("/api/v1/sessions")
        session_id = r.json()["session_id"]

        num_turns = 8
        for i in range(num_turns):
            resp = await _post_estimate(
                http_client, session_id, f"Turn {i + 1}: please estimate this feature."
            )
            assert resp.status_code == 200

    assert len(captured) == num_turns

    for i, msgs in enumerate(captured):
        turn = i + 1
        # windowed history = min(turns already stored, MAX_TURNS) * 2
        history_size = min((turn - 1), MAX_TURNS) * 2
        expected = history_size + 1  # + current user message
        assert len(msgs) == expected, (
            f"Turn {turn}: expected {expected} messages, got {len(msgs)}"
        )

    # From turn MAX_TURNS+1 onwards the total is always MAX_TURNS*2 + 1
    for msgs in captured[MAX_TURNS:]:
        assert len(msgs) == MAX_TURNS * 2 + 1

    # During the final call the history contains the MAX_TURNS pairs stored after
    # turns 1..(num_turns-1).  The oldest pair visible is from turn (num_turns-MAX_TURNS)
    # because eviction removes one pair per turn once the window is full.
    # Example: 8 turns, MAX_TURNS=6 → history during turn 8 = turns 2..7 → oldest = 2.
    last_history = captured[-1][:-1]  # all but the current user message
    first_user = next(m for m in last_history if m["role"] == "user")
    expected_oldest_turn = num_turns - MAX_TURNS  # = 2 for 8 turns, MAX_TURNS=6
    assert f"Turn {expected_oldest_turn}" in first_user["content"], (
        f"Expected oldest stored turn to be {expected_oldest_turn}, "
        f"got: {first_user['content']!r}"
    )
