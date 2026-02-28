"""Configuration for ZERA Analytics Platform — v2 Dynamic."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "database", "procurement.db")

# Create upload dir if missing
os.makedirs(UPLOAD_DIR, exist_ok=True)

# App settings
APP_TITLE = "ZERA Analytics Intelligence Platform"
APP_VERSION = "2.0 — Dynamic"
APP_ICON = "⚡"
COMPANY = "ZERA India Pvt. Ltd., Gandhinagar"

# Meter specifications
NOMINAL_VOLTAGE = 240  # V
VOLTAGE_TOLERANCE = 0.10  # ±10%
HIGH_VOLTAGE_THRESHOLD = NOMINAL_VOLTAGE * (1 + VOLTAGE_TOLERANCE)  # 264V
LOW_VOLTAGE_THRESHOLD = NOMINAL_VOLTAGE * (1 - VOLTAGE_TOLERANCE)   # 216V
OVER_VOLTAGE = 288  # V
UNDER_VOLTAGE = 192  # V
BASIC_CURRENT = 10   # A
MAX_CURRENT = 60     # A
FREQUENCY = 50       # Hz

# Supported upload formats
SUPPORTED_EXCEL = [".xlsx", ".xls", ".csv"]
SUPPORTED_PDF = [".pdf"]

# Graph types for Tableau-style builder
CHART_TYPES = {
    "Bar Chart": "bar",
    "Line Chart": "line",
    "Area Chart": "area",
    "Scatter Plot": "scatter",
    "Pie Chart": "pie",
    "Histogram": "histogram",
    "Box Plot": "box",
    "Treemap": "treemap",
    "Sunburst": "sunburst",
    "Heatmap": "heatmap",
    "Funnel": "funnel",
}
