import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database.db import query_df
from modules.analytics import get_meter_summary, get_voltage_event_breakdown, get_voltage_timeline

st.set_page_config(page_title="Meter Analytics | ZERA Analytics", page_icon="⚡", layout="wide")
st.markdown("## ⚡ Smart Meter Analytics Engine")
st.caption("Meter test results, voltage event profiling, and health assessment — Meter #3003597 (Session S-14)")
st.divider()

# KPIs
kpis = get_meter_summary()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Meters Tested", kpis.get("total_meters_tested", 0))
c2.metric("Passed", kpis.get("meters_passed", 0), delta="✓")
c3.metric("Failed", kpis.get("meters_failed", 0), delta="✗", delta_color="inverse")
c4.metric("Avg Tamper Count", f"{kpis.get('avg_tamper_count', 0):.0f}")
c5.metric("Voltage Events", kpis.get("total_voltage_events", 0))

st.divider()

tab1, tab2, tab3 = st.tabs(["🔬 Accuracy Test Results", "⚡ Voltage Event Profile", "📊 Event Analysis"])

with tab1:
    st.markdown("#### Meter Accuracy & Data Readout — Session 13 (IS16444)")
    meters = query_df("SELECT * FROM meter_accuracy_test")
    if len(meters) > 0:
        # Pass/Fail visual
        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure()
            colors = ["#48bb78" if e == "pass" else "#fc5c65" for e in meters["total_evaluation"]]
            fig.add_trace(go.Bar(x=meters["meter_serial"], y=[1]*len(meters),
                                marker_color=colors, text=meters["total_evaluation"],
                                textposition="inside", textfont=dict(size=16, color="white")))
            fig.update_layout(title="Pass/Fail Status", height=250, margin=dict(t=40, b=20),
                            yaxis=dict(visible=False), xaxis_title="Meter Serial")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=[meters.iloc[0]["tamper_count"], meters.iloc[0]["power_fail_count"],
                                            meters.iloc[0]["programming_count"], meters.iloc[0]["billing_count"]],
                                         theta=["Tamper", "Power Fail", "Programming", "Billing"],
                                         fill="toself", name=meters.iloc[0]["meter_serial"]))
            if len(meters) > 1:
                fig.add_trace(go.Scatterpolar(r=[meters.iloc[1]["tamper_count"], meters.iloc[1]["power_fail_count"],
                                                meters.iloc[1]["programming_count"], meters.iloc[1]["billing_count"]],
                                             theta=["Tamper", "Power Fail", "Programming", "Billing"],
                                             fill="toself", name=meters.iloc[1]["meter_serial"]))
            fig.update_layout(title="Meter Health Radar", height=350, margin=dict(t=40, b=20),
                            polar=dict(radialaxis=dict(visible=True)))
            st.plotly_chart(fig, use_container_width=True)

        # Detailed comparison table
        st.markdown("#### Meter Comparison Table")
        display_cols = ["meter_serial", "manufacturer", "manufacture_year", "firmware_version",
                       "total_evaluation", "tamper_count", "power_fail_count",
                       "cum_power_fail_duration", "billing_count", "programming_count",
                       "max_demand_kw"]
        available = [c for c in display_cols if c in meters.columns]
        st.dataframe(meters[available], use_container_width=True, hide_index=True)

        # Manufacturer analysis
        st.markdown("#### By Manufacturer")
        mfr = meters.groupby("manufacturer").agg(
            meters_count=("meter_serial", "count"),
            avg_tamper=("tamper_count", "mean"),
            avg_power_fail=("power_fail_count", "mean"),
            pass_count=("total_evaluation", lambda x: (x == "pass").sum())
        ).reset_index()
        st.dataframe(mfr, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("#### Voltage Related Events — Meter 3003597")
    events = query_df("SELECT * FROM meter_voltage_events")
    if len(events) > 0:
        st.success(f"📡 {len(events)} voltage events parsed from PDF")

        # Event type breakdown
        col1, col2 = st.columns(2)
        with col1:
            breakdown = get_voltage_event_breakdown()
            if len(breakdown) > 0:
                fig = px.sunburst(breakdown, path=["event_type", "event_action"], values="count",
                                color="count", color_continuous_scale="RdYlGn_r")
                fig.update_layout(title="Event Type Breakdown", height=400, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Occurrence vs Restoration
            action_counts = events.groupby("event_action").size().reset_index(name="count")
            fig = px.pie(action_counts, values="count", names="event_action", hole=0.4,
                        color_discrete_map={"Occurrence": "#fc5c65", "Restoration": "#48bb78"},
                        title="Occurrence vs Restoration")
            fig.update_layout(height=400, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # Voltage readings scatter
        st.markdown("#### Voltage Readings During Events")
        fig = go.Figure()
        for phase, col, color in [("R-Phase", "voltage_vrn", "#fc5c65"),
                                   ("Y-Phase", "voltage_vyn", "#fed330"),
                                   ("B-Phase", "voltage_vbn", "#4b7bec")]:
            valid = events[events[col].notna()]
            fig.add_trace(go.Scatter(x=list(range(len(valid))), y=valid[col],
                                    mode="markers", name=phase, marker=dict(color=color, size=5)))
        # Reference lines
        fig.add_hline(y=240, line_dash="dash", line_color="green", annotation_text="Nominal 240V")
        fig.add_hline(y=288, line_dash="dash", line_color="red", annotation_text="Over Voltage (288V)")
        fig.add_hline(y=192, line_dash="dash", line_color="orange", annotation_text="Under Voltage (192V)")
        fig.update_layout(height=400, margin=dict(t=20, b=20),
                         xaxis_title="Event Index", yaxis_title="Voltage (V)")
        st.plotly_chart(fig, use_container_width=True)

        # Filter by event type
        st.markdown("#### 🎛️ Filter Events")
        event_types = sorted(events["event_type"].dropna().unique().tolist())
        sel_types = st.multiselect("Filter by event type:", event_types, key="volt_type_filter")
        sel_action = st.multiselect("Filter by action:", ["Occurrence", "Restoration", "Unknown"], key="volt_action_filter")

        filtered_events = events.copy()
        if sel_types:
            filtered_events = filtered_events[filtered_events["event_type"].isin(sel_types)]
        if sel_action:
            filtered_events = filtered_events[filtered_events["event_action"].isin(sel_action)]

        st.markdown(f"**Showing {len(filtered_events)} of {len(events)} events**")

        # Raw data table
        with st.expander("📋 View Raw Event Data"):
            st.dataframe(filtered_events, use_container_width=True, hide_index=True, height=400)

        # Download
        import io
        dl1, dl2 = st.columns(2)
        with dl1:
            csv_v = filtered_events.to_csv(index=False).encode()
            st.download_button("⬇️ Download Voltage Events (CSV)", csv_v,
                             file_name="voltage_events_filtered.csv", mime="text/csv",
                             use_container_width=True, key="dl_volt_csv")
        with dl2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                filtered_events.to_excel(w, index=False)
            st.download_button("⬇️ Download Voltage Events (Excel)", buf.getvalue(),
                             file_name="voltage_events_filtered.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True, key="dl_volt_xlsx")
    else:
        st.warning("No voltage events parsed yet")

with tab3:
    st.markdown("#### Power Failure Events — Meter 3003597")
    pwr = query_df("SELECT * FROM meter_power_events")
    if len(pwr) > 0:
        st.success(f"⚡ {len(pwr)} power failure events parsed")
        pwr["event_datetime"] = pd.to_datetime(pwr["event_datetime"], errors="coerce")
        pwr_sorted = pwr.sort_values("event_datetime")

        col1, col2 = st.columns(2)
        with col1:
            action_ct = pwr.groupby("event_action").size().reset_index(name="count")
            fig_pwr = px.pie(action_ct, values="count", names="event_action", hole=0.4,
                           color_discrete_map={"Occurrence": "#fc5c65", "Restoration": "#48bb78"},
                           title="Power Failures: Occurrence vs Restoration")
            fig_pwr.update_layout(height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig_pwr, use_container_width=True)
        with col2:
            occ = pwr_sorted[pwr_sorted["event_action"] == "Occurrence"]
            rest = pwr_sorted[pwr_sorted["event_action"] == "Restoration"]
            fig_tl = go.Figure()
            fig_tl.add_trace(go.Scatter(x=occ["event_datetime"], y=[1]*len(occ),
                                       mode="markers", name="Failure Start", marker=dict(color="red", size=10)))
            fig_tl.add_trace(go.Scatter(x=rest["event_datetime"], y=[0]*len(rest),
                                       mode="markers", name="Restoration", marker=dict(color="green", size=10)))
            fig_tl.update_layout(title="Power Failure Timeline", height=350, margin=dict(t=40, b=20),
                               yaxis=dict(tickvals=[0,1], ticktext=["Restored","Failed"]))
            st.plotly_chart(fig_tl, use_container_width=True)
        
        with st.expander("📋 View Power Event Data"):
            st.dataframe(pwr_sorted, use_container_width=True, hide_index=True)
    else:
        st.warning("No power events loaded")

    st.markdown("#### Transaction Events — Meter 3003597")
    txn = query_df("SELECT * FROM meter_transaction_events")
    if len(txn) > 0:
        st.info(f"📋 {len(txn)} transaction events found")
        st.dataframe(txn, use_container_width=True, hide_index=True)
    else:
        st.warning("No transaction events loaded")

    st.markdown("#### Event Summary Statistics")
    events = query_df("SELECT * FROM meter_voltage_events")
    if len(events) > 0:
        event_summary = events.groupby("event_type").agg(
            total_events=("id", "count"),
            avg_voltage_r=("voltage_vrn", "mean"),
            avg_voltage_y=("voltage_vyn", "mean"),
            avg_voltage_b=("voltage_vbn", "mean"),
            min_voltage=("voltage_vrn", "min"),
            max_voltage=("voltage_vrn", "max"),
        ).reset_index()
        st.dataframe(event_summary.round(2), use_container_width=True, hide_index=True)
