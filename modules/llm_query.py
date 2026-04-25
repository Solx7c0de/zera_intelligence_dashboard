"""
LLM-powered natural language to SQL helper for the AI Query page.

Uses Google's Gemini API (free tier) to:
  1. Convert plain-English questions into SQLite-compatible SELECT queries
  2. Narrate the result of those queries in plain English

Falls back to the legacy pattern matcher if no API key is configured, so
deployments without a key still function.
"""

from __future__ import annotations

import os
import re
import pandas as pd

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RESULT_ROWS_FOR_NARRATION = 50
SAMPLE_ROWS_PER_TABLE = 3


# ─────────────────────────────────────────────────────────────────────
# CLIENT INITIALIZATION (lazy, cached)
# ─────────────────────────────────────────────────────────────────────
_client = None
_client_error: str | None = None


def _get_api_key() -> str | None:
    """Look for the Gemini API key in Streamlit secrets, then env vars."""
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_client():
    """Return a configured google-genai client, or None if unavailable."""
    global _client, _client_error
    if _client is not None:
        return _client
    if _client_error is not None:
        return None

    api_key = _get_api_key()
    if not api_key:
        _client_error = "No GEMINI_API_KEY found in st.secrets or environment."
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        return _client
    except ImportError:
        _client_error = "google-genai package not installed. Run: pip install google-genai"
        return None
    except Exception as e:
        _client_error = f"Failed to initialize Gemini client: {e}"
        return None


def llm_available() -> bool:
    """Quick check used by the UI to decide which mode to advertise."""
    return get_client() is not None


def llm_status_message() -> str:
    """Human-readable status for the UI."""
    if llm_available():
        return f"✅ Gemini ({DEFAULT_MODEL}) is configured and ready."
    return f"⚠️ LLM unavailable — {_client_error}. Falling back to pattern matcher."


# ─────────────────────────────────────────────────────────────────────
# SAMPLE DATA HELPERS — gives the LLM a peek at real values
# ─────────────────────────────────────────────────────────────────────
def _get_sample_rows(table_name: str, n: int = SAMPLE_ROWS_PER_TABLE) -> str:
    """Return a few sample rows as a tab-separated string for prompt context."""
    try:
        from database.db import query_df
        df = query_df(f"SELECT * FROM {table_name} LIMIT {n}")
        if df.empty:
            return "(no sample data)"
        return df.to_string(index=False, max_cols=20, max_colwidth=30)
    except Exception:
        return "(could not fetch samples)"


def _build_schema_with_samples() -> str:
    """Combine schema text with a few sample rows per table for richer context."""
    try:
        from database.db import list_tables, get_table_schema, table_row_count
    except Exception:
        return ""

    parts = []
    for t in list_tables():
        try:
            cols = get_table_schema(t)
            count = table_row_count(t)
            col_strs = ", ".join(f"{name} ({dtype})" for name, dtype in cols)
            samples = _get_sample_rows(t)
            parts.append(
                f"TABLE: {t} ({count} rows)\n"
                f"  Columns: {col_strs}\n"
                f"  Sample rows:\n{samples}"
            )
        except Exception:
            continue
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# SQL VALIDATION — defense-in-depth on top of safe_query
# ─────────────────────────────────────────────────────────────────────
_FORBIDDEN_PATTERNS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bREPLACE\b", r"\bTRUNCATE\b",
    r"\bATTACH\b", r"\bDETACH\b", r"\bPRAGMA\b",
]


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```sql ... ``` or ``` ... ```)."""
    text = text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text)
    return text.strip().rstrip(";").strip()


def _is_safe_select(sql: str) -> tuple[bool, str]:
    """Return (is_safe, reason). Only allow SELECT/WITH single-statement queries."""
    if not sql:
        return False, "Empty query."
    if ";" in sql.rstrip(";"):
        return False, "Multiple statements not allowed."
    upper = sql.upper().lstrip()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False, "Only SELECT/WITH queries are allowed."
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, sql, flags=re.IGNORECASE):
            return False, f"Disallowed keyword detected ({pat})."
    return True, ""


# ─────────────────────────────────────────────────────────────────────
# CORE: NATURAL LANGUAGE → SQL
# ─────────────────────────────────────────────────────────────────────
_SQL_SYSTEM_PROMPT = """You are an expert SQL assistant for a SQLite database.

