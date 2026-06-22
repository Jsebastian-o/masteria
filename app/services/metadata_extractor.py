from __future__ import annotations

import json
import os
import re

from .sessions import ProjectMetadata
from .llm_service import client

_EXTRACTION_PROMPT = """\
You are a data extraction assistant. Read the conversation exchange below and extract software project facts.

Return a single JSON object with exactly these keys:
- "project_name": string or null
- "assumed_team_size": integer or null
- "mentioned_technologies": array of strings (names only, e.g. ["React", "FastAPI", "PostgreSQL"])
- "agreed_scope": string (one sentence summarising the agreed scope) or null

Rules:
- Only populate a field when the exchange provides explicit evidence.
- Prefer more specific or updated values over null; do not overwrite a known value with null.
- Current known facts are provided so you can extend them, not replace them.

Current known facts:
{current_json}

New exchange:
User: {transcript}
Assistant: {assistant_response}

Respond with only the JSON object. No markdown fences, no explanation."""


def extract_and_merge(
    current: ProjectMetadata,
    transcript: str,
    assistant_response: str,
) -> ProjectMetadata:
    prompt = _EXTRACTION_PROMPT.format(
        current_json=current.model_dump_json(),
        transcript=transcript,
        assistant_response=assistant_response,
    )

    response = client.messages.create(
        model=os.environ.get("LLM_MODEL"),
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

    updates: dict = json.loads(raw)

    return ProjectMetadata(
        project_name=updates.get("project_name") or current.project_name,
        assumed_team_size=updates.get("assumed_team_size") or current.assumed_team_size,
        mentioned_technologies=sorted({
            *current.mentioned_technologies,
            *(updates.get("mentioned_technologies") or []),
        }),
        agreed_scope=updates.get("agreed_scope") or current.agreed_scope,
    )
