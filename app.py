import streamlit as st
import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db
from modules.data_loader import load_all_procurement_data
from modules.pdf_parser import load_all_meter_data

st.set_page_config(
    page_title="ZERA Analytics Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem;}
    .sub-header {font-size: 1.1rem; color: #6c757d; margin-bottom: 1.5rem;}
    .metric-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem; border-radius: 12px; color: white; text-align: center;}
    .metric-value {font-size: 1.8rem; font-weight: 700;}
    .metric-label {font-size: 0.85rem; opacity: 0.9;}
    .stMetric > div {background: #f8f9fa; border-radius: 10px; padding: 12px; border-left: 4px solid #667eea;}
    div[data-testid="stSidebar"] {background-color: #f0f2f6;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading procurement data...")
def init_procurement():
    return load_all_procurement_data()

@st.cache_data(show_spinner="Parsing meter PDFs...")
def init_meter():
    return load_all_meter_data()


def main():
    # Sidebar
    st.sidebar.image("https://img.icons8.com/fluency/96/lightning-bolt.png", width=60)
    st.sidebar.markdown("### ⚡ ZERA Analytics")
    st.sidebar.markdown("*Intelligence Platform*")
    st.sidebar.divider()

    # Initialize data
    with st.spinner("Initializing database..."):
        init_db()
        proc_results = init_procurement()
        meter_results = init_meter()

    st.sidebar.success("Data loaded successfully!")
    st.sidebar.markdown("**Data Sources:**")
    for table, count in {**proc_results, **meter_results}.items():
        st.sidebar.caption(f"📊 {table}: {count} records")

    # Main page content
    st.markdown('<p class="main-header">⚡ ZERA Analytics Intelligence Platform</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Procurement Intelligence & Smart Meter Analytics for ZERA India Pvt. Ltd., Gandhinagar</p>', unsafe_allow_html=True)

    # Quick KPIs
    from modules.analytics import get_procurement_summary, get_meter_summary
    proc_kpis = get_procurement_summary()
    meter_kpis = get_meter_summary()

    st.markdown("### 📈 Executive Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Spend", f"₹{proc_kpis.get('grand_total_spend', 0):,.0f}")
    col2.metric("Line Items", f"{proc_kpis.get('total_line_items', 0):,}")
    col3.metric("Meters Tested", f"{meter_kpis.get('total_meters_tested', 0)}")
    col4.metric("Pass Rate", f"{meter_kpis.get('pass_rate', 0):.0f}%")
    col5.metric("Voltage Events", f"{meter_kpis.get('total_voltage_events', 0)}")

    st.divider()

    # Navigation cards
    st.markdown("### 🗂️ Navigate to Modules")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### 📊 Dashboard")
        st.caption("KPIs, spend overview, trend charts")
        st.page_link("pages/1_Dashboard.py", label="Open Dashboard →")
    with c2:
        st.markdown("#### 📦 Procurement")
        st.caption("Supplier analysis, cost breakdowns")
        st.page_link("pages/2_Procurement.py", label="Open Procurement →")
    with c3:
        st.markdown("#### ⚡ Meter Analytics")
        st.caption("Voltage events, meter health, anomaly detection")
        st.page_link("pages/3_Meter_Analytics.py", label="Open Meter Analytics →")
    with c4:
        st.markdown("#### 🤖 AI Insights")
        st.caption("ML predictions, risk scoring, forecasting")
        st.page_link("pages/4_AI_Insights.py", label="Open AI Insights →")

    st.divider()
    st.caption("Built by Vishvam | ZERA India Pvt. Ltd. Internship 2025-26 | Powered by Python, Streamlit, scikit-learn")


if __name__ == "__main__":
    main()
