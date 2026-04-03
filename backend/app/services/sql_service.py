import asyncio
import logging
import re
from app.database import get_db
from app.services.tracing import get_traced_client

logger = logging.getLogger(__name__)

_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|EXECUTE|COPY|VACUUM|ANALYZE|COMMENT|SET|LOCK)\b",
    re.IGNORECASE,
)

DOCUMENTS_SCHEMA = """\
Table: documents
Columns:
  id          uuid
  user_id     uuid        -- ALWAYS filter: WHERE user_id = '$USER_ID'
  filename    text
  status      text        -- 'pending'|'processing'|'extracting'|'complete'|'error'
  size_bytes  int
  chunk_count int
  created_at  timestamptz
  metadata    jsonb       -- keys: document_type, topic, entity, year, quarter, language, summary

Rules:
  - ALWAYS include WHERE user_id = '$USER_ID' (literal placeholder, will be substituted)
  - SELECT only — no INSERT/UPDATE/DELETE/DDL
  - No semicolons
  - LIMIT added automatically if omitted (max 50)
  - JSONB access: metadata->>'entity'  or  (metadata->>'year')::int
"""


def _validate_sql(sql: str, user_id: str) -> str:
    """Validate SQL is safe to execute. Returns stripped SQL or raises ValueError."""
    stripped = sql.strip().rstrip(";")

    if not re.match(r"(?i)^\s*SELECT\b", stripped):
        raise ValueError(f"Generated SQL is not a SELECT statement: {stripped[:80]!r}")

    match = _BLOCKED_KEYWORDS.search(stripped)
    if match:
        raise ValueError(f"Blocked keyword '{match.group()}' found in generated SQL")

    if ";" in stripped:
        raise ValueError("Semicolons not allowed in generated SQL")

    if user_id not in stripped:
        raise ValueError(
            f"Generated SQL does not contain the required user_id filter ({user_id})"
        )

    return stripped


async def _generate_sql(question: str, user_id: str) -> str:
    """Ask LLM to write a SELECT SQL query. Returns empty string on failure."""
    client = get_traced_client()
    prompt = (
        f"You are a SQL expert. Generate a single SELECT query to answer the question.\n\n"
        f"Schema:\n{DOCUMENTS_SCHEMA}\n"
        f"User ID: {user_id}\n\n"
        f"Question: {question}\n\n"
        f"Return ONLY valid SQL. No markdown, no explanation, no backticks."
    )
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        return raw.strip()
    except Exception as exc:
        logger.warning(f"[sql_service] LLM SQL generation failed: {exc}")
        return ""


def _format_results(rows: list[dict]) -> str:
    """Format row dicts into a readable pipe-delimited table string."""
    if not rows:
        return "No results found."
    columns = list(rows[0].keys())
    lines = [" | ".join(columns), "-" * max(len(" | ".join(columns)), 10)]
    for row in rows:
        lines.append(" | ".join(str(row.get(col, "")) for col in columns))
    return "\n".join(lines)


async def query_documents_sql(question: str, user_id: str) -> str:
    """
    Generate SQL, validate, execute via Supabase RPC, return formatted result.
    Returns descriptive string on failure — never raises.
    """
    try:
        sql = await _generate_sql(question, user_id)
        if not sql:
            return "Could not generate a SQL query for this question."

        sql_with_id = sql.replace("$USER_ID", user_id)
        validated = _validate_sql(sql_with_id, user_id)

        db = get_db()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: db.rpc("execute_documents_query", {"query_sql": validated}).execute(),
        )
        rows: list[dict] = result.data if isinstance(result.data, list) else []
        return _format_results(rows)

    except ValueError as exc:
        logger.warning(f"[sql_service] SQL validation failed: {exc}")
        return f"SQL validation failed: {exc}"
    except Exception as exc:
        logger.warning(f"[sql_service] query_documents_sql error: {exc}")
        return ""
