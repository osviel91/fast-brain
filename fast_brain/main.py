import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException

from .config import settings
from .db import migrate
from .embeddings import embed
from .schemas import ConsolidateIn, MemoryIn, MemoryOut, MessageIn, SearchIn
from .store import (
    delete_memory,
    mark_consolidated,
    pending_sessions,
    recent_messages,
    save_memory,
    save_message,
    search_memories,
    stats,
    unconsolidated_messages,
)

app = FastAPI(title="fast-brain", version="0.1.0")


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_key:
        return
    if authorization != f"Bearer {settings.api_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.on_event("startup")
def startup() -> None:
    migrate()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/stats", dependencies=[Depends(require_auth)])
def get_stats(agent_id: str = "hermes") -> dict[str, int]:
    return stats(agent_id)


@app.get("/v1/consolidate/pending", dependencies=[Depends(require_auth)])
def get_pending(agent_id: str = "hermes", limit: int = 20) -> dict[str, object]:
    return {"sessions": pending_sessions(agent_id, limit)}


@app.post("/v1/messages", dependencies=[Depends(require_auth)])
def add_message(message: MessageIn) -> dict[str, str]:
    save_message(message.session_id, message.role, message.content, message.agent_id, message.device_id)
    return {"status": "stored"}


@app.get("/v1/sessions/{session_id}/recent", dependencies=[Depends(require_auth)])
def get_recent(session_id: str, limit: int = 20) -> dict[str, object]:
    return {"messages": recent_messages(session_id, limit)}


@app.post("/v1/memories", dependencies=[Depends(require_auth)])
async def remember(memory: MemoryIn) -> dict[str, int]:
    memory_id = save_memory(
        memory.content,
        await embed(memory.content),
        memory.agent_id,
        memory.session_id,
        memory.kind,
        memory.metadata,
    )
    return {"id": memory_id}


@app.post("/v1/search", response_model=list[MemoryOut], dependencies=[Depends(require_auth)])
async def search(search_input: SearchIn) -> list[dict[str, object]]:
    return search_memories(await embed(search_input.query), search_input.agent_id, search_input.limit)


@app.delete("/v1/memories/{memory_id}", dependencies=[Depends(require_auth)])
def forget(memory_id: int, agent_id: str = "hermes") -> dict[str, object]:
    return {"deleted": delete_memory(memory_id, agent_id)}


@app.post("/v1/consolidate/session/{session_id}", dependencies=[Depends(require_auth)])
async def consolidate_session(session_id: str, request: ConsolidateIn) -> dict[str, object]:
    messages = unconsolidated_messages(session_id)
    if not messages:
        return {"status": "empty", "memory_id": None, "messages": 0}

    lines = [f"{message['role']}: {message['content']}" for message in messages]
    content = f"Session {session_id} summary:\n" + "\n".join(lines)
    content = content[: request.max_chars]
    memory_id = save_memory(
        content,
        await embed(content),
        request.agent_id,
        session_id,
        request.kind,
        {"source": "consolidation", "message_count": len(messages)},
    )
    mark_consolidated([message["id"] for message in messages], memory_id)
    return {"status": "consolidated", "memory_id": memory_id, "messages": len(messages)}


@app.post("/v1/consolidate", dependencies=[Depends(require_auth)])
def consolidate() -> dict[str, str]:
    return {"status": "use /v1/consolidate/session/{session_id}"}


def run() -> None:
    uvicorn.run("fast_brain.main:app", host="0.0.0.0", port=8080)
