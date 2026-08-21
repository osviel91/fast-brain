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
        if session_id:
            conn.execute(
                """
                INSERT INTO sessions (id, agent_id, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE SET updated_at = now()
                """,
                (session_id, agent_id),
            )
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


def delete_memory(memory_id: int, agent_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "DELETE FROM memories WHERE id = %s AND agent_id = %s RETURNING id",
            (memory_id, agent_id),
        ).fetchone()
    return row is not None


def stats(agent_id: str = "hermes") -> dict[str, int]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                (SELECT count(*) FROM sessions WHERE agent_id = %s),
                (SELECT count(*) FROM messages m JOIN sessions s ON s.id = m.session_id WHERE s.agent_id = %s),
                (SELECT count(*) FROM messages m JOIN sessions s ON s.id = m.session_id WHERE s.agent_id = %s AND m.consolidated_at IS NULL),
                (SELECT count(*) FROM memories WHERE agent_id = %s)
            """,
            (agent_id, agent_id, agent_id, agent_id),
        ).fetchone()
    return {"sessions": row[0], "messages": row[1], "unconsolidated_messages": row[2], "memories": row[3]}


def pending_sessions(agent_id: str = "hermes", limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT s.id, count(m.id), min(m.created_at), max(m.created_at)
            FROM sessions s
            JOIN messages m ON m.session_id = s.id
            WHERE s.agent_id = %s AND m.consolidated_at IS NULL
            GROUP BY s.id
            ORDER BY max(m.created_at)
            LIMIT %s
            """,
            (agent_id, limit),
        ).fetchall()
    return [
        {"session_id": row[0], "unconsolidated_messages": row[1], "first_message_at": row[2], "last_message_at": row[3]}
        for row in rows
    ]


def unconsolidated_messages(session_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content
            FROM messages
            WHERE session_id = %s AND consolidated_at IS NULL
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
    return [{"id": row[0], "role": row[1], "content": row[2]} for row in rows]


def mark_consolidated(message_ids: list[int], memory_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE messages SET consolidated_at = now(), consolidation_memory_id = %s WHERE id = ANY(%s)",
            (memory_id, message_ids),
        )


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
