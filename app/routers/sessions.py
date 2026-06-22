import io
import os
import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..prompts.loader import render_session_system_prompt
from ..services.llm_service import client
from ..services.metadata_extractor import extract_and_merge
from ..services.sessions import Session, session_store

router = APIRouter(prefix="/api/v1")


class SessionResponse(BaseModel):
    session_id: str


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session() -> SessionResponse:
    session_id = str(uuid.uuid4())
    session_store.get_or_create(session_id)
    return SessionResponse(session_id=session_id)


@router.post("/sessions/{session_id}/estimate")
async def session_estimate(
    session_id: str,
    transcript: Annotated[str, Form()],
    attachments: Annotated[list[UploadFile], File()] = [],
) -> StreamingResponse:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Render system prompt with current metadata (empty block on first turn)
    system_prompt = render_session_system_prompt(session.metadata)

    # Upload each attachment to the Files API before streaming
    file_ids: list[tuple[str, str]] = []  # (file_id, mime_type)
    for upload in attachments:
        raw = await upload.read()
        mime = upload.content_type or "application/octet-stream"
        uploaded = client.beta.files.upload(
            file=(upload.filename or "attachment", io.BytesIO(raw), mime),
        )
        file_ids.append((uploaded.id, mime))

    return StreamingResponse(
        _stream(session, transcript, file_ids, system_prompt),
        media_type="text/plain",
    )


def _stream(
    session: Session,
    transcript: str,
    file_ids: list[tuple[str, str]],
    system_prompt: str,
) -> Generator[str, None, None]:
    content: list[dict] = [{"type": "text", "text": transcript}]
    for file_id, mime in file_ids:
        if mime.startswith("image/"):
            block: dict = {"type": "image", "source": {"type": "file", "file_id": file_id}}
        else:
            block = {"type": "document", "source": {"type": "file", "file_id": file_id}}
        content.append(block)

    messages = session.history.to_messages_list() + [{"role": "user", "content": content}]

    try:
        with client.beta.messages.stream(
            model=os.environ.get("LLM_MODEL"),
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            betas=["files-api-2025-04-14"],
        ) as stream:
            chunks: list[str] = []
            for text in stream.text_stream:
                chunks.append(text)
                yield text

        assistant_text = "".join(chunks)

        # Persist text-only history so future turns don't reference stale file_ids
        session.history.add("user", transcript)
        session.history.add("assistant", assistant_text)

        # Update project metadata (best-effort; a failure must not break the session)
        try:
            session.metadata = extract_and_merge(session.metadata, transcript, assistant_text)
        except Exception:
            pass

        # Trailing sentinel: client parses everything after \x00 as JSON metadata
        yield f"\x00{session.metadata.model_dump_json()}"
    finally:
        for file_id, _ in file_ids:
            try:
                client.beta.files.delete(file_id)
            except Exception:
                pass
