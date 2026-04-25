import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import io

from database.db import ensure_data_loaded, get_all_schemas_text, safe_query, list_tables
from modules.llm_query import (
    generate_sql,
    narrate_results,
    llm_available,
    DEFAULT_MODEL,
)

st.set_page_config(page_title="AI Query Chat | ZERA Analytics", page_icon="💬", layout="wide")

# Make sure data is loaded before any UI calls list_tables()
ensure_data_loaded()


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD BUTTONS HELPER (preserved from original)
# ═══════════════════════════════════════════════════════════════
def _download_buttons(df: pd.DataFrame, key_prefix: str):
    """Show CSV + Excel download buttons for a result dataframe."""
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ CSV", csv,
            file_name=f"{key_prefix}.csv", mime="text/csv",
            key=f"dl_csv_{key_prefix}", use_container_width=True
        )
    with col2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False)
        st.download_button(
            "⬇️ Excel", buf.getvalue(),
            file_name=f"{key_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_{key_prefix}", use_container_width=True
        )


def _run_and_render(sql: str, question: str, key_prefix: str, do_narrate: bool = True):
    """Execute SQL, render results table + downloads + (optional) AI narration."""
    df_result, error = safe_query(sql)
    if error:
        st.error(error)
        st.info("💡 Try rephrasing your question or use the SQL tab to write a query directly.")
        return None
    if df_result is None or len(df_result) == 0:
        st.info("Query returned no results. Try a different question or check the data.")
        return None

    st.markdown(f"#### ✅ Results — {len(df_result):,} rows")
    st.dataframe(df_result, use_container_width=True, hide_index=True, height=400)
    _download_buttons(df_result, key_prefix)

    # AI narration of the results (Tier 2 feature)
    if do_narrate and llm_available():
        with st.spinner("📝 Summarizing results..."):
            narration = narrate_results(question, sql, df_result)
        if narration:
            st.markdown("#### 🧠 AI Summary")
            st.info(narration)

    return df_result


# ═══════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("## 💬 AI Query Chat")
st.caption("Ask questions about your data in plain English — see the SQL, get downloadable results")

# LLM status badge
if llm_available():
    st.success(
        f"🤖 AI mode active — powered by Google Gemini ({DEFAULT_MODEL}). "
        f"Ask anything in natural language."
    )
else:
    st.warning(
        "⚙️ Pattern-matching mode (no Gemini API key found). "
        "Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` or as an environment "
        "variable to unlock full AI mode. See README for setup."
    )

st.divider()

# ═══════════════════════════════════════════════════════════════
# SCHEMA CONTEXT
# ═══════════════════════════════════════════════════════════════
tables = list_tables()
if not tables:
    st.warning("No data loaded. Go to the Home page or Data Manager to load data first.")
    st.stop()

with st.expander("🗄️ Available Database Schema", expanded=False):
    st.code(get_all_schemas_text(), language="sql")


# ═══════════════════════════════════════════════════════════════
# QUERY INTERFACE — TWO MODES (preserved)
# ═══════════════════════════════════════════════════════════════
tab_natural, tab_sql = st.tabs(["🗣️ Ask in English", "🔧 Write SQL Directly"])

