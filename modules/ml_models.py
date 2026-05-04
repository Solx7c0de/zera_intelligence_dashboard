import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from database.db import query_df


def meter_risk_scoring():
    """Score meters based on tamper count, power failures, and voltage anomalies.
    Returns a dataframe with risk scores and categories."""
    df = query_df("SELECT * FROM meter_accuracy_test")
    if len(df) < 2:
        return pd.DataFrame()

    features = ["tamper_count", "power_fail_count", "cum_power_fail_duration",
                 "programming_count", "billing_count"]
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest for anomaly detection
    iso = IsolationForest(contamination=0.25, random_state=42)
    df["anomaly_score"] = iso.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal

    # Create composite risk score (0-100)
    # Normalize each feature to 0-1, weighted sum
    weights = {"tamper_count": 0.30, "power_fail_count": 0.25,
               "cum_power_fail_duration": 0.20, "programming_count": 0.15,
               "billing_count": 0.10}

    risk_score = np.zeros(len(df))
    for feat, weight in weights.items():
        vals = df[feat].fillna(0).values.astype(float)
        max_val = vals.max() if vals.max() > 0 else 1
        risk_score += (vals / max_val) * weight * 100

    df["risk_score"] = risk_score
    df["risk_category"] = pd.cut(df["risk_score"],
                                  bins=[0, 30, 60, 100],
                                  labels=["Low Risk", "Medium Risk", "High Risk"],
                                  include_lowest=True)

    return df[["meter_serial", "manufacturer", "total_evaluation",
               "tamper_count", "power_fail_count", "risk_score",
               "risk_category", "anomaly_score"]]


def voltage_anomaly_detection():
    """Detect anomalous voltage events using Isolation Forest."""
    df = query_df("SELECT * FROM meter_voltage_events")
    if len(df) < 5:
        return pd.DataFrame()

    # Use voltage readings as features
    features = ["voltage_vrn", "voltage_vyn", "voltage_vbn",
                 "current_ir", "current_iy", "current_ib"]
    df_clean = df.dropna(subset=features[:3])

    if len(df_clean) < 5:
        return pd.DataFrame()

    X = df_clean[features].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(contamination=0.15, random_state=42)
    df_clean["is_anomaly"] = iso.fit_predict(X_scaled)
    df_clean["is_anomaly"] = df_clean["is_anomaly"].map({1: "Normal", -1: "Anomaly"})

    return df_clean


def supplier_clustering():
    """Cluster suppliers by spend patterns."""
    df = query_df("""
        SELECT supplier,
               SUM(total_value_inr) as total_spend,
               COUNT(*) as order_count,
               SUM(quantity) as total_qty,
               AVG(total_value_inr) as avg_order_value
        FROM purchase_import
        GROUP BY supplier
        HAVING order_count >= 2
    """)
    if len(df) < 3:
        return df

    features = ["total_spend", "order_count", "total_qty", "avg_order_value"]
    X = df[features].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clusters = min(3, len(df))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X_scaled)
    cluster_names = {0: "Strategic", 1: "Routine", 2: "Tactical"}
    df["supplier_tier"] = df["cluster"].map(cluster_names)

    return df


def spend_forecast(periods=6):
    """Simple exponential moving average forecast for spend."""
    df = query_df("SELECT purchase_date, total_value_inr FROM purchase_import WHERE purchase_date IS NOT NULL")
    if len(df) < 3:
        return pd.DataFrame()

    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    df = df.dropna(subset=["purchase_date"])
    df["month"] = df["purchase_date"].dt.to_period("M")
    monthly = df.groupby("month")["total_value_inr"].sum().reset_index()
    monthly["month"] = monthly["month"].astype(str)
    monthly = monthly.sort_values("month")

    # EMA-based forecast
    values = monthly["total_value_inr"].values
    alpha = 0.3
    ema = values[-1]
    forecasts = []
    last_month = pd.to_datetime(monthly["month"].iloc[-1])

    for i in range(1, periods + 1):
        forecast_month = last_month + pd.DateOffset(months=i)
        trend = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
        forecast_val = ema + trend * i
        # Add some variance
        noise = np.random.normal(0, values.std() * 0.1) if len(values) > 1 else 0
        forecasts.append({
            "month": forecast_month.strftime("%Y-%m"),
            "total_value_inr": max(0, forecast_val + noise),
            "type": "forecast"
        })

    monthly["type"] = "actual"
    forecast_df = pd.DataFrame(forecasts)
    return pd.concat([monthly, forecast_df], ignore_index=True)
