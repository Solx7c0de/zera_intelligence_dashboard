"""Analytics functions for ZERA procurement and meter data."""
import pandas as pd
from database.db import query_df


def get_procurement_summary() -> dict:
    """High-level procurement KPIs."""
    try:
        imp = query_df("SELECT COUNT(*) as n, COALESCE(SUM(total_value_inr),0) as val, COALESCE(SUM(landed_cost),0) as lc, COUNT(DISTINCT supplier) as sup FROM purchase_import")
        ind = query_df("SELECT COUNT(*) as n, COALESCE(SUM(invoice_amount),0) as val, COUNT(DISTINCT supplier) as sup FROM purchase_india")
        pack = query_df("SELECT COUNT(*) as n, COALESCE(SUM(invoice_amount),0) as val FROM purchase_packing")
        lab = query_df("SELECT COUNT(*) as n, COALESCE(SUM(invoice_amount),0) as val FROM purchase_labour")
        
        total_import = float(imp["lc"].iloc[0] or 0)
        total_india = float(ind["val"].iloc[0] or 0)
        total_pack = float(pack["val"].iloc[0] or 0)
        total_labour = float(lab["val"].iloc[0] or 0)
        
        return {
            "grand_total_spend": total_import + total_india + total_pack + total_labour,
            "total_import_landed": total_import,
            "total_import_value": float(imp["val"].iloc[0] or 0),
            "total_india_value": total_india,
            "total_packing_value": total_pack,
            "total_labour_value": total_labour,
            "total_line_items": int(imp["n"].iloc[0]) + int(ind["n"].iloc[0]) + int(pack["n"].iloc[0]) + int(lab["n"].iloc[0]),
            "import_suppliers": int(imp["sup"].iloc[0]),
            "india_suppliers": int(ind["sup"].iloc[0]),
        }
    except Exception as e:
        return {"grand_total_spend": 0, "total_line_items": 0, "error": str(e)}


def get_meter_summary() -> dict:
    """Meter testing KPIs."""
    try:
        acc = query_df("SELECT COUNT(*) as n, SUM(CASE WHEN total_evaluation='pass' THEN 1 ELSE 0 END) as passed, AVG(tamper_count) as avg_tamper, AVG(power_fail_count) as avg_pf FROM meter_accuracy_test")
        ve = query_df("SELECT COUNT(*) as n FROM meter_voltage_events")
        pe = query_df("SELECT COUNT(*) as n FROM meter_power_events")
        
        total = int(acc["n"].iloc[0])
        passed = int(acc["passed"].iloc[0] or 0)
        
        return {
            "total_meters_tested": total,
            "meters_passed": passed,
            "meters_failed": total - passed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "avg_tamper_count": float(acc["avg_tamper"].iloc[0] or 0),
            "avg_power_fail_count": float(acc["avg_pf"].iloc[0] or 0),
            "total_voltage_events": int(ve["n"].iloc[0]),
            "total_power_events": int(pe["n"].iloc[0]),
        }
    except Exception as e:
        return {"total_meters_tested": 0, "pass_rate": 0, "total_voltage_events": 0, "error": str(e)}


def get_supplier_analysis(source: str = "import") -> pd.DataFrame:
    """Top suppliers by spend."""
    if source == "import":
        return query_df("""
            SELECT supplier, SUM(landed_cost) as total_spend, COUNT(*) as order_count,
                   SUM(quantity) as total_qty, AVG(landed_cost) as avg_order_value
            FROM purchase_import WHERE supplier IS NOT NULL
            GROUP BY supplier ORDER BY total_spend DESC
        """)
    else:
        return query_df("""
            SELECT supplier, SUM(invoice_amount) as total_spend, COUNT(*) as order_count,
                   SUM(quantity) as total_qty, AVG(invoice_amount) as avg_order_value
            FROM purchase_india WHERE supplier IS NOT NULL
            GROUP BY supplier ORDER BY total_spend DESC
        """)


def get_monthly_spend(source: str = "import") -> pd.DataFrame:
    """Monthly spend trends."""
    if source == "import":
        df = query_df("SELECT purchase_date, landed_cost FROM purchase_import WHERE purchase_date IS NOT NULL")
        if len(df) == 0:
            return pd.DataFrame()
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
        df = df.dropna(subset=["purchase_date"])
        df["month"] = df["purchase_date"].dt.to_period("M").astype(str)
        return df.groupby("month").agg(landed_cost=("landed_cost", "sum"), count=("landed_cost", "count")).reset_index().sort_values("month")
    else:
        df = query_df("SELECT purchase_date, invoice_amount FROM purchase_india WHERE purchase_date IS NOT NULL")
        if len(df) == 0:
            return pd.DataFrame()
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
        df = df.dropna(subset=["purchase_date"])
        df["month"] = df["purchase_date"].dt.to_period("M").astype(str)
        return df.groupby("month").agg(invoice_amount=("invoice_amount", "sum"), count=("invoice_amount", "count")).reset_index().sort_values("month")


def get_voltage_event_breakdown() -> pd.DataFrame:
    """Voltage events grouped by type and action."""
    return query_df("""
        SELECT event_type, event_action, COUNT(*) as count
        FROM meter_voltage_events
        GROUP BY event_type, event_action
        ORDER BY count DESC
    """)


def get_voltage_timeline() -> pd.DataFrame:
    """Voltage events over time."""
    df = query_df("SELECT event_datetime, event_type, event_action, voltage_vrn, voltage_vyn, voltage_vbn FROM meter_voltage_events ORDER BY event_datetime")
    if len(df) > 0:
        df["event_datetime"] = pd.to_datetime(df["event_datetime"], errors="coerce")
    return df


def get_power_event_timeline() -> pd.DataFrame:
    """Power failure events over time."""
    df = query_df("SELECT event_datetime, event_type, event_action FROM meter_power_events ORDER BY event_datetime")
    if len(df) > 0:
        df["event_datetime"] = pd.to_datetime(df["event_datetime"], errors="coerce")
    return df
