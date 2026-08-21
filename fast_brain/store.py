from typing import Any

from pgvector import Vector
from psycopg.types.json import Jsonb

from .db import connect


def save_message(session_id: str, role: str, content: str, agent_id: str, device_id: str | None) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, agent_id, device_id, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET updated_at = now()
            """,
            (session_id, agent_id, device_id),
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )


def save_memory(
    content: str,
    embedding: list[float],
    agent_id: str,
    session_id: str | None,
    kind: str,
    metadata: dict[str, Any],
) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO memories (content, embedding, agent_id, session_id, kind, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (content, Vector(embedding), agent_id, session_id, kind, Jsonb(metadata)),
        ).fetchone()
    return row[0]


def search_memories(query_embedding: list[float], agent_id: str, limit: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, content, kind, metadata, 1 - (embedding <=> %s) AS score
            FROM memories
            WHERE agent_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (Vector(query_embedding), agent_id, Vector(query_embedding), limit),
        ).fetchall()
    return [
        {"id": row[0], "content": row[1], "kind": row[2], "metadata": row[3], "score": row[4]}
        for row in rows
    ]


def recent_messages(session_id: str, limit: int = 20) -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]
