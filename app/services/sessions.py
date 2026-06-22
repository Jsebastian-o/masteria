from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from ..config import MAX_TURNS


class ProjectMetadata(BaseModel):
    project_name: str = ""
    assumed_team_size: Optional[int] = None
    mentioned_technologies: list[str] = Field(default_factory=list)
    agreed_scope: str = ""


class ConversationHistory:
    """Sliding-window turn history.

    Invariant: _messages always contains complete user+assistant pairs,
    never more than max_turns of them.
    """

    def __init__(self, max_turns: int = MAX_TURNS) -> None:
        self._max_turns = max_turns
        self._messages: list[dict] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})
        self._evict()

    def _evict(self) -> None:
        # Only evict when a complete pair has just been committed (even count).
        # This prevents cutting a pair in half between the two add() calls.
        if len(self._messages) % 2 != 0:
            return
        while len(self._messages) > self._max_turns * 2:
            del self._messages[:2]  # drop oldest complete pair

    def to_messages_list(self) -> list[dict]:
        """Return a copy of the windowed history ready to pass to the LLM API.

        The system prompt is managed separately (pass via system= kwarg so that
        the caller can regenerate it from the latest ProjectMetadata each turn).
        """
        return list(self._messages)

    def __len__(self) -> int:
        return len(self._messages)


class Session:
    def __init__(self, session_id: str, max_turns: int = MAX_TURNS) -> None:
        self.session_id = session_id
        self.history = ConversationHistory(max_turns=max_turns)
        self.metadata = ProjectMetadata()


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str, max_turns: int = MAX_TURNS) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id, max_turns=max_turns)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._sessions)


# Process-level singleton
session_store = SessionStore()
