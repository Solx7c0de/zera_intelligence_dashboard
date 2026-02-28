import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text, inspect

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(PROJECT_ROOT, "database", "procurement.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


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
    df = query_df(f"SELECT COUNT(*) as cnt FROM {table_name}")
    return df["cnt"].iloc[0]


def insert_df(df, table_name, if_exists="append"):
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)


# ── v2 ADDITIONS ──────────────────────────────────────────────

def list_tables():
    """Return list of all table names in the database."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def get_table_schema(table_name):
    """Return column names and types for a table."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return [(c["name"], str(c["type"])) for c in columns]


def get_all_schemas_text():
    """Return a formatted string of all table schemas for AI prompting."""
    tables = list_tables()
    parts = []
    for t in tables:
        cols = get_table_schema(t)
        col_strs = ", ".join(f"{name} ({dtype})" for name, dtype in cols)
        count = table_row_count(t)
        parts.append(f"TABLE: {t} ({count} rows)\n  Columns: {col_strs}")
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
    """Upload a pandas DataFrame as a new table. Returns row count."""
    # Clean column names for SQL compatibility
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    return len(df)
