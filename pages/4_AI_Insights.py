import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.ml_models import meter_risk_scoring, voltage_anomaly_detection, supplier_clustering, spend_forecast

st.set_page_config(page_title="AI Insights | ZERA Analytics", page_icon="🤖", layout="wide")
st.markdown("## 🤖 AI-Powered Insights")
st.caption("Machine Learning models: Risk scoring, Anomaly detection, Clustering, and Forecasting")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Meter Risk Scoring", "🔍 Anomaly Detection",
                                    "🏷️ Supplier Clustering", "📈 Spend Forecast"])

with tab1:
    st.markdown("#### Meter Failure Risk Assessment")
    st.markdown("""
    > **Model**: Composite risk scoring using weighted features + Isolation Forest anomaly detection  
    > **Features**: Tamper count (30%), Power failures (25%), Failure duration (20%), Programming count (15%), Billing count (10%)
    """)

    risk_df = meter_risk_scoring()
    if len(risk_df) > 0:
        # Risk gauge cards
        cols = st.columns(len(risk_df))
        for i, (_, row) in enumerate(risk_df.iterrows()):
            with cols[i]:
                color = "#48bb78" if row["risk_category"] == "Low Risk" else "#f6ad55" if row["risk_category"] == "Medium Risk" else "#fc5c65"
                st.markdown(f"""
                <div style="background:{color}; padding:15px; border-radius:10px; text-align:center; color:white;">
                    <div style="font-size:0.8rem;">Meter {row['meter_serial']}</div>
                    <div style="font-size:2rem; font-weight:700;">{row['risk_score']:.0f}</div>
                    <div style="font-size:0.9rem;">{row['risk_category']}</div>
                    <div style="font-size:0.7rem;">Test: {row['total_evaluation'].upper()}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Risk factors chart
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(risk_df, x="meter_serial", y="risk_score",
                        color="risk_category",
                        color_discrete_map={"Low Risk": "#48bb78", "Medium Risk": "#f6ad55", "High Risk": "#fc5c65"},
                        title="Risk Score by Meter")
            fig.update_layout(height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Tampers", x=risk_df["meter_serial"], y=risk_df["tamper_count"], marker_color="#667eea"))
            fig.add_trace(go.Bar(name="Power Fails", x=risk_df["meter_serial"], y=risk_df["power_fail_count"], marker_color="#f093fb"))
            fig.update_layout(barmode="group", title="Risk Factor Comparison", height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # Anomaly flag
        anomalies = risk_df[risk_df["anomaly_score"] == -1]
        if len(anomalies) > 0:
            st.warning(f"⚠️ Isolation Forest flagged {len(anomalies)} meter(s) as anomalous: {', '.join(anomalies['meter_serial'].tolist())}")

        st.markdown("#### Full Risk Assessment Table")
        st.dataframe(risk_df, use_container_width=True, hide_index=True)
    else:
        st.info("Need at least 2 meters for risk scoring")

with tab2:
    st.markdown("#### Voltage Anomaly Detection")
    st.markdown("""
    > **Model**: Isolation Forest (unsupervised)  
    > **Features**: 3-phase voltage readings (VRN, VYN, VBN) + 3-phase current readings (IR, IY, IB)  
    > **Contamination**: 15% — flags the most extreme 15% of readings as anomalous
    """)

    anom_df = voltage_anomaly_detection()
    if len(anom_df) > 0:
        normal_count = (anom_df["is_anomaly"] == "Normal").sum()
        anomaly_count = (anom_df["is_anomaly"] == "Anomaly").sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Events", len(anom_df))
        c2.metric("Normal", normal_count)
        c3.metric("Anomalies Detected", anomaly_count, delta=f"{anomaly_count/len(anom_df)*100:.1f}%", delta_color="inverse")

        # Scatter plot
        fig = px.scatter(anom_df, x="voltage_vrn", y="voltage_vyn",
                        color="is_anomaly",
                        color_discrete_map={"Normal": "#48bb78", "Anomaly": "#fc5c65"},
                        size_max=10, title="Voltage R vs Y Phase — Anomaly Detection",
                        labels={"voltage_vrn": "R-Phase Voltage (V)", "voltage_vyn": "Y-Phase Voltage (V)"})
        fig.update_layout(height=450, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # 3D scatter
        fig = px.scatter_3d(anom_df, x="voltage_vrn", y="voltage_vyn", z="voltage_vbn",
                           color="is_anomaly",
                           color_discrete_map={"Normal": "#48bb78", "Anomaly": "#fc5c65"},
                           title="3-Phase Voltage Space — Anomaly Detection",
                           labels={"voltage_vrn": "VRN", "voltage_vyn": "VYN", "voltage_vbn": "VBN"})
        fig.update_layout(height=500, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # Anomaly details
        with st.expander("📋 View Anomalous Events"):
            st.dataframe(anom_df[anom_df["is_anomaly"] == "Anomaly"], use_container_width=True, hide_index=True)
    else:
        st.info("Need voltage event data for anomaly detection")

with tab3:
    st.markdown("#### Supplier Segmentation (K-Means Clustering)")
    st.markdown("""
    > **Model**: K-Means (k=3)  
    > **Features**: Total spend, Order count, Total quantity, Average order value  
    > **Output**: Strategic / Routine / Tactical tiers
    """)

    cluster_df = supplier_clustering()
    if len(cluster_df) > 0 and "supplier_tier" in cluster_df.columns:
        fig = px.scatter(cluster_df, x="total_spend", y="order_count",
                        color="supplier_tier", size="total_qty",
                        hover_data=["supplier"],
                        color_discrete_map={"Strategic": "#667eea", "Routine": "#48bb78", "Tactical": "#f6ad55"},
                        title="Supplier Segmentation")
        fig.update_layout(height=450, margin=dict(t=40, b=20),
                         xaxis_title="Total Spend (₹)", yaxis_title="Order Count")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(cluster_df[["supplier", "total_spend", "order_count", "total_qty", "supplier_tier"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Need at least 3 suppliers with 2+ orders for clustering")

with tab4:
    st.markdown("#### Import Spend Forecast (EMA-based)")
    st.markdown("""
    > **Model**: Exponential Moving Average with trend projection  
    > **Forecast period**: 6 months ahead
    """)

    forecast_df = spend_forecast()
    if len(forecast_df) > 0:
        fig = go.Figure()
        actual = forecast_df[forecast_df["type"] == "actual"]
        predicted = forecast_df[forecast_df["type"] == "forecast"]

        fig.add_trace(go.Scatter(x=actual["month"], y=actual["total_value_inr"],
                                mode="lines+markers", name="Actual",
                                line=dict(color="#667eea", width=2)))
        fig.add_trace(go.Scatter(x=predicted["month"], y=predicted["total_value_inr"],
                                mode="lines+markers", name="Forecast",
                                line=dict(color="#f093fb", width=2, dash="dash")))
        fig.update_layout(title="Monthly Import Spend — Actual vs Forecast",
                         height=400, margin=dict(t=40, b=20),
                         xaxis_title="Month", yaxis_title="Spend (₹)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Need at least 3 months of data for forecasting")

st.divider()
st.markdown("#### 🧠 Model Summary")
st.markdown("""
| Model | Algorithm | Purpose | Library |
|-------|-----------|---------|---------|
| Meter Risk Scoring | Weighted composite + Isolation Forest | Predict meter failure risk | scikit-learn |
| Voltage Anomaly Detection | Isolation Forest (unsupervised) | Flag abnormal voltage events | scikit-learn |
| Supplier Clustering | K-Means (k=3) | Segment suppliers into tiers | scikit-learn |
| Spend Forecasting | Exponential Moving Average | Project future procurement spend | pandas + numpy |
""")
st.caption("Built with scikit-learn, pandas, numpy — mapped to EXL Business Analyst skill requirements")
