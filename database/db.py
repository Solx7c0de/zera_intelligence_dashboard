import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

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
