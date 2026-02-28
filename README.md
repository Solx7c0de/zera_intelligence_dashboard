# ZERA Analytics Intelligence Platform

AI-enabled procurement & smart meter analytics dashboard for ZERA Electronics India.

## Quick Start

```bash
# 1. Clone/copy this project
# 2. Add your data files to the data/ folder:
#    - Purchase-Stock-2023-24_BS_290724.xlsx
#    - All S-14_MP2_*.pdf meter test files
#    - ACCURCAY_AND_DATA_READOUT.pdf
#    - POWER_CONSUMPTION_TEST.pdf

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

## Project Structure

```
procurement_ai/
├── app.py                    # Main entry point + executive overview
├── config.py                 # Configuration constants
├── requirements.txt          # Python dependencies
├── data/                     # Your Excel + PDF data files
├── database/
│   ├── db.py                 # SQLAlchemy engine + helper functions
│   ├── schema.sql            # Database schema (auto-created)
│   └── procurement.db        # SQLite DB (auto-generated on first run)
├── modules/
│   ├── cleaning.py           # Data cleaning pipeline
│   ├── data_loader.py        # Excel sheet parser (4 sheets)
│   ├── pdf_parser.py         # Meter PDF parser (voltage/power/txn events)
│   ├── analytics.py          # Analytics functions (KPIs, breakdowns)
│   └── ml_models.py          # ML models (risk scoring, anomaly detection, clustering, forecast)
└── pages/
    ├── 1_Dashboard.py        # Executive dashboard with KPI cards
    ├── 2_Procurement.py      # Procurement deep dive (4 tabs)
    ├── 3_Meter_Analytics.py  # Smart meter event analysis
    └── 4_AI_Insights.py      # ML-powered insights (4 tabs)
```

## Data Loaded

| Table | Records | Source |
|-------|---------|--------|
| purchase_import | 284 | Excel: For. Purchase |
| purchase_india | 2,506 | Excel: Purchase India |
| purchase_packing | 170 | Excel: PACKING MATERIAL |
| purchase_labour | 157 | Excel: Labour Charges |
| meter_accuracy_test | 4 | PDF: Accuracy Report |
| meter_voltage_events | 49 | PDF: Voltage Events |
| meter_power_events | 50 | PDF: Power Events |
| meter_transaction_events | 5 | PDF: Transaction Events |

## ML Models

| Model | Algorithm | Purpose |
|-------|-----------|---------|
| Meter Risk Scoring | Weighted composite + Isolation Forest | Predict meter failure risk |
| Voltage Anomaly Detection | Isolation Forest | Flag abnormal voltage events |
| Supplier Clustering | K-Means (k=3) | Segment suppliers into tiers |
| Spend Forecasting | EMA trend projection | Project future procurement spend |

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to share.streamlit.io
3. Connect your repo, set `app.py` as main file
4. Deploy — share the URL for your presentation
