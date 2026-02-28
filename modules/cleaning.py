import pandas as pd
import numpy as np


def safe_float(val):
    """Convert a value to float, handling commas, currency symbols, units."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # Remove currency, units, commas
    for ch in ["₹", "$", ",", " ", "A", "V", "W", "Wh", "VAh"]:
        s = s.replace(ch, "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def standardize_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def clean_numeric_columns(df):
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                cleaned = df[col].str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("₹", "", regex=False)
                numeric = pd.to_numeric(cleaned, errors="coerce")
                if numeric.notna().sum() > len(df) * 0.3:
                    df[col] = numeric
            except (AttributeError, TypeError):
                pass
    return df


def clean_dataframe(df):
    df = standardize_columns(df)
    df = clean_numeric_columns(df)
    df = df.dropna(how="all")
    df = df.reset_index(drop=True)
    return df
