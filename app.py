import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import init_db, list_tables, table_row_count

st.set_page_config(
    page_title="ZERA Analytics Intelligence Platform v2",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem;}
    .sub-header {font-size: 1.1rem; color: #6c757d; margin-bottom: 0.5rem;}
    .version-badge {
        display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 4px 14px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
        margin-left: 10px; vertical-align: middle;
    }
    .stMetric > div {background: #f8f9fa; border-radius: 10px; padding: 12px; border-left: 4px solid #667eea;}
    div[data-testid="stSidebar"] {background-color: #f0f2f6;}
</style>
""", unsafe_allow_html=True)


def ensure_db_ready():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True


def load_existing_data():
    from database.db import ensure_data_loaded
    ensure_data_loaded()


def handle_sidebar_upload(uploaded_file):
    import pandas as pd
    from database.db import upload_dataframe_to_db
    fname = uploaded_file.name
    table_name = os.path.splitext(fname)[0].lower().replace(" ", "_").replace("-", "_").replace(".", "_")[:50]
    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        n = upload_dataframe_to_db(df, f"uploaded_{table_name}")
        st.sidebar.success(f"✅ **{fname}** → `uploaded_{table_name}` ({n:,} rows)")
    except Exception as e:
        st.sidebar.error(f"Upload failed: {e}")


def main():
    # Sidebar
    st.sidebar.image("https://img.icons8.com/fluency/96/lightning-bolt.png", width=60)
    st.sidebar.markdown("### ⚡ ZERA Analytics")
    st.sidebar.markdown("*Intelligence Platform v2*")
    st.sidebar.divider()

    ensure_db_ready()

    # Data source selector
    st.sidebar.markdown("**📂 Data Source**")
    data_mode = st.sidebar.radio(
        "Choose:", ["📁 Bundled Data", "📤 Upload New", "🔄 Both"],
        index=0, label_visibility="collapsed"
    )

    if data_mode in ["📁 Bundled Data", "🔄 Both"]:
        load_existing_data()

    if data_mode in ["📤 Upload New", "🔄 Both"]:
        st.sidebar.markdown("---")
        uploaded = st.sidebar.file_uploader(
            "Upload Excel / CSV", type=["xlsx", "xls", "csv"],
            key="sidebar_upload", label_visibility="collapsed"
        )
        if uploaded:
            handle_sidebar_upload(uploaded)

    # Table status
    st.sidebar.divider()
    tables = list_tables()
    if tables:
        st.sidebar.success(f"✅ {len(tables)} tables loaded")
        with st.sidebar.expander("View tables"):
            for t in tables:
                try:
                    st.caption(f"📊 **{t}**: {table_row_count(t):,} rows")
                except:
                    st.caption(f"📊 {t}: (empty)")
    else:
        st.sidebar.info("No data loaded yet.")

    # ── MAIN PAGE ─────────────────────────────────────────────
    st.markdown(
        '<p class="main-header">⚡ ZERA Analytics Intelligence Platform'
        '<span class="version-badge">v2.0 Dynamic</span></p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">Procurement Intelligence & Smart Meter Analytics — ZERA India Pvt. Ltd., Gandhinagar</p>',
        unsafe_allow_html=True
    )

    # Executive KPIs
    if tables:
        try:
            from modules.analytics import get_procurement_summary, get_meter_summary
            proc = get_procurement_summary()
            meter = get_meter_summary()
            st.markdown("### 📈 Executive Overview")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Spend", f"₹{proc.get('grand_total_spend', 0):,.0f}")
            c2.metric("Line Items", f"{proc.get('total_line_items', 0):,}")
            c3.metric("Meters Tested", f"{meter.get('total_meters_tested', 0)}")
            c4.metric("Pass Rate", f"{meter.get('pass_rate', 0):.0f}%")
            c5.metric("Voltage Events", f"{meter.get('total_voltage_events', 0)}")
        except:
            pass

    st.divider()

    # Navigation cards — Row 1 (existing)
    st.markdown("### 🗂️ Navigate to Modules")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### 📊 Dashboard")
        st.caption("KPIs, spend overview, trend charts")
        st.page_link("pages/1_Dashboard.py", label="Open Dashboard →")
    with c2:
        st.markdown("#### 📦 Procurement")
        st.caption("Supplier analysis, cost breakdowns, filters & download")
        st.page_link("pages/2_Procurement.py", label="Open Procurement →")
    with c3:
        st.markdown("#### ⚡ Meter Analytics")
        st.caption("Voltage events, meter health, anomaly detection")
        st.page_link("pages/3_Meter_Analytics.py", label="Open Meter Analytics →")
    with c4:
        st.markdown("#### 🤖 AI Insights")
        st.caption("ML predictions, risk scoring, forecasting")
        st.page_link("pages/4_AI_Insights.py", label="Open AI Insights →")

    # Navigation cards — Row 2 (v2 new)
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown("#### 📤 Data Manager")
        st.caption("Upload files, filter, preview & download data")
        st.page_link("pages/5_Data_Manager.py", label="Open Data Manager →")
    with c6:
        st.markdown("#### 💬 AI Query Chat")
        st.caption("English → SQL → downloadable results")
        st.page_link("pages/6_AI_Query.py", label="Open AI Query →")
    with c7:
        st.markdown("#### 📉 Graph Builder")
        st.caption("Tableau-style chart builder")
        st.page_link("pages/7_Graph_Builder.py", label="Open Graph Builder →")
    with c8:
        st.markdown("#### 🏢 Company Hub")
        st.caption("Employee directory, HR section, blog")
        st.page_link("pages/8_Company_Hub.py", label="Open Company Hub →")

    st.divider()
    st.caption("Built by Vishvam | ZERA India Pvt. Ltd. Internship 2025-26 | v2.0 Dynamic — Python, Streamlit, scikit-learn")


if __name__ == "__main__":
    main()
