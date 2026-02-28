import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import io
import re
from database.db import init_db, get_all_schemas_text, safe_query, list_tables

st.set_page_config(page_title="AI Query Chat | ZERA Analytics", page_icon="💬", layout="wide")
init_db()

st.markdown("## 💬 AI Query Chat")
st.caption("Ask questions about your data in plain English — see the SQL, get downloadable results")
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
            schema_ctx = get_all_schemas_text()
            generated_sql = _generate_sql_from_question(question, schema_ctx)

            if generated_sql:
                st.markdown("#### 🔍 Generated SQL")
                st.code(generated_sql, language="sql")

                df_result, error = safe_query(generated_sql)
                if error:
                    st.error(error)
                    st.info("💡 Try rephrasing your question or use the SQL tab to write a query directly.")
                elif df_result is not None and len(df_result) > 0:
                    st.markdown(f"#### ✅ Results — {len(df_result):,} rows")
                    st.dataframe(df_result, use_container_width=True, hide_index=True, height=400)
                    _download_buttons(df_result, "ai_query_results")
                else:
                    st.info("Query returned no results. Try a different question.")

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
                if err:
                    st.error(err)
                elif df_r is not None and len(df_r) > 0:
                    st.dataframe(df_r, use_container_width=True, hide_index=True)
                    _download_buttons(df_r, f"quick_{i}")


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
            if error:
                st.error(error)
            elif df_result is not None and len(df_result) > 0:
                st.markdown(f"#### ✅ Results — {len(df_result):,} rows")
                st.dataframe(df_result, use_container_width=True, hide_index=True, height=400)
                _download_buttons(df_result, "direct_sql_results")
            else:
                st.info("Query returned no results.")


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def _generate_sql_from_question(question: str, schema: str) -> str:
    """Generate SQL from natural language using pattern matching + heuristics.
    This is a local rule-based engine — no external API needed."""

    q = question.lower().strip()

    # Detect target table
    table_map = {}
    for t in list_tables():
        table_map[t.lower()] = t
        # Also map partial names
        short = t.replace("purchase_", "").replace("meter_", "").replace("uploaded_", "")
        table_map[short] = t

    target_table = None
    for key, tname in sorted(table_map.items(), key=lambda x: -len(x[0])):
        if key in q:
            target_table = tname
            break

    # Fallback: guess from keywords
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

    # Detect intent
    limit = 20
    limit_match = re.search(r"top\s+(\d+)", q) or re.search(r"first\s+(\d+)", q) or re.search(r"limit\s+(\d+)", q)
    if limit_match:
        limit = int(limit_match.group(1))

    # Aggregation patterns
    if any(w in q for w in ["top", "most", "highest", "biggest", "largest"]):
        if "supplier" in q and "spend" in q or "amount" in q:
            val_col = "invoice_amount" if "india" in target_table or "packing" in target_table else "landed_cost" if "import" in target_table else "invoice_amount"
            return f"SELECT supplier, SUM({val_col}) as total_spend, COUNT(*) as orders\nFROM {target_table}\nWHERE supplier IS NOT NULL\nGROUP BY supplier\nORDER BY total_spend DESC\nLIMIT {limit}"

    if any(w in q for w in ["monthly", "trend", "over time", "by month"]):
        val_col = "invoice_amount" if "india" in target_table or "packing" in target_table else "landed_cost" if "import" in target_table else "invoice_amount"
        date_col = "purchase_date" if "purchase" in target_table else "event_datetime"
        return f"SELECT strftime('%Y-%m', {date_col}) as month, SUM({val_col}) as total, COUNT(*) as count\nFROM {target_table}\nWHERE {date_col} IS NOT NULL\nGROUP BY month\nORDER BY month"

    if any(w in q for w in ["count", "how many", "total number"]):
        if "by" in q:
            # Try to find grouping column
            group_col = None
            for candidate in ["supplier", "event_type", "event_action", "manufacturer", "total_evaluation", "item_description"]:
                if candidate in q:
                    group_col = candidate
                    break
            if group_col:
                return f"SELECT {group_col}, COUNT(*) as count\nFROM {target_table}\nGROUP BY {group_col}\nORDER BY count DESC"
        return f"SELECT COUNT(*) as total_count FROM {target_table}"

    if any(w in q for w in ["failed", "fail"]):
        if "meter" in target_table or "accuracy" in target_table:
            return f"SELECT * FROM meter_accuracy_test WHERE total_evaluation = 'fail'"

    if any(w in q for w in ["passed", "pass"]):
        if "meter" in target_table or "accuracy" in target_table:
            return f"SELECT * FROM meter_accuracy_test WHERE total_evaluation = 'pass'"

    if any(w in q for w in ["average", "avg", "mean"]):
        return f"SELECT * FROM {target_table} LIMIT 5"  # fallback

    if any(w in q for w in ["all", "everything", "show all", "list all"]):
        return f"SELECT * FROM {target_table} LIMIT 500"

    # Default: select with limit
    return f"SELECT * FROM {target_table} LIMIT {limit}"


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
