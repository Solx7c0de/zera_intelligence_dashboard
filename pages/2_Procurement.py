import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import pandas as pd
from database.db import query_df
from modules.analytics import get_supplier_analysis, get_monthly_spend

st.set_page_config(page_title="Procurement | ZERA Analytics", page_icon="📦", layout="wide")
st.markdown("## 📦 Procurement Deep Dive")
st.caption("Supplier analysis, cost breakdowns, and inventory tracking")
st.divider()

# Source selector
tab1, tab2, tab3, tab4 = st.tabs(["🌍 Foreign Imports", "🇮🇳 India Purchases", "📦 Packing Material", "👷 Labour Charges"])

with tab1:
    df = query_df("SELECT * FROM purchase_import")
    if len(df) > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Records", f"{len(df):,}")
        c2.metric("Total Value", f"₹{df['total_value_inr'].sum()/1e7:.2f} Cr")
        c3.metric("Landed Cost", f"₹{df['landed_cost'].sum()/1e7:.2f} Cr")
        c4.metric("Suppliers", f"{df['supplier'].nunique()}")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Supplier-wise Spend")
            sup = get_supplier_analysis("import")
            fig = px.treemap(sup.head(15), path=["supplier"], values="total_spend",
                           color="total_spend", color_continuous_scale="Blues")
            fig.update_layout(margin=dict(t=30, b=10), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Cost Breakdown (Import)")
            cost_components = pd.DataFrame({
                "Component": ["Base Value", "Freight", "Import Duty", "Custom Clearance", "Misc"],
                "Amount": [df["total_value_inr"].sum(), df["freight"].sum(), df["import_duty"].sum(),
                          df["custom_clearance"].sum(), df["misc_charges"].sum()]
            })
            fig = px.bar(cost_components, x="Component", y="Amount",
                        color="Component", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=20, b=20), height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Monthly trend
        st.markdown("#### Monthly Spend Trend")
        monthly = get_monthly_spend("import")
        if len(monthly) > 0:
            fig = px.area(monthly, x="month", y="landed_cost",
                         labels={"landed_cost": "Landed Cost (₹)", "month": "Month"},
                         color_discrete_sequence=["#667eea"])
            fig.update_layout(margin=dict(t=20, b=20), height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Searchable table
        st.markdown("#### Detailed Records")
        search = st.text_input("🔍 Search by supplier or item", key="imp_search")
        filtered = df
        if search:
            mask = df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
            filtered = df[mask]
        st.dataframe(filtered, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("No import purchase data loaded")

with tab2:
    df = query_df("SELECT * FROM purchase_india")
    if len(df) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Records", f"{len(df):,}")
        c2.metric("Total Value", f"₹{df['invoice_amount'].sum()/1e7:.2f} Cr")
        c3.metric("Suppliers", f"{df['supplier'].nunique()}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Top Suppliers")
            sup = get_supplier_analysis("india")
            if len(sup) > 0:
                fig = px.bar(sup.head(10), x="total_spend", y="supplier", orientation="h",
                           color_discrete_sequence=["#48bb78"])
                fig.update_layout(margin=dict(t=20, b=20), height=400, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.markdown("#### GST Breakdown")
            gst = pd.DataFrame({
                "Type": ["SGST", "CGST", "IGST"],
                "Amount": [df["sgst"].sum(), df["cgst"].sum(), df["igst"].sum()]
            })
            fig = px.pie(gst, values="Amount", names="Type", hole=0.4,
                        color_discrete_sequence=["#48bb78", "#38a169", "#276749"])
            fig.update_layout(margin=dict(t=20, b=20), height=400)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Detailed Records")
        search = st.text_input("🔍 Search", key="ind_search")
        filtered = df
        if search:
            mask = df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
            filtered = df[mask]
        st.dataframe(filtered, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("No India purchase data loaded")

with tab3:
    df = query_df("SELECT * FROM purchase_packing")
    if len(df) > 0:
        c1, c2 = st.columns(2)
        c1.metric("Records", f"{len(df):,}")
        c2.metric("Total Value", f"₹{df['invoice_amount'].sum()/1e6:.2f} L")
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("No packing data loaded")

with tab4:
    df = query_df("SELECT * FROM purchase_labour")
    if len(df) > 0:
        c1, c2 = st.columns(2)
        c1.metric("Records", f"{len(df):,}")
        c2.metric("Total Value", f"₹{df['invoice_amount'].sum()/1e6:.2f} L")
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("No labour data loaded")
