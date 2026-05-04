import pandas as pd
import numpy as np
import os
from database.db import engine, query_df, table_row_count, insert_df
from modules.cleaning import clean_dataframe, safe_float


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EXCEL_FILE = os.path.join(DATA_DIR, "Purchase-Stock-2023-24_BS_290724.xlsx")


def load_foreign_purchase():
    """Load 'For. Purchase' sheet - clean headers already in row 0."""
    df = pd.read_excel(EXCEL_FILE, sheet_name="For. Purchase")
    df = df.dropna(subset=["Supplier Name"], how="all")
    df = df[df["Sr. No."].notna()]

    out = pd.DataFrame({
        "supplier": df["Supplier Name"].astype(str).str.strip(),
        "invoice_no": df["Invoice No."].astype(str).str.strip(),
        "item_description": df["Item Description"].astype(str).str.strip(),
        "quantity": pd.to_numeric(df["Quantity"], errors="coerce"),
        "unit_rate_usd": pd.to_numeric(df["Unit Rate per Unit"], errors="coerce"),
        "exchange_rate": pd.to_numeric(df["Exchange Rate"], errors="coerce"),
        "unit_rate_inr": pd.to_numeric(df["INR Rate per Unit"], errors="coerce"),
        "total_value_inr": pd.to_numeric(df["INR Value"], errors="coerce"),
        "freight": pd.to_numeric(df.get("Freight-Import", 0), errors="coerce").fillna(0),
        "import_duty": pd.to_numeric(df.get("Custom Duty", 0), errors="coerce").fillna(0),
        "custom_clearance": pd.to_numeric(df.get("Custom Clearence", df.get("Custom Clearing & Forwarding", 0)), errors="coerce").fillna(0),
        "misc_charges": pd.to_numeric(df.get("MISC", 0), errors="coerce").fillna(0),
        "quantity_used": pd.to_numeric(df.get("Quantity Used", 0), errors="coerce").fillna(0),
        "balance_quantity": pd.to_numeric(df.get("Balance Quantity", 0), errors="coerce").fillna(0),
        "purchase_date": pd.to_datetime(df["Date as per Tally"], errors="coerce"),
    })

    # Calculate landed cost
    out["landed_cost"] = out["total_value_inr"] + out["freight"] + out["import_duty"] + out["custom_clearance"] + out["misc_charges"]
    out = out.dropna(subset=["quantity"])
    out = out[out["quantity"] > 0]
    return out


def _load_india_style_sheet(sheet_name):
    """Load sheets where row 0 is totals and row 1 has headers (Purchase India, Packing, Labour)."""
    df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=None)
    # Find header row - look for "Sr. No." or "Sr No"
    header_idx = None
    for i in range(min(5, len(df))):
        row_vals = df.iloc[i].astype(str).str.lower()
        if any("sr" in v and "no" in v for v in row_vals):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 1
    df.columns = df.iloc[header_idx].astype(str).str.strip()
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    df = df[df["Sr. No."].notna()]
    return df


def load_india_purchase():
    df = _load_india_style_sheet("Purchase India")
    out = pd.DataFrame({
        "supplier": df["Supplier"].astype(str).str.strip(),
        "invoice_no": df["Invoice No."].astype(str).str.strip(),
        "item_description": df["Item Description"].astype(str).str.strip(),
        "hsn_code": df.get("HSN Code", "").astype(str),
        "quantity": pd.to_numeric(df["Quantity"], errors="coerce"),
        "unit": df.get("Unit", "").astype(str),
        "unit_price": pd.to_numeric(df["Unit Price"], errors="coerce"),
        "total_price": pd.to_numeric(df["Total Price"], errors="coerce"),
        "freight": pd.to_numeric(df.get("Freight", 0), errors="coerce").fillna(0),
        "sgst": pd.to_numeric(df.get("SGST", 0), errors="coerce").fillna(0),
        "cgst": pd.to_numeric(df.get("CGST", 0), errors="coerce").fillna(0),
        "igst": pd.to_numeric(df.get("IGST", 0), errors="coerce").fillna(0),
        "invoice_amount": pd.to_numeric(df.get("Invoice Amount", 0), errors="coerce").fillna(0),
        "quantity_consumed": pd.to_numeric(df.get("Quantity Consume", 0), errors="coerce").fillna(0),
        "balance_quantity": pd.to_numeric(df.get("Balance Quantity", 0), errors="coerce").fillna(0),
        "purchase_date": pd.to_datetime(df["Invoice Date"], errors="coerce", dayfirst=True),
    })
    out = out.dropna(subset=["quantity"])
    out = out[out["quantity"] > 0]
    return out


