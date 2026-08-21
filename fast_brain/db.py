from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from .config import settings


def connect():
    conn = psycopg.connect(settings.database_url, autocommit=True)
    register_vector(conn)
    return conn


def migrate() -> None:
    sql = Path("migrations/001_init.sql").read_text().replace(
        "__EMBEDDING_DIMENSIONS__", str(settings.embeddings_dimensions)
    )
    with connect() as conn:
        conn.execute(sql)
