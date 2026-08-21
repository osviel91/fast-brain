from typing import Any, Literal

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    session_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    agent_id: str = "hermes"
    device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryIn(BaseModel):
    content: str
    agent_id: str = "hermes"
    session_id: str | None = None
    kind: str = "fact"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchIn(BaseModel):
    query: str
    agent_id: str = "hermes"
    limit: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.25, ge=-1, le=1)


class ConsolidateIn(BaseModel):
    agent_id: str = "hermes"
    kind: str = "summary"
    max_chars: int = Field(default=3000, ge=500, le=12000)


class CompactIn(ConsolidateIn):
    max_sessions: int = Field(default=10, ge=1, le=100)


class SummarizerTestIn(BaseModel):
    text: str
    max_chars: int = Field(default=3000, ge=100, le=12000)


class ContextIn(BaseModel):
    query: str
    agent_id: str = "hermes"
    session_id: str | None = None
    max_chars: int = Field(default=12000, ge=1000, le=64000)
    memory_limit: int = Field(default=5, ge=1, le=20)
    recent_limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.25, ge=-1, le=1)


class MemoryOut(BaseModel):
    id: int
    content: str
    kind: str
    score: float | None = None
    metadata: dict[str, Any]