def load_packing():
    df = _load_india_style_sheet("PACKING MATERIAL")
    out = pd.DataFrame({
        "supplier": df["Supplier"].astype(str).str.strip(),
        "invoice_no": df["Invoice No."].astype(str).str.strip(),
        "item_description": df["Item Description"].astype(str).str.strip(),
        "hsn_code": df.get("HSN Code", "").astype(str),
        "quantity": pd.to_numeric(df.iloc[:, 6], errors="coerce"),  # qty column
        "unit": df.get("Unit", "").astype(str),
        "unit_price": pd.to_numeric(df.get("Rate", df.get("Unit Price", 0)), errors="coerce"),
        "total_price": pd.to_numeric(df.get("Total Price", 0), errors="coerce"),
        "freight": pd.to_numeric(df.get("Freight", 0), errors="coerce").fillna(0),
        "sgst": pd.to_numeric(df.get("SGST", 0), errors="coerce").fillna(0),
        "cgst": pd.to_numeric(df.get("CGST", 0), errors="coerce").fillna(0),
        "igst": pd.to_numeric(df.get("IGST", 0), errors="coerce").fillna(0),
        "invoice_amount": pd.to_numeric(df.get("Invoice Amount", 0), errors="coerce").fillna(0),
        "quantity_consumed": pd.to_numeric(df.get("Quantity Consume", 0), errors="coerce").fillna(0),
        "balance_quantity": pd.to_numeric(df.get("Balance Quantity", 0), errors="coerce").fillna(0),
        "purchase_date": pd.to_datetime(df["Invoice Date"], errors="coerce", dayfirst=True),
    })
    out = out.dropna(subset=["quantity"])
    return out


def load_labour():
    df = _load_india_style_sheet("Labour Charges")
    out = pd.DataFrame({
        "supplier": df["Supplier"].astype(str).str.strip(),
        "invoice_no": df["Invoice No."].astype(str).str.strip(),
        "item_description": df["Item Description"].astype(str).str.strip(),
        "hsn_code": df.get("HSN Code", "").astype(str),
        "quantity": pd.to_numeric(df["Quantity"], errors="coerce"),
        "unit": df.get("Unit", "").astype(str),
        "unit_price": pd.to_numeric(df["Unit Price"], errors="coerce"),
        "total_price": pd.to_numeric(df["Total Price"], errors="coerce"),
        "labour_charges": pd.to_numeric(df.get("Labour Charges", 0), errors="coerce").fillna(0),
        "sgst": pd.to_numeric(df.get("SGST", 0), errors="coerce").fillna(0),
        "cgst": pd.to_numeric(df.get("CGST", 0), errors="coerce").fillna(0),
        "igst": pd.to_numeric(df.get("IGST", 0), errors="coerce").fillna(0),
        "invoice_amount": pd.to_numeric(df.get("Invoice Amount", 0), errors="coerce").fillna(0),
        "purchase_date": pd.to_datetime(df["Invoice Date"], errors="coerce", dayfirst=True),
    })
    out = out.dropna(subset=["quantity"])
    return out


def load_all_procurement_data():
    """Load all 4 sheets, insert into DB, return counts."""
    from database.db import init_db
    init_db()

    results = {}

    # Foreign purchases
    try:
        if table_row_count("purchase_import") == 0:
            df = load_foreign_purchase()
            insert_df(df, "purchase_import")
            results["purchase_import"] = len(df)
        else:
            results["purchase_import"] = table_row_count("purchase_import")
    except Exception as e:
        results["purchase_import"] = f"Error: {e}"

    # India purchases
    try:
        if table_row_count("purchase_india") == 0:
            df = load_india_purchase()
            insert_df(df, "purchase_india")
            results["purchase_india"] = len(df)
        else:
            results["purchase_india"] = table_row_count("purchase_india")
    except Exception as e:
        results["purchase_india"] = f"Error: {e}"

    # Packing
    try:
        if table_row_count("purchase_packing") == 0:
            df = load_packing()
            insert_df(df, "purchase_packing")
            results["purchase_packing"] = len(df)
        else:
            results["purchase_packing"] = table_row_count("purchase_packing")
    except Exception as e:
        results["purchase_packing"] = f"Error: {e}"

    # Labour
    try:
        if table_row_count("purchase_labour") == 0:
            df = load_labour()
            insert_df(df, "purchase_labour")
            results["purchase_labour"] = len(df)
        else:
            results["purchase_labour"] = table_row_count("purchase_labour")
    except Exception as e:
        results["purchase_labour"] = f"Error: {e}"

    return results