Your job: convert the user's plain-English question into a single, valid, READ-ONLY SQLite SELECT query.

STRICT RULES:
1. Output ONLY the SQL — no explanation, no markdown, no preamble.
2. Use ONLY tables and columns that appear in the schema below.
3. The query MUST start with SELECT or WITH.
4. NEVER use DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, REPLACE, TRUNCATE, ATTACH, or PRAGMA.
5. Date columns (purchase_date, event_datetime) are stored as ISO-format strings like '2023-04-01 00:00:00.000000'.
   Use strftime('%Y-%m', purchase_date) for monthly grouping, strftime('%Y', purchase_date) for yearly, etc.
   Use date(purchase_date) to convert to a clean date.
6. Always add a sensible LIMIT (default 100, max 1000) unless the user explicitly asks for aggregate counts.
7. Use clear column aliases (e.g., AS total_spend, AS month, AS supplier_count).
8. For "top N" queries, use ORDER BY ... DESC LIMIT N.
9. If the question is ambiguous, make a reasonable interpretation and proceed.
10. Prefer GROUP BY + aggregation for "by", "per", "breakdown" questions.

SCHEMA AND SAMPLE DATA:
{schema}

USER QUESTION:
{question}

SQL:"""


def generate_sql_with_llm(question: str) -> tuple[str | None, str | None]:
    """
    Convert NL question to SQL via Gemini.
    Returns (sql, error). On success error is None.
    """
    client = get_client()
    if client is None:
        return None, _client_error or "LLM client unavailable."

    schema_with_samples = _build_schema_with_samples()
    if not schema_with_samples:
        return None, "Could not build schema context — is data loaded?"

    prompt = _SQL_SYSTEM_PROMPT.format(schema=schema_with_samples, question=question)

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
        )
        raw = (response.text or "").strip()
    except Exception as e:
        return None, f"Gemini API error: {e}"

    sql = _strip_code_fences(raw)
    is_safe, reason = _is_safe_select(sql)
    if not is_safe:
        return None, f"Generated SQL rejected: {reason}\n\nLLM output was:\n{raw}"

    return sql, None


# ─────────────────────────────────────────────────────────────────────
# CORE: RESULT NARRATION
# ─────────────────────────────────────────────────────────────────────
_NARRATE_PROMPT = """You are a data analyst summarizing query results for a business user.

The user asked: "{question}"

The SQL query that ran:
{sql}

Results ({n_rows} rows total, showing first {shown}):
{results}

