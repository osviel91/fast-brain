import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException

from .config import settings
from .db import migrate
from .embeddings import embed
from .schemas import CompactIn, ConsolidateIn, MemoryIn, MemoryOut, MessageIn, SearchIn, SummarizerTestIn
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
from .summarizer import summarize_session

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


@app.get("/v1/config", dependencies=[Depends(require_auth)])
def get_config() -> dict[str, object]:
    return {
        "embeddings_dimensions": settings.embeddings_dimensions,
        "summarizer_configured": bool(settings.summarizer_base_url and settings.summarizer_model),
        "summarizer_base_url": settings.summarizer_base_url,
        "summarizer_model": settings.summarizer_model,
    }


@app.post("/v1/summarizer/test", dependencies=[Depends(require_auth)])
async def test_summarizer(request: SummarizerTestIn) -> dict[str, object]:
    messages = [{"id": 0, "role": "user", "content": request.text}]
    result = await summarize_session("summarizer-test", messages, request.max_chars)
    return result


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
    return await consolidate_one_session(session_id, request)


@app.post("/v1/compact", dependencies=[Depends(require_auth)])
async def compact(request: CompactIn) -> dict[str, object]:
    sessions = pending_sessions(request.agent_id, request.max_sessions)
    results = [await consolidate_one_session(session["session_id"], request) for session in sessions]
    return {"status": "compacted", "sessions": len(results), "results": results}


async def consolidate_one_session(session_id: str, request: ConsolidateIn) -> dict[str, object]:
    messages = unconsolidated_messages(session_id)
    if not messages:
        return {"status": "empty", "memory_id": None, "messages": 0}

    summary = await summarize_session(session_id, messages, request.max_chars)
    memory_ids = []
    for memory in summary["memories"]:
        content = memory["content"][: request.max_chars]
        memory_ids.append(
            save_memory(
                content,
                await embed(content),
                request.agent_id,
                session_id,
                memory.get("kind") or request.kind,
                {
                    "source": "consolidation",
                    "message_count": len(messages),
                    "mode": summary["mode"],
                    "error": summary["error"],
                },
            )
        )
    mark_consolidated([message["id"] for message in messages], memory_ids[0])
    return {
        "status": "consolidated",
        "session_id": session_id,
        "memory_ids": memory_ids,
        "mode": summary["mode"],
        "error": summary["error"],
        "messages": len(messages),
    }


@app.post("/v1/consolidate", dependencies=[Depends(require_auth)])
def consolidate() -> dict[str, str]:
    return {"status": "use /v1/consolidate/session/{session_id}"}


def run() -> None:
    uvicorn.run("fast_brain.main:app", host="0.0.0.0", port=8080)
