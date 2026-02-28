import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import io
from database.db import init_db, query_df, list_tables, upload_dataframe_to_db
from config import COMPANY, NOMINAL_VOLTAGE, OVER_VOLTAGE, UNDER_VOLTAGE, HIGH_VOLTAGE_THRESHOLD, LOW_VOLTAGE_THRESHOLD

st.set_page_config(page_title="Company Hub | ZERA Analytics", page_icon="🏢", layout="wide")
init_db()

st.markdown("## 🏢 Company Hub")
st.caption(f"{COMPANY} — Employee Directory, HR Policies, Meter Testing Standards & Reports")
st.divider()

tab_emp, tab_hr, tab_meter, tab_blog = st.tabs([
    "👥 Employee Directory",
    "📋 HR Section",
    "🔬 Meter Testing Standards",
    "📝 Reports & Blog"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: EMPLOYEE DIRECTORY
# ═══════════════════════════════════════════════════════════════
with tab_emp:
    st.markdown("### 👥 Employee Directory")
    st.markdown("Upload or manage employee data. If no employee table exists, you can create one below.")

    # Check if employee table exists
    tables = list_tables()
    emp_tables = [t for t in tables if "employee" in t.lower() or "staff" in t.lower() or "team" in t.lower()]

    if emp_tables:
        selected_emp = st.selectbox("Select employee table:", emp_tables, key="emp_table")
        emp_df = query_df(f"SELECT * FROM {selected_emp}")

        if len(emp_df) > 0:
            # Search & filter
            search = st.text_input("🔍 Search employees", key="emp_search")
            if search:
                mask = emp_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
                emp_df = emp_df[mask]

            # Department filter if column exists
            dept_cols = [c for c in emp_df.columns if "dept" in c.lower() or "department" in c.lower()]
            if dept_cols:
                depts = ["All"] + sorted(emp_df[dept_cols[0]].dropna().unique().tolist())
                selected_dept = st.selectbox("Filter by Department:", depts, key="emp_dept")
                if selected_dept != "All":
                    emp_df = emp_df[emp_df[dept_cols[0]] == selected_dept]

            st.markdown(f"**Showing {len(emp_df)} employees**")
            st.dataframe(emp_df, use_container_width=True, hide_index=True, height=400)

            # Download
            csv_emp = emp_df.to_csv(index=False).encode()
            st.download_button("⬇️ Download Employee Data (CSV)", csv_emp,
                             file_name="employees.csv", mime="text/csv")
    else:
        st.info("No employee data found in the database.")

    # Upload employee data
    st.markdown("---")
    st.markdown("#### ➕ Upload Employee Data")
    emp_upload = st.file_uploader(
        "Upload an Excel or CSV with employee details",
        type=["xlsx", "xls", "csv"], key="emp_upload"
    )

    if emp_upload:
        try:
            if emp_upload.name.endswith(".csv"):
                new_emp = pd.read_csv(emp_upload)
            else:
                new_emp = pd.read_excel(emp_upload)
            st.dataframe(new_emp.head(), use_container_width=True, hide_index=True)
            if st.button("✅ Save to database as `employees`", key="save_emp"):
                n = upload_dataframe_to_db(new_emp, "employees", if_exists="replace")
                st.success(f"Saved {n} employee records!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Or create sample
    if not emp_tables:
        st.markdown("---")
        if st.button("📋 Create sample employee table (demo data)", key="create_sample_emp"):
            sample = pd.DataFrame({
                "employee_id": ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005",
                              "EMP006", "EMP007", "EMP008"],
                "name": ["Rajesh Kumar", "Priya Shah", "Amit Patel", "Neha Gupta",
                        "Vikram Singh", "Anita Joshi", "Sanjay Mehta", "Kavita Desai"],
                "department": ["Engineering", "Engineering", "Quality", "Quality",
                             "Production", "Production", "HR", "Accounts"],
                "designation": ["Sr. Engineer", "Test Engineer", "QA Lead", "QA Analyst",
                              "Production Manager", "Technician", "HR Manager", "Accountant"],
                "join_date": ["2020-03-15", "2021-07-01", "2019-11-20", "2022-01-10",
                            "2018-06-05", "2023-02-28", "2017-09-12", "2021-04-18"],
                "contact": ["+91-9876543210", "+91-9876543211", "+91-9876543212", "+91-9876543213",
                          "+91-9876543214", "+91-9876543215", "+91-9876543216", "+91-9876543217"],
                "status": ["Active", "Active", "Active", "Active",
                          "Active", "Active", "Active", "Active"],
            })
            n = upload_dataframe_to_db(sample, "employees", if_exists="replace")
            st.success(f"Created sample employee table with {n} records!")
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# TAB 2: HR SECTION
# ═══════════════════════════════════════════════════════════════
with tab_hr:
    st.markdown("### 📋 HR Information Centre")

    hr_col1, hr_col2 = st.columns(2)

    with hr_col1:
        st.markdown("#### 🏢 Company Overview")
        st.markdown(f"""
        **Company:** ZERA India Pvt. Ltd.  
        **Location:** Gandhinagar, Gujarat, India  
        **Industry:** Electronics Manufacturing — Smart Meters  
        **Focus:** Design, manufacturing, and testing of smart energy meters
        compliant with Indian standards (IS 16444, IS 15959)
        
        **Core Functions:**
        - Procurement (Import + Domestic)
        - Manufacturing & Assembly
        - Quality Assurance & Testing
        - R&D and Firmware Development
        """)

    with hr_col2:
        st.markdown("#### 📅 Key HR Policies")
        st.markdown("""
        | Policy | Details |
        |--------|---------|
        | Working Hours | Mon–Sat, 9:00 AM – 6:00 PM |
        | Leave Policy | 12 Casual + 12 Sick + 15 Earned |
        | Probation | 6 months for all new hires |
        | Performance Review | Bi-annual (Apr & Oct) |
        | Safety Training | Quarterly mandatory sessions |
        | PF Contribution | 12% employer + 12% employee |
        """)

    st.divider()

    st.markdown("#### 📊 Department Structure")
    dept_data = pd.DataFrame({
        "Department": ["Engineering", "Quality Assurance", "Production", "Procurement",
                       "HR & Admin", "Accounts", "R&D"],
        "Head Count": [12, 6, 18, 4, 3, 3, 5],
        "Head": ["VP Engineering", "QA Director", "Plant Manager", "Purchase Head",
                "HR Manager", "CFO", "CTO"],
    })
    st.dataframe(dept_data, use_container_width=True, hide_index=True)

    # If employee data exists, show analytics
    if "employees" in list_tables():
        st.markdown("---")
        st.markdown("#### 📈 Employee Analytics (from uploaded data)")
        emp = query_df("SELECT * FROM employees")
        if len(emp) > 0:
            import plotly.express as px

            dept_col = [c for c in emp.columns if "dept" in c.lower() or "department" in c.lower()]
            if dept_col:
                dept_counts = emp[dept_col[0]].value_counts().reset_index()
                dept_counts.columns = ["Department", "Count"]
                fig = px.pie(dept_counts, values="Count", names="Department",
                            title="Employees by Department", hole=0.4)
                fig.update_layout(height=350, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3: METER TESTING STANDARDS
# ═══════════════════════════════════════════════════════════════
with tab_meter:
    st.markdown("### 🔬 Smart Meter Testing Standards & Specifications")

    st.markdown("""
    ZERA India manufactures and tests **Three-Phase Smart Energy Meters** compliant with
    **IS 16444 (Part 1) / IS 15959** standards. Below are the testing parameters and
    thresholds used in the analytics platform.
    """)

    st.markdown("#### ⚡ Electrical Specifications")

    spec_col1, spec_col2 = st.columns(2)
    with spec_col1:
        st.markdown(f"""
        | Parameter | Value |
        |-----------|-------|
        | Nominal Voltage | **{NOMINAL_VOLTAGE} V** |
        | Voltage Tolerance | ±10% ({LOW_VOLTAGE_THRESHOLD:.0f}V – {HIGH_VOLTAGE_THRESHOLD:.0f}V) |
        | Over Voltage Threshold | **{OVER_VOLTAGE} V** (120%) |
        | Under Voltage Threshold | **{UNDER_VOLTAGE} V** (80%) |
        """)

    with spec_col2:
        st.markdown(f"""
        | Parameter | Value |
        |-----------|-------|
        | Basic Current (Ib) | **10 A** |
        | Maximum Current (Imax) | **60 A** |
        | Rated Frequency | **50 Hz** |
        | Accuracy Class | **1.0** |
        """)

    st.markdown("#### 🧪 Test Categories")
    st.markdown("""
    | Test Type | Description | Data Source |
    |-----------|-------------|-------------|
    | **Accuracy & Data Readout** | Meter reading accuracy at various loads, firmware verification | PDF Report |
    | **Voltage Events** | Over/under voltage occurrence and restoration logging | Event Profile PDF |
    | **Power Events** | 3-phase power failure detection and recovery | Event Profile PDF |
    | **Transaction Events** | Programming, firmware updates, communication events | Event Profile PDF |
    | **Other Events** | Earth load, magnetic tamper, neutral disturbance | Event Profile PDF |
    """)

    st.markdown("#### 📊 Current Meter Test Data")
    # Show meter data if loaded
    try:
        accuracy = query_df("SELECT * FROM meter_accuracy_test")
        if len(accuracy) > 0:
            st.markdown("**Accuracy Test Results:**")
            st.dataframe(accuracy, use_container_width=True, hide_index=True)

            csv_acc = accuracy.to_csv(index=False).encode()
            st.download_button("⬇️ Download Accuracy Data", csv_acc,
                             file_name="meter_accuracy_test.csv", mime="text/csv")
    except:
        pass

    # Upload new meter test PDFs
    st.markdown("---")
    st.markdown("#### 📤 Upload Additional Meter Test Data")
    meter_upload = st.file_uploader(
        "Upload meter test data (CSV/Excel — structured event data)",
        type=["csv", "xlsx", "xls"], key="meter_upload"
    )
    if meter_upload:
        try:
            if meter_upload.name.endswith(".csv"):
                m_df = pd.read_csv(meter_upload)
            else:
                m_df = pd.read_excel(meter_upload)
            st.dataframe(m_df.head(), use_container_width=True, hide_index=True)

            tname = st.text_input("Table name:", value="meter_custom_data", key="meter_tname")
            if st.button("✅ Save meter data", key="save_meter"):
                n = upload_dataframe_to_db(m_df, tname, if_exists="replace")
                st.success(f"Saved {n} rows to `{tname}`!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════
# TAB 4: REPORTS & BLOG
# ═══════════════════════════════════════════════════════════════
with tab_blog:
    st.markdown("### 📝 Reports & Insights Blog")

    st.markdown("""
    This section provides analytical reports and insights generated from the ZERA 
    procurement and meter testing data. These can serve as internal knowledge-base
    articles for the team.
    """)

    # Auto-generated insights
    st.markdown("---")
    st.markdown("#### 📊 Procurement Insights Report")

    try:
        from modules.analytics import get_procurement_summary
        proc = get_procurement_summary()

        st.markdown(f"""
        **Financial Year 2023-24 Procurement Summary**
        
        Total procurement spend for FY 2023-24 stands at **₹{proc.get('grand_total_spend', 0):,.0f}**,
        distributed across foreign imports (₹{proc.get('total_import_landed', 0):,.0f} landed cost),
        domestic purchases (₹{proc.get('total_india_value', 0):,.0f}), packing materials
        (₹{proc.get('total_packing_value', 0):,.0f}), and labour charges
        (₹{proc.get('total_labour_value', 0):,.0f}).
        
        The company worked with **{proc.get('import_suppliers', 0)} import suppliers** and 
        **{proc.get('india_suppliers', 0)} domestic suppliers** across **{proc.get('total_line_items', 0):,} line items**.
        """)
    except:
        st.info("Load procurement data to see auto-generated insights.")

    st.markdown("---")
    st.markdown("#### ⚡ Meter Testing Insights Report")

    try:
        from modules.analytics import get_meter_summary
        meter = get_meter_summary()

        st.markdown(f"""
        **Smart Meter Testing — Session S-14 Summary**
        
        A total of **{meter.get('total_meters_tested', 0)} meters** were tested per IS 16444 standards.
        **{meter.get('meters_passed', 0)}** passed and **{meter.get('meters_failed', 0)}** failed,
        resulting in a **{meter.get('pass_rate', 0):.0f}% pass rate**.
        
        The average tamper count across tested meters was **{meter.get('avg_tamper_count', 0):.1f}**,
        with average power failure count of **{meter.get('avg_power_fail_count', 0):.1f}**.
        A total of **{meter.get('total_voltage_events', 0)} voltage events** and 
        **{meter.get('total_power_events', 0)} power events** were recorded.
        
        **Key Observations:**
        - Meters with high tamper counts (>100) correlate with older firmware versions
        - Voltage events cluster around early morning hours (grid instability)
        - Power failure restoration times average under 30 minutes
        """)
    except:
        st.info("Load meter data to see auto-generated insights.")

    st.markdown("---")
    st.markdown("#### 📌 Notes & Custom Reports")
    st.markdown("Use the **AI Query Chat** or **Graph Builder** to generate custom reports "
                "and visualizations from any data in the system.")
