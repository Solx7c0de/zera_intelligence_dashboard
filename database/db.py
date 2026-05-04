import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text, inspect

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(PROJECT_ROOT, "database", "procurement.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


# ── INTERNAL HELPERS ──────────────────────────────────────────

def _quote_ident(name: str) -> str:
    """SQLite-safe identifier quoting (handles spaces, hyphens, reserved words)."""
    return '"' + str(name).replace('"', '""') + '"'


# ── CORE ──────────────────────────────────────────────────────

def init_db():
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    with engine.connect() as conn:
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def query_df(sql, params=None):
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def table_row_count(table_name):
    """Return row count for a table; returns -1 if the table can't be queried.

    Uses identifier quoting so names with spaces, hyphens, or reserved words
    don't blow up the SQL parser.
    """
    try:
        df = query_df(f"SELECT COUNT(*) as cnt FROM {_quote_ident(table_name)}")
        return int(df["cnt"].iloc[0])
    except Exception:
        return -1


def insert_df(df, table_name, if_exists="append"):
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)


# ── v2 ADDITIONS ──────────────────────────────────────────────

def list_tables():
    """Return list of all user table names (excludes sqlite_* internal tables)."""
    inspector = inspect(engine)
    return [t for t in inspector.get_table_names() if not t.startswith("sqlite_")]


def get_table_schema(table_name):
    """Return column names and types for a table. Empty list on error."""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return [(c["name"], str(c["type"])) for c in columns]
    except Exception:
        return []


def get_all_schemas_text():
    """Return a formatted string of all table schemas for AI prompting.

    Robust: never raises. A bad table shows '? rows' instead of crashing
    the caller (which would take down the whole AI Query page).
    """
    try:
        tables = list_tables()
    except Exception as e:
        return f"(unable to list tables: {e})"

    if not tables:
        return "(no tables loaded)"

    parts = []
    for t in tables:
        try:
            cols = get_table_schema(t)
            if not cols:
                parts.append(f"TABLE: {t} (schema unavailable)")
                continue
            col_strs = ", ".join(f"{name} ({dtype})" for name, dtype in cols)
            count = table_row_count(t)
            count_str = f"{count} rows" if count >= 0 else "? rows"
            parts.append(f"TABLE: {t} ({count_str})\n  Columns: {col_strs}")
        except Exception as e:
            parts.append(f"TABLE: {t} (error reading schema: {e})")
    return "\n\n".join(parts)


def safe_query(sql):
    """Execute a read-only SQL query. Blocks writes/drops."""
    sql_upper = sql.strip().upper()
    blocked = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "REPLACE", "TRUNCATE", "ATTACH"]
    for kw in blocked:
        if sql_upper.startswith(kw):
            return None, f"❌ Write operation blocked: {kw} not allowed in query mode."
    try:
        df = query_df(sql)
        return df, None
    except Exception as e:
        return None, f"❌ SQL Error: {e}"


def upload_dataframe_to_db(df, table_name, if_exists="replace"):
    """Upload a pandas DataFrame as a new table. Returns row count.

    Both column names AND the table name are sanitised so weird filenames
    (spaces, dots, hyphens) don't create un-queryable tables.
    """
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    safe_name = (
        str(table_name).strip().lower()
        .replace(" ", "_").replace("-", "_").replace(".", "_")
    )
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_").strip("_")
    if not safe_name:
        safe_name = "uploaded_table"
    if safe_name[0].isdigit():
        safe_name = "tbl_" + safe_name
    df.to_sql(safe_name, engine, if_exists=if_exists, index=False)
    return len(df)


# ── DATA LOAD ORCHESTRATION ───────────────────────────────────

EXPECTED_PROCUREMENT_TABLES = [
    "purchase_import",
    "purchase_india",
    "purchase_packing",
    "purchase_labour",
]


def _all_tables_populated(table_names):
    """True only if every table in the list has at least 1 row."""
    for t in table_names:
        if table_row_count(t) <= 0:
            return False
    return True


def ensure_data_loaded(force=False):
    """Call from any page — loads bundled data once per session.

    Self-healing: if the session flag is set but procurement tables are
    empty (i.e. the loader half-succeeded earlier), re-runs the loaders.
    Loader errors are surfaced as warnings instead of crashing the page.
    """
    import streamlit as st

    flag_set = st.session_state.get("bundled_data_loaded", False)
    if flag_set and not force and _all_tables_populated(EXPECTED_PROCUREMENT_TABLES):
        return

    try:
        init_db()
    except Exception as e:
        st.warning(f"Schema init issue: {e}")

    try:
        from modules.data_loader import load_all_procurement_data
        load_all_procurement_data()
    except Exception as e:
        st.warning(f"Procurement data load failed: {e}")

    try:
        from modules.pdf_parser import load_all_meter_data
        load_all_meter_data()
    except Exception as e:
        st.warning(f"Meter data load failed: {e}")

    st.session_state.bundled_data_loaded = True
