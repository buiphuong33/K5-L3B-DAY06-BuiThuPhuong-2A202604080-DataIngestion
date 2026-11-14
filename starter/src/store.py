"""PostgreSQL + pgvector store: stable IDs, no duplicates, SQL metadata filter."""
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .models import Chunk

ALLOWED_FILTERS = {"chapter", "document_id"}


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("invalid dimensions")
        self.url, self.dim = database_url, int(dimensions)

    def _conn(self):
        return psycopg.connect(self.url, connect_timeout=5)

    def create_schema(self) -> None:
        with self._conn() as c:
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    strategy    TEXT NOT NULL,
                    chunk_id    TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source      TEXT NOT NULL,
                    page        INT  NOT NULL,
                    chapter     TEXT,
                    text        TEXT NOT NULL,
                    embedding   vector({self.dim}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id))""")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        if any(len(v) != self.dim for v in vectors):
            raise ValueError("vector dimension mismatch")
        ids_by_doc: dict[str, list[str]] = {}
        for ch in chunks:
            ids_by_doc.setdefault(ch.document_id, []).append(ch.chunk_id)
        with self._conn() as c, c.cursor() as cur:
            for doc_id, ids in ids_by_doc.items():   # xóa chunk cũ không còn trong lần nạp này
                cur.execute("DELETE FROM chunks WHERE strategy=%s AND document_id=%s "
                            "AND NOT (chunk_id = ANY(%s))", (strategy, doc_id, ids))
            cur.executemany("""
                INSERT INTO chunks (strategy, chunk_id, document_id, source, page, chapter, text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                    document_id=EXCLUDED.document_id, source=EXCLUDED.source, page=EXCLUDED.page,
                    chapter=EXCLUDED.chapter, text=EXCLUDED.text, embedding=EXCLUDED.embedding""",
                [(strategy, ch.chunk_id, ch.document_id, ch.source, ch.page,
                  ch.metadata.get("chapter"), ch.text, _vec(v)) for ch, v in zip(chunks, vectors)])

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        where, params = ["strategy = %s"], [strategy]
        for key, value in (filters or {}).items():
            if key not in ALLOWED_FILTERS:
                raise ValueError(f"filter not allowed: {key}")
            where.append(f"{key} = %s")
            params.append(value)
        q = _vec(query_vector)
        sql = f"""SELECT chunk_id, document_id, source, page, chapter, text,
                         1 - (embedding <=> %s::vector) AS score
                  FROM chunks WHERE {' AND '.join(where)}
                  ORDER BY embedding <=> %s::vector LIMIT %s"""
        with self._conn() as c, c.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, [q, *params, q, top_k])
            return cur.fetchall()

    def count(self) -> dict[str, int]:
        with self._conn() as c:
            return dict(c.execute("SELECT strategy, COUNT(*) FROM chunks GROUP BY strategy").fetchall())
