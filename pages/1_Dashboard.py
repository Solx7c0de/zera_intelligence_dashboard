import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import plotly.graph_objects as go
from modules.analytics import get_procurement_summary, get_meter_summary, get_supplier_analysis, get_monthly_spend
from database.db import query_df

st.set_page_config(page_title="Dashboard | ZERA Analytics", page_icon="📊", layout="wide")
st.markdown("## 📊 Executive Dashboard")
st.caption("Procurement & Meter Testing Overview — ZERA India Pvt. Ltd.")
st.divider()

# KPIs
proc = get_procurement_summary()
meter = get_meter_summary()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Spend", f"₹{proc.get('grand_total_spend',0)/1e7:.2f} Cr")
c2.metric("Import Spend", f"₹{proc.get('total_import_landed',0)/1e7:.2f} Cr")
c3.metric("India Spend", f"₹{proc.get('total_india_value',0)/1e7:.2f} Cr")
c4.metric("Line Items", f"{proc.get('total_line_items',0):,}")
c5.metric("Meters Tested", f"{meter.get('total_meters_tested',0)}")
c6.metric("Pass Rate", f"{meter.get('pass_rate',0):.0f}%")

st.divider()

# Row 1: Spend split + Monthly trend
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Spend Distribution")
    spend_data = {
        "Category": ["Foreign Import", "India Domestic", "Packing Material", "Labour Charges"],
        "Amount": [
            proc.get("total_import_landed", 0),
            proc.get("total_india_value", 0),
            proc.get("total_packing_value", 0),
            proc.get("total_labour_value", 0),
        ]
    }
    fig = px.pie(spend_data, values="Amount", names="Category",
                 color_discrete_sequence=px.colors.qualitative.Set2,
                 hole=0.4)
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("#### Monthly Import Spend Trend")
    monthly = get_monthly_spend("import")
    if len(monthly) > 0:
        fig = px.bar(monthly, x="month", y="landed_cost",
                     labels={"landed_cost": "Landed Cost (₹)", "month": "Month"},
                     color_discrete_sequence=["#667eea"])
        fig.update_layout(margin=dict(t=20, b=20), height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly data available")

# Row 2: Top Suppliers + Meter comparison
col3, col4 = st.columns(2)

with col3:
    st.markdown("#### Top 10 Import Suppliers by Spend")
    suppliers = get_supplier_analysis("import")
    if len(suppliers) > 0:
        top10 = suppliers.head(10)
        fig = px.bar(top10, x="total_spend", y="supplier", orientation="h",
                     color="total_spend", color_continuous_scale="Viridis",
                     labels={"total_spend": "Total Spend (₹)", "supplier": ""})
        fig.update_layout(margin=dict(t=20, b=20, l=20), height=400, showlegend=False,
                         yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.markdown("#### Meter Test Results — Session 13")
    meters = query_df("SELECT meter_serial, manufacturer, total_evaluation, tamper_count, power_fail_count FROM meter_accuracy_test")
    if len(meters) > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Tamper Count", x=meters["meter_serial"], y=meters["tamper_count"], marker_color="#667eea"))
        fig.add_trace(go.Bar(name="Power Failures", x=meters["meter_serial"], y=meters["power_fail_count"], marker_color="#f093fb"))
        fig.update_layout(barmode="group", margin=dict(t=20, b=20), height=400,
                         xaxis_title="Meter Serial", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

        # Pass/Fail table
        st.dataframe(meters, use_container_width=True, hide_index=True)

        # Download
        csv_meters = meters.to_csv(index=False).encode()
        st.download_button("⬇️ Download Meter Data (CSV)", csv_meters,
                         file_name="meter_test_results.csv", mime="text/csv")

st.divider()
st.caption("Data Source: Purchase-Stock-2023-24 Excel + ZERA Meter Test PDFs | Session 13, Jan 2026 | v2.0 Dynamic")