# ── TAB 1: NATURAL LANGUAGE → SQL ─────────────────────────────
with tab_natural:
    st.markdown("#### Ask a question about your data")
    if llm_available():
        st.markdown(
            "*Ask anything — the AI understands your schema. Try: "
            "'Which 5 suppliers had biggest spending growth between Q2 and Q3?', "
            "'What's the average tamper count per manufacturer for failed meters?', "
            "'Show months where total spend exceeded ₹2 crore.'*"
        )
    else:
        st.markdown(
            "*Examples: 'Show top 5 suppliers by spend', 'Which meters failed?', "
            "'Monthly purchase trend'*"
        )

    question = st.text_area(
        "Your question:",
        placeholder="e.g., What are the top 10 suppliers by total invoice amount?",
        height=90, key="nl_question"
    )

    col_run, col_clear = st.columns([5, 1])
    with col_run:
        run_clicked = st.button(
            "🚀 Generate & Run Query", key="nl_run",
            type="primary", use_container_width=True
        )
    with col_clear:
        if st.button("🔄 Clear", key="nl_clear", use_container_width=True):
            for k in ["last_nl_sql", "last_nl_question", "last_nl_mode"]:
                st.session_state.pop(k, None)
            st.rerun()

    if run_clicked:
        if not question.strip():
            st.warning("Please type a question first.")
        else:
            spinner_msg = "🤖 Thinking..." if llm_available() else "⚙️ Building query..."
            with st.spinner(spinner_msg):
                generated_sql, mode, warning = generate_sql(question)

            if warning:
                st.warning(f"⚠️ {warning}")

            if generated_sql:
                st.session_state["last_nl_sql"] = generated_sql
                st.session_state["last_nl_question"] = question
                st.session_state["last_nl_mode"] = mode

                badge = "🤖 LLM" if mode == "llm" else "⚙️ Pattern matcher"
                st.markdown(f"#### 🔍 Generated SQL  &nbsp; *({badge})*")
                st.code(generated_sql, language="sql")
                _run_and_render(generated_sql, question, "ai_query_results")

    # Quick query suggestions (preserved + 1 extra)
    st.markdown("---")
    st.markdown("**💡 Quick queries:**")
    suggestions = [
        ("Top suppliers by spend",
         "SELECT supplier, SUM(invoice_amount) as total_spend, COUNT(*) as orders "
         "FROM purchase_india GROUP BY supplier ORDER BY total_spend DESC LIMIT 10"),
        ("Meter pass/fail summary",
         "SELECT total_evaluation, COUNT(*) as count "
         "FROM meter_accuracy_test GROUP BY total_evaluation"),
        ("Monthly purchase trend",
         "SELECT strftime('%Y-%m', purchase_date) as month, "
         "SUM(invoice_amount) as spend FROM purchase_india "
         "WHERE purchase_date IS NOT NULL GROUP BY month ORDER BY month"),
        ("Voltage event types",
         "SELECT event_type, event_action, COUNT(*) as count "
         "FROM meter_voltage_events GROUP BY event_type, event_action ORDER BY count DESC"),
        ("High-risk meters (tamper > 50)",
         "SELECT meter_serial, manufacturer, tamper_count, power_fail_count, total_evaluation "
         "FROM meter_accuracy_test WHERE tamper_count > 50"),
        ("Top items by quantity",
         "SELECT item_description, SUM(quantity) as total_qty, COUNT(*) as orders "
         "FROM purchase_india GROUP BY item_description ORDER BY total_qty DESC LIMIT 15"),
    ]

    cols = st.columns(3)
    for i, (label, sql) in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(f"📌 {label}", key=f"quick_{i}", use_container_width=True):
                st.session_state["direct_sql_input"] = sql
                st.markdown(f"**Query:** `{label}`")
                st.code(sql, language="sql")
                _run_and_render(sql, label, f"quick_{i}", do_narrate=llm_available())


# ── TAB 2: DIRECT SQL (preserved, with optional AI summary) ───
with tab_sql:
    st.markdown("#### Write your own SQL query")
    st.markdown("*Read-only: SELECT queries only. DROP/DELETE/INSERT blocked for safety.*")

    default_sql = st.session_state.get("direct_sql_input", "SELECT * FROM purchase_india LIMIT 20")
    sql_input = st.text_area(
        "SQL Query:", value=default_sql, height=140, key="direct_sql"
    )

    col_exec, col_narrate = st.columns([4, 2])
    with col_exec:
        exec_clicked = st.button(
            "▶️ Execute", key="sql_run",
            type="primary", use_container_width=True
        )
    with col_narrate:
        ai_summary_for_sql = st.checkbox(
            "🧠 AI summary",
            value=llm_available(),
            disabled=not llm_available(),
            help="Generate a plain-English summary of the query results "
                 "(requires Gemini API key).",
            key="sql_narrate_toggle",
        )

    if exec_clicked:
        if not sql_input.strip():
            st.warning("Enter a SQL query.")
        else:
            st.code(sql_input, language="sql")
            _run_and_render(
                sql_input,
                question="(direct SQL)",
                key_prefix="direct_sql_results",
                do_narrate=ai_summary_for_sql,
            )
