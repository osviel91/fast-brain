import json
from typing import Any

import httpx

from .config import settings


def extractive_summary(session_id: str, messages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    lines = [f"{message['role']}: {message['content']}" for message in messages]
    content = (f"Session {session_id} summary:\n" + "\n".join(lines))[:max_chars]
    return [{"kind": "summary", "content": content}]


async def summarize_session(session_id: str, messages: list[dict[str, Any]], max_chars: int) -> dict[str, Any]:
    if not (settings.summarizer_base_url and settings.summarizer_model):
        return {"mode": "fallback", "error": "summarizer not configured", "memories": extractive_summary(session_id, messages, max_chars)}

    transcript = "\n".join(f"{message['role']}: {message['content']}" for message in messages)[:max_chars]
    prompt = (
        "Extract durable memories from this Hermes conversation. "
        "Return only JSON: an array of objects with keys kind and content. "
        "Allowed kinds: project, decision, preference, task, fact, correction, summary. "
        "Skip trivial chatter, secrets, raw logs, and duplicates. Keep each content concise.\n\n"
        f"Session: {session_id}\n{transcript}"
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.summarizer_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.summarizer_api_key}"},
                json={
                    "model": settings.summarizer_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.removeprefix("json").strip()
        items = json.loads(text)
        memories = [item for item in items if item.get("content")]
        if memories:
            return {"mode": "summarizer", "error": "", "memories": memories}
        return {"mode": "fallback", "error": "summarizer returned no memories", "memories": extractive_summary(session_id, messages, max_chars)}
    except Exception as exc:
        return {"mode": "fallback", "error": str(exc), "memories": extractive_summary(session_id, messages, max_chars)}
