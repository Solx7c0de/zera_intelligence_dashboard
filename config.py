"""Configuration for ZERA Analytics Platform."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "database", "procurement.db")

# App settings
APP_TITLE = "ZERA Analytics Intelligence Platform"
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
