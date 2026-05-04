import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import io
from database.db import (
    ensure_data_loaded,
    get_all_schemas_text,
    safe_query,
    list_tables,
)
from modules.llm_query import (
    llm_available,
    llm_status_message,
    generate_sql,
    narrate_results,
)

st.set_page_config(page_title="AI Query Chat | ZERA Analytics", page_icon="💬", layout="wide")
ensure_data_loaded()


# ═══════════════════════════════════════════════════════════════
# HELPERS
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


def _render_results(df_result, sql, error, question, key_prefix, *, with_narration=False):
    """Shared result rendering for both natural-language and direct-SQL paths."""
    if error:
        st.error(error)
        return
    if df_result is None or len(df_result) == 0:
        st.info("Query returned no results.")
        return

    st.markdown(f"#### ✅ Results — {len(df_result):,} rows")
    st.dataframe(df_result, use_container_width=True, hide_index=True, height=400)
    _download_buttons(df_result, key_prefix)

    if with_narration and llm_available() and question:
        with st.expander("🧠 AI summary of these results", expanded=True):
            with st.spinner("Generating summary..."):
                summary = narrate_results(question, sql, df_result)
            if summary:
                st.markdown(summary)
            else:
                st.caption("Couldn't generate a summary for this result.")


# ═══════════════════════════════════════════════════════════════
# PAGE UI
# ═══════════════════════════════════════════════════════════════
st.markdown("## 💬 AI Query Chat")
st.caption("Ask questions about your data in plain English — see the SQL, get downloadable results")

# ── LLM STATUS BANNER (the green line) ────────────────────────
if llm_available():
    st.success(llm_status_message())
else:
    st.warning(llm_status_message())

st.divider()

# ═══════════════════════════════════════════════════════════════
# SCHEMA CONTEXT
# ═══════════════════════════════════════════════════════════════
tables = list_tables()
if not tables:
    st.warning("No data loaded. Go to the Home page or Data Manager to load data first.")
    st.stop()

with st.expander("🗄️ Available Database Schema", expanded=False):
    try:
        st.code(get_all_schemas_text(), language="sql")
    except Exception as e:
        st.error(f"Couldn't render schema: {e}")
        st.caption("Schema render failure shouldn't block queries — try the SQL tab.")

# ═══════════════════════════════════════════════════════════════
# QUERY INTERFACE — TWO MODES
# ═══════════════════════════════════════════════════════════════
tab_natural, tab_sql = st.tabs(["🗣️ Ask in English", "🔧 Write SQL Directly"])

# ── TAB 1: NATURAL LANGUAGE → SQL ─────────────────────────────
with tab_natural:
    st.markdown("#### Ask a question about your data")
    st.markdown("*Examples: 'Show top 5 suppliers by spend', 'Which meters failed?', 'Monthly purchase trend'*")

    question = st.text_area(
        "Your question:",
        placeholder="e.g., What are the top 10 suppliers by total invoice amount?",
        height=80, key="nl_question"
    )

    if st.button("🚀 Generate & Run Query", key="nl_run", type="primary"):
        if not question.strip():
            st.warning("Please type a question first.")
        else:
            with st.spinner("Generating SQL..."):
                generated_sql, mode, warning = generate_sql(question)

            mode_label = "🤖 LLM-generated" if mode == "llm" else "🧩 Pattern-matched"
            st.markdown(f"#### 🔍 Generated SQL  &nbsp;<small>({mode_label})</small>", unsafe_allow_html=True)
            st.code(generated_sql, language="sql")
            if warning:
                st.caption(f"⚠️ {warning}")

            df_result, error = safe_query(generated_sql)
            _render_results(
                df_result, generated_sql, error, question,
                key_prefix="ai_query_results",
                with_narration=True,
            )
            if error:
                st.info("💡 Try rephrasing or use the SQL tab to write a query directly.")

    # Quick query suggestions
    st.markdown("---")
    st.markdown("**💡 Quick queries:**")
    suggestions = [
        ("Top suppliers by spend", "SELECT supplier, SUM(invoice_amount) as total_spend, COUNT(*) as orders FROM purchase_india GROUP BY supplier ORDER BY total_spend DESC LIMIT 10"),
        ("Meter pass/fail summary", "SELECT total_evaluation, COUNT(*) as count FROM meter_accuracy_test GROUP BY total_evaluation"),
        ("Monthly purchase trend", "SELECT strftime('%Y-%m', purchase_date) as month, SUM(invoice_amount) as spend FROM purchase_india WHERE purchase_date IS NOT NULL GROUP BY month ORDER BY month"),
        ("Voltage event types", "SELECT event_type, event_action, COUNT(*) as count FROM meter_voltage_events GROUP BY event_type, event_action ORDER BY count DESC"),
        ("High-risk meters (tamper > 50)", "SELECT meter_serial, manufacturer, tamper_count, power_fail_count, total_evaluation FROM meter_accuracy_test WHERE tamper_count > 50"),
    ]

    cols = st.columns(3)
    for i, (label, sql) in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(f"📌 {label}", key=f"quick_{i}", use_container_width=True):
                st.session_state["direct_sql_input"] = sql
                st.markdown(f"**Query:** `{label}`")
                st.code(sql, language="sql")
                df_r, err = safe_query(sql)
                _render_results(
                    df_r, sql, err, label,
                    key_prefix=f"quick_{i}",
                    with_narration=False,
                )


# ── TAB 2: DIRECT SQL ─────────────────────────────────────────
with tab_sql:
    st.markdown("#### Write your own SQL query")
    st.markdown("*Read-only: SELECT queries only. DROP/DELETE/INSERT blocked for safety.*")

    default_sql = st.session_state.get("direct_sql_input", "SELECT * FROM purchase_india LIMIT 20")
    sql_input = st.text_area(
        "SQL Query:", value=default_sql, height=120, key="direct_sql"
    )

    if st.button("▶️ Execute", key="sql_run", type="primary"):
        if not sql_input.strip():
            st.warning("Enter a SQL query.")
        else:
            st.code(sql_input, language="sql")
            df_result, error = safe_query(sql_input)
            _render_results(
                df_result, sql_input, error, "",
                key_prefix="direct_sql_results",
                with_narration=False,
            )
