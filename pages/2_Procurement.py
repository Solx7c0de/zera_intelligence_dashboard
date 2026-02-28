import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import pandas as pd
import io
from database.db import query_df, init_db
from modules.analytics import get_supplier_analysis, get_monthly_spend

st.set_page_config(page_title="Procurement | ZERA Analytics", page_icon="📦", layout="wide")
init_db()

st.markdown("## 📦 Procurement Deep Dive")
st.caption("Supplier analysis, cost breakdowns, inventory tracking — with filters & download")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🌍 Foreign Imports", "🇮🇳 India Purchases", "📦 Packing Material", "👷 Labour Charges"])


def _render_procurement_tab(table_name, value_col, label, tab_key):
    """Reusable renderer for each procurement tab with filters & download."""
    df = query_df(f"SELECT * FROM {table_name}")
    if len(df) == 0:
        st.warning(f"No {label} data loaded")
        return

    # ── FILTERS ───────────────────────────────────────────────
    with st.expander("🎛️ Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            suppliers = sorted(df["supplier"].dropna().unique().tolist())
            selected_sup = st.multiselect(
                "🏢 Supplier", suppliers, key=f"sup_{tab_key}",
                placeholder="All suppliers"
            )
        with fc2:
            if "purchase_date" in df.columns:
                df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
                valid_dates = df["purchase_date"].dropna()
                if len(valid_dates) > 0:
                    min_d = valid_dates.min().date()
                    max_d = valid_dates.max().date()
                    date_range = st.date_input(
                        "📅 Date Range", value=(min_d, max_d),
                        min_value=min_d, max_value=max_d, key=f"date_{tab_key}"
                    )
                else:
                    date_range = None
            else:
                date_range = None
        with fc3:
            if "item_description" in df.columns:
                search_item = st.text_input("🔍 Search item", key=f"item_{tab_key}")
            else:
                search_item = ""

    # Apply filters
    filtered = df.copy()
    if selected_sup:
        filtered = filtered[filtered["supplier"].isin(selected_sup)]
    if date_range and len(date_range) == 2 and "purchase_date" in filtered.columns:
        filtered = filtered[
            (filtered["purchase_date"] >= pd.Timestamp(date_range[0])) &
            (filtered["purchase_date"] <= pd.Timestamp(date_range[1]))
        ]
    if search_item:
        filtered = filtered[filtered["item_description"].astype(str).str.contains(search_item, case=False, na=False)]

    # ── KPIs ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records", f"{len(filtered):,}")
    c2.metric("Total Value", f"₹{filtered[value_col].sum():,.0f}")
    c3.metric("Suppliers", f"{filtered['supplier'].nunique()}")
    c4.metric("Avg Order", f"₹{filtered[value_col].mean():,.0f}" if len(filtered) > 0 else "—")

    st.divider()

    # ── CHARTS ────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Supplier-wise Spend")
        sup_spend = (
            filtered.groupby("supplier")[value_col]
            .sum().reset_index()
            .sort_values(value_col, ascending=False).head(15)
        )
        if len(sup_spend) > 0:
            fig = px.treemap(sup_spend, path=["supplier"], values=value_col,
                           color=value_col, color_continuous_scale="Blues")
            fig.update_layout(margin=dict(t=30, b=10), height=400)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Monthly Trend")
        if "purchase_date" in filtered.columns:
            monthly = filtered.dropna(subset=["purchase_date"]).copy()
            monthly["month"] = monthly["purchase_date"].dt.to_period("M").astype(str)
            m_agg = monthly.groupby("month")[value_col].sum().reset_index().sort_values("month")
            if len(m_agg) > 0:
                fig = px.area(m_agg, x="month", y=value_col,
                             color_discrete_sequence=["#667eea"])
                fig.update_layout(margin=dict(t=20, b=20), height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No date data for trend")

    # ── DATA TABLE ────────────────────────────────────────────
    st.markdown(f"#### Detailed Records ({len(filtered):,} rows)")
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=400)

    # ── DOWNLOAD ──────────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    with dl1:
        csv = filtered.to_csv(index=False).encode()
        st.download_button(f"⬇️ Download {label} CSV", csv,
                         file_name=f"{table_name}_filtered.csv", mime="text/csv",
                         key=f"dl_csv_{tab_key}", use_container_width=True)
    with dl2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            filtered.to_excel(w, index=False)
        st.download_button(f"⬇️ Download {label} Excel", buf.getvalue(),
                         file_name=f"{table_name}_filtered.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         key=f"dl_xlsx_{tab_key}", use_container_width=True)


with tab1:
    _render_procurement_tab("purchase_import", "landed_cost", "Import", "imp")

with tab2:
    _render_procurement_tab("purchase_india", "invoice_amount", "India", "ind")

with tab3:
    _render_procurement_tab("purchase_packing", "invoice_amount", "Packing", "pack")

with tab4:
    _render_procurement_tab("purchase_labour", "invoice_amount", "Labour", "lab")