Write a brief, clear, business-oriented summary of the findings (3-5 sentences max).
- Lead with the most important takeaway.
- Mention specific numbers, names, or trends where relevant.
- Use Indian rupee format (₹) for monetary values when applicable.
- Do not repeat the SQL or schema in your answer.
- Do not use markdown headers; plain prose with light bullet points only if needed.
"""


def narrate_results(question: str, sql: str, df: pd.DataFrame) -> str | None:
    """
    Ask Gemini to summarize the result dataframe in plain English.
    Returns the narration string, or None on failure.
    """
    client = get_client()
    if client is None or df is None or df.empty:
        return None

    n_rows = len(df)
    shown = min(n_rows, MAX_RESULT_ROWS_FOR_NARRATION)
    sample = df.head(shown).to_string(index=False, max_cols=15, max_colwidth=40)

    prompt = _NARRATE_PROMPT.format(
        question=question, sql=sql, n_rows=n_rows, shown=shown, results=sample,
    )
    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
        )
        return (response.text or "").strip() or None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────
# LEGACY PATTERN MATCHER — preserved as fallback
# ─────────────────────────────────────────────────────────────────────
def generate_sql_with_pattern_matcher(question: str) -> str:
    """
    Original heuristic-based SQL generator. Used when LLM is unavailable.
    Kept verbatim from the original implementation so behavior is unchanged.
    """
    from database.db import list_tables

    q = question.lower().strip()

    table_map = {}
    for t in list_tables():
        table_map[t.lower()] = t
        short = t.replace("purchase_", "").replace("meter_", "").replace("uploaded_", "")
        table_map[short] = t

    target_table = None
    for key, tname in sorted(table_map.items(), key=lambda x: -len(x[0])):
        if key in q:
            target_table = tname
            break

    if not target_table:
        if any(w in q for w in ["supplier", "purchase", "spend", "invoice", "procurement", "buy", "cost"]):
            target_table = "purchase_india"
        elif any(w in q for w in ["meter", "voltage", "tamper", "power fail", "accuracy", "test"]):
            if "voltage" in q:
                target_table = "meter_voltage_events"
            elif "power" in q:
                target_table = "meter_power_events"
            elif "transaction" in q:
                target_table = "meter_transaction_events"
            else:
                target_table = "meter_accuracy_test"
        elif any(w in q for w in ["packing", "material"]):
            target_table = "purchase_packing"
        elif any(w in q for w in ["labour", "labor"]):
            target_table = "purchase_labour"
        elif any(w in q for w in ["import", "foreign"]):
            target_table = "purchase_import"
        else:
            target_table = list_tables()[0] if list_tables() else "purchase_india"

    limit = 20
    limit_match = re.search(r"top\s+(\d+)", q) or re.search(r"first\s+(\d+)", q) or re.search(r"limit\s+(\d+)", q)
    if limit_match:
        limit = int(limit_match.group(1))

    if any(w in q for w in ["top", "most", "highest", "biggest", "largest"]):
        if "supplier" in q and ("spend" in q or "amount" in q):
            val_col = "invoice_amount" if "india" in target_table or "packing" in target_table else "landed_cost" if "import" in target_table else "invoice_amount"
            return f"SELECT supplier, SUM({val_col}) as total_spend, COUNT(*) as orders\nFROM {target_table}\nWHERE supplier IS NOT NULL\nGROUP BY supplier\nORDER BY total_spend DESC\nLIMIT {limit}"

    if any(w in q for w in ["monthly", "trend", "over time", "by month"]):
        val_col = "invoice_amount" if "india" in target_table or "packing" in target_table else "landed_cost" if "import" in target_table else "invoice_amount"
        date_col = "purchase_date" if "purchase" in target_table else "event_datetime"
        return f"SELECT strftime('%Y-%m', {date_col}) as month, SUM({val_col}) as total, COUNT(*) as count\nFROM {target_table}\nWHERE {date_col} IS NOT NULL\nGROUP BY month\nORDER BY month"

    if any(w in q for w in ["count", "how many", "total number"]):
        if "by" in q:
            for candidate in ["supplier", "event_type", "event_action", "manufacturer", "total_evaluation", "item_description"]:
                if candidate in q:
                    return f"SELECT {candidate}, COUNT(*) as count\nFROM {target_table}\nGROUP BY {candidate}\nORDER BY count DESC"
        return f"SELECT COUNT(*) as total_count FROM {target_table}"

    if any(w in q for w in ["failed", "fail"]):
        if "meter" in target_table or "accuracy" in target_table:
            return "SELECT * FROM meter_accuracy_test WHERE total_evaluation = 'fail'"

    if any(w in q for w in ["passed", "pass"]):
        if "meter" in target_table or "accuracy" in target_table:
            return "SELECT * FROM meter_accuracy_test WHERE total_evaluation = 'pass'"

    if any(w in q for w in ["all", "everything", "show all", "list all"]):
        return f"SELECT * FROM {target_table} LIMIT 500"

    return f"SELECT * FROM {target_table} LIMIT {limit}"


# ─────────────────────────────────────────────────────────────────────
# UNIFIED ENTRY POINT — used by the page
# ─────────────────────────────────────────────────────────────────────
def generate_sql(question: str) -> tuple[str, str, str | None]:
    """
    Best-effort SQL generation. Tries LLM first, falls back to pattern matcher.

    Returns: (sql, mode, warning)
      mode: 'llm' or 'pattern'
      warning: optional warning string (e.g. why LLM was skipped), else None
    """
    if llm_available():
        sql, err = generate_sql_with_llm(question)
        if sql:
            return sql, "llm", None
        # LLM failed — fall through to pattern matcher with a warning
        return generate_sql_with_pattern_matcher(question), "pattern", err

    return generate_sql_with_pattern_matcher(question), "pattern", _client_error
