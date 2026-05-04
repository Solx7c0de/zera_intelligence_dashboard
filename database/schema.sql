-- ZERA PROCUREMENT AI - DATABASE SCHEMA

-- PURCHASE TABLES
CREATE TABLE IF NOT EXISTS purchase_import (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT, invoice_no TEXT, item_description TEXT, quantity REAL,
    unit_rate_usd REAL, exchange_rate REAL, unit_rate_inr REAL, total_value_inr REAL,
    freight REAL DEFAULT 0, import_duty REAL DEFAULT 0, custom_clearance REAL DEFAULT 0,
    misc_charges REAL DEFAULT 0, landed_cost REAL DEFAULT 0,
    quantity_used REAL DEFAULT 0, balance_quantity REAL DEFAULT 0, purchase_date DATE
);

CREATE TABLE IF NOT EXISTS purchase_india (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT, invoice_no TEXT, item_description TEXT, hsn_code TEXT,
    quantity REAL, unit TEXT, unit_price REAL, total_price REAL, freight REAL DEFAULT 0,
    sgst REAL DEFAULT 0, cgst REAL DEFAULT 0, igst REAL DEFAULT 0,
    invoice_amount REAL DEFAULT 0, quantity_consumed REAL DEFAULT 0,
    balance_quantity REAL DEFAULT 0, purchase_date DATE
);

CREATE TABLE IF NOT EXISTS purchase_packing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT, invoice_no TEXT, item_description TEXT, hsn_code TEXT,
    quantity REAL, unit TEXT, unit_price REAL, total_price REAL, freight REAL DEFAULT 0,
    sgst REAL DEFAULT 0, cgst REAL DEFAULT 0, igst REAL DEFAULT 0,
    invoice_amount REAL DEFAULT 0, quantity_consumed REAL DEFAULT 0,
    balance_quantity REAL DEFAULT 0, purchase_date DATE
);

CREATE TABLE IF NOT EXISTS purchase_labour (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT, invoice_no TEXT, item_description TEXT, hsn_code TEXT,
    quantity REAL, unit TEXT, unit_price REAL, total_price REAL, labour_charges REAL DEFAULT 0,
    sgst REAL DEFAULT 0, cgst REAL DEFAULT 0, igst REAL DEFAULT 0,
    invoice_amount REAL DEFAULT 0, purchase_date DATE
);

-- METER TEST DATA TABLES (columns match parser output exactly)
CREATE TABLE IF NOT EXISTS meter_voltage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_datetime TEXT, event_type TEXT, event_action TEXT,
    current_ir REAL, current_iy REAL, current_ib REAL,
    voltage_vrn REAL, voltage_vyn REAL, voltage_vbn REAL,
    pf_r REAL, pf_y REAL, pf_b REAL,
    cum_energy_kwh_import INTEGER, cum_tamper_count INTEGER
);

CREATE TABLE IF NOT EXISTS meter_power_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_datetime TEXT, event_type TEXT, event_action TEXT,
    current_ir REAL, voltage_vrn REAL, voltage_vyn REAL, voltage_vbn REAL,
    cum_energy_kwh_import INTEGER
);

CREATE TABLE IF NOT EXISTS meter_other_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_datetime TEXT, event_type TEXT, event_action TEXT,
    current_ir REAL, voltage_vrn REAL, voltage_vyn REAL, voltage_vbn REAL
);

CREATE TABLE IF NOT EXISTS meter_transaction_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_datetime TEXT, event_description TEXT
);

CREATE TABLE IF NOT EXISTS meter_accuracy_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_serial TEXT, manufacturer TEXT, manufacture_year INTEGER,
    firmware_version TEXT, total_evaluation TEXT,
    tamper_count INTEGER, power_fail_count INTEGER, cum_power_fail_duration REAL,
    billing_count INTEGER, programming_count INTEGER, max_demand_kw REAL
);
