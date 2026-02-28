# ZERA Analytics Intelligence Platform — v2.0 Dynamic

AI-enabled procurement & smart meter analytics dashboard for ZERA Electronics India.

> **Branch**: `v2_dynamic` — Enhanced from `v1_stable`

## What's New in v2.0

| Feature | Description |
|---------|-------------|
| **Lazy Loading** | Data loads on-demand, not at startup — 3x faster launch |
| **File Upload Manager** | Upload Excel/CSV files dynamically — each becomes a queryable table |
| **Dynamic Data Source** | Choose: bundled data, upload new, or both |
| **Supplier/Client Filters** | Dropdown filters on every data page + date range picker |
| **CSV/Excel Download** | Download filtered data from any page |
| **AI Query Chat** | Ask questions in English → auto-generates SQL → shows results → download |
| **Direct SQL Mode** | Write and execute your own SQL queries (read-only, safe) |
| **Tableau-style Graph Builder** | Pick any table, any columns, any chart type — 15 chart types |
| **Company Hub** | Employee directory, HR policies, meter testing standards |
| **Reports Blog** | Auto-generated procurement & meter testing insight reports |
| **Quick Query Suggestions** | Pre-built queries for common questions |

## Quick Start

```bash
# 1. Clone this branch
git clone -b v2_dynamic https://github.com/Solx7c0de/zera_intelligence_dashboard.git
cd zera_intelligence_dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

## Project Structure (v2)

```
zera_intelligence_dashboard/
├── app.py                          # Main entry — lazy loading + data source selector
├── config.py                       # Configuration constants (v2: chart types, upload dir)
├── requirements.txt                # Python dependencies (v2: +kaleido)
├── data/                           # Bundled Excel + PDF data files
├── uploads/                        # (auto-created) User-uploaded files
├── database/
│   ├── db.py                       # SQLAlchemy engine + v2: dynamic tables, safe_query, schema helpers
│   ├── schema.sql                  # Base schema (auto-created on first run)
│   └── procurement.db              # SQLite DB (auto-generated)
├── modules/
│   ├── cleaning.py                 # Data cleaning pipeline
│   ├── data_loader.py              # Excel sheet parser (4 sheets)
│   ├── pdf_parser.py               # Meter PDF parser
│   ├── analytics.py                # Analytics functions (KPIs, breakdowns)
│   └── ml_models.py                # ML models (risk, anomaly, clustering, forecast)
└── pages/
    ├── 1_Dashboard.py              # Executive dashboard + download
    ├── 2_Procurement.py            # v2: Supplier filter dropdown + date range + download
    ├── 3_Meter_Analytics.py        # v2: Event type filters + download
    ├── 4_AI_Insights.py            # ML-powered insights (4 tabs)
    ├── 5_Data_Manager.py           # NEW: Upload, filter, preview, download any table
    ├── 6_AI_Query.py               # NEW: English → SQL → results → download
    ├── 7_Graph_Builder.py          # NEW: Tableau-style chart builder (15 chart types)
    └── 8_Company_Hub.py            # NEW: Employee directory, HR, meter specs, blog
```

## Data Tables

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
| *uploaded_** | dynamic | User uploads via Data Manager |
| *employees* | dynamic | Created/uploaded via Company Hub |

## Chart Types (Graph Builder)

Bar · Horizontal Bar · Grouped Bar · Line · Area · Scatter · Bubble · Pie · Donut · Histogram · Box Plot · Treemap · Sunburst · Heatmap

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
3. Connect your repo, set `app.py` as main file, branch `v2_dynamic`
4. Deploy — share the URL

## About

Built by Vishvam | ZERA India Pvt. Ltd. Internship 2025-26
