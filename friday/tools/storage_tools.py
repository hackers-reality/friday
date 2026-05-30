from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

# ──────────────────────────────────────────────
# Dataclass results
# ──────────────────────────────────────────────

@dataclass
class SupabaseResult:
    """Result from a Supabase database query."""
    table: str
    rows: list[dict]
    count: int = 0
    error: Optional[str] = None


@dataclass
class QdrantResult:
    """Result from a Qdrant vector similarity search."""
    collection: str
    results: list[dict]
    error: Optional[str] = None


@dataclass
class E2BResult:
    """Result from E2B sandboxed code execution."""
    language: str
    stdout: str
    stderr: str
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Lazy dependency flags
# ──────────────────────────────────────────────

HAS_SUPABASE = False
try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    pass

HAS_QDRANT = False
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter as QdrantFilter
    HAS_QDRANT = True
except ImportError:
    pass

HAS_E2B = False
try:
    from e2b_code_interpreter import CodeInterpreter
    HAS_E2B = True
except ImportError:
    pass


# ──────────────────────────────────────────────
# Supabase — PostgreSQL-as-a-Service (free 500 MB)
# ──────────────────────────────────────────────

async def supabase_query(
    table: str,
    select: str = "*",
    eq: dict | None = None,
    limit: int = 10,
) -> SupabaseResult:
    """Query a Supabase table.

    Requires ``SUPABASE_URL`` and ``SUPABASE_KEY`` environment variables.
    Supabase offers a free tier with 500 MB database size.

    Args:
        table: Name of the table to query.
        select: Columns to return (default ``"*"``).
        eq: Optional equality filters as ``{column: value}``.
        limit: Maximum number of rows to return (default 10).

    Returns:
        A ``SupabaseResult`` containing the matching rows.
    """
    if not HAS_SUPABASE:
        return SupabaseResult(
            table=table, rows=[], count=0,
            error="supabase package not installed (pip install supabase)",
        )

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return SupabaseResult(
            table=table, rows=[], count=0,
            error="SUPABASE_URL and SUPABASE_KEY environment variables must be set",
        )

    def _blocking() -> SupabaseResult:
        try:
            client = create_client(url, key)
            query = client.table(table).select(select)
            if eq:
                for col, val in eq.items():
                    query = query.eq(col, val)
            query = query.limit(limit)
            resp = query.execute()
            rows = resp.data or []
            return SupabaseResult(table=table, rows=rows, count=len(rows))
        except Exception as exc:
            return SupabaseResult(table=table, rows=[], count=0, error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# Qdrant — vector similarity search (free 1 GB)
# ──────────────────────────────────────────────

async def qdrant_search(
    collection: str,
    query: str,
    limit: int = 5,
) -> QdrantResult:
    """Semantic search over a Qdrant vector collection.

    Requires ``QDRANT_URL`` and ``QDRANT_API_KEY`` environment variables.
    Qdrant Cloud free tier includes 1 GB of storage.

    This function embeds the query string using a lightweight local
    sentence-transformer model (all-MiniLM-L6-v2) before searching.

    Args:
        collection: Name of the Qdrant collection.
        query: Free-text search query.
        limit: Number of top results to return (default 5).

    Returns:
        A ``QdrantResult`` with scored results.  Each result dict
        contains ``"text"``, ``"score"``, and ``"metadata"`` keys.
    """
    if not HAS_QDRANT:
        return QdrantResult(
            collection=collection, results=[],
            error="qdrant-client package not installed (pip install qdrant-client)",
        )

    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    if not url or not api_key:
        return QdrantResult(
            collection=collection, results=[],
            error="QDRANT_URL and QDRANT_API_KEY environment variables must be set",
        )

    HAS_SENTENCE_TF = False
    try:
        from sentence_transformers import SentenceTransformer
        HAS_SENTENCE_TF = True
    except ImportError:
        pass

    def _blocking() -> QdrantResult:
        try:
            if not HAS_SENTENCE_TF:
                return QdrantResult(
                    collection=collection, results=[],
                    error="sentence-transformers not installed (pip install sentence-transformers)",
                )

            model = SentenceTransformer("all-MiniLM-L6-v2")
            vector = model.encode(query).tolist()

            client = QdrantClient(url=url, api_key=api_key)
            hits = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=limit,
            )
            results = []
            for hit in hits:
                payload = hit.payload or {}
                results.append({
                    "text": payload.get("text", ""),
                    "score": round(hit.score, 4),
                    "metadata": {k: v for k, v in payload.items() if k != "text"},
                })
            return QdrantResult(collection=collection, results=results)
        except Exception as exc:
            return QdrantResult(collection=collection, results=[], error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# E2B — secure cloud code execution ($100 free credits)
# ──────────────────────────────────────────────

async def e2b_execute_code(code: str, language: str = "python") -> E2BResult:
    """Execute arbitrary code in an E2B cloud sandbox.

    Requires the ``E2B_API_KEY`` environment variable.  New accounts
    receive $100 in free credits.  The sandbox is ephemeral and
    auto-closes after execution.

    Args:
        code: Source code to execute.
        language: Language identifier (default ``"python"``).

    Returns:
        An ``E2BResult`` with captured stdout / stderr.
    """
    if not HAS_E2B:
        return E2BResult(
            language=language, stdout="", stderr="",
            error="e2b-code-interpreter package not installed (pip install e2b-code-interpreter)",
        )

    api_key = os.environ.get("E2B_API_KEY")
    if not api_key:
        return E2BResult(
            language=language, stdout="", stderr="",
            error="E2B_API_KEY environment variable not set",
        )

    def _blocking() -> E2BResult:
        try:
            with CodeInterpreter(api_key=api_key) as interpreter:
                result = interpreter.notebook.exec_cell(code)
            stdout = "\n".join(result.logs.stdout) if result.logs else ""
            stderr = "\n".join(result.logs.stderr) if result.logs else ""
            return E2BResult(language=language, stdout=stdout, stderr=stderr)
        except Exception as exc:
            return E2BResult(language=language, stdout="", stderr="", error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)
