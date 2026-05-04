import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import io
from database.db import (
    init_db, list_tables, query_df, table_row_count,
    upload_dataframe_to_db, get_table_schema
)

st.set_page_config(page_title="Data Manager | ZERA Analytics", page_icon="📤", layout="wide")
init_db()

st.markdown("## 📤 Data Manager")
st.caption("Upload new data files, explore any table with filters, and download results")
st.divider()

# ═══════════════════════════════════════════════════════════════
# SECTION 1: FILE UPLOAD
# ═══════════════════════════════════════════════════════════════
st.markdown("### 📁 Upload New Data")

col_up1, col_up2 = st.columns([2, 1])

with col_up1:
    uploaded_files = st.file_uploader(
        "Upload Excel (.xlsx) or CSV files — each file becomes a queryable table",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key="data_mgr_upload"
    )

with col_up2:
    st.markdown("**Upload options**")
    table_prefix = st.text_input("Table name prefix", value="uploaded", help="Tables will be named: prefix_filename")
    overwrite = st.checkbox("Overwrite if table exists", value=True)

if uploaded_files:
    for uf in uploaded_files:
        fname = uf.name
        base = os.path.splitext(fname)[0].lower().replace(" ", "_").replace("-", "_").replace(".", "_")[:40]
        tname = f"{table_prefix}_{base}" if table_prefix else base

        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(uf)
            else:
                # For multi-sheet Excel, let user pick
                xls = pd.ExcelFile(uf)
                if len(xls.sheet_names) > 1:
                    sheet = st.selectbox(
                        f"**{fname}** has multiple sheets — pick one:",
                        xls.sheet_names, key=f"sheet_{fname}"
                    )
                    df = pd.read_excel(uf, sheet_name=sheet)
                    tname = f"{tname}_{sheet.lower().replace(' ', '_')}"
                else:
                    df = pd.read_excel(uf)

            mode = "replace" if overwrite else "append"
            n = upload_dataframe_to_db(df, tname, if_exists=mode)
            st.success(f"✅ **{fname}** → `{tname}` — {n:,} rows loaded")

            with st.expander(f"Preview: {tname} (first 5 rows)"):
                st.dataframe(df.head(5), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ **{fname}** failed: {e}")

st.divider()

# ═══════════════════════════════════════════════════════════════
# SECTION 2: TABLE EXPLORER WITH FILTERS
# ═══════════════════════════════════════════════════════════════
st.markdown("### 🔍 Explore & Filter Data")

tables = list_tables()
if not tables:
    st.info("No tables in database yet. Upload files above or load bundled data from the home page.")
    st.stop()

selected_table = st.selectbox("Select a table to explore:", tables, key="explorer_table")

if selected_table:
    df = query_df(f"SELECT * FROM {selected_table}")
    schema = get_table_schema(selected_table)

    st.markdown(f"**`{selected_table}`** — {len(df):,} rows × {len(df.columns)} columns")

    if len(df) == 0:
        st.warning("This table is empty.")
        st.stop()

    # ── FILTERS ───────────────────────────────────────────────
    st.markdown("#### 🎛️ Filters")
    filter_cols = st.multiselect(
        "Select columns to filter by:",
        df.columns.tolist(),
        key="filter_cols"
    )

    filtered_df = df.copy()

    if filter_cols:
        filter_container = st.columns(min(len(filter_cols), 4))
        for i, col in enumerate(filter_cols):
            with filter_container[i % 4]:
                unique_vals = filtered_df[col].dropna().unique()
                if len(unique_vals) <= 50 and filtered_df[col].dtype == "object":
                    # Dropdown for categorical
                    selected = st.multiselect(
                        f"**{col}**", sorted(unique_vals.astype(str)),
                        key=f"filter_{col}"
                    )
                    if selected:
                        filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]
                elif pd.api.types.is_numeric_dtype(filtered_df[col]):
                    # Range slider for numeric
                    col_min = float(filtered_df[col].min())
                    col_max = float(filtered_df[col].max())
                    if col_min < col_max:
                        rng = st.slider(
                            f"**{col}**", col_min, col_max, (col_min, col_max),
                            key=f"filter_{col}"
                        )
                        filtered_df = filtered_df[
                            (filtered_df[col] >= rng[0]) & (filtered_df[col] <= rng[1])
                        ]
                else:
                    # Text search
                    txt = st.text_input(f"**{col}** (search)", key=f"filter_{col}")
                    if txt:
                        filtered_df = filtered_df[
                            filtered_df[col].astype(str).str.contains(txt, case=False, na=False)
                        ]

    st.markdown(f"**Showing {len(filtered_df):,} of {len(df):,} rows**")

    # ── DATA TABLE ────────────────────────────────────────────
    st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=450)

    # ── QUICK STATS ───────────────────────────────────────────
    with st.expander("📊 Quick Column Statistics"):
        numeric_cols = filtered_df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            st.dataframe(
                filtered_df[numeric_cols].describe().round(2),
                use_container_width=True
            )
        else:
            st.info("No numeric columns in this table.")

    # ── DOWNLOAD ──────────────────────────────────────────────
    st.markdown("#### 📥 Download Filtered Data")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download as CSV",
            csv_data,
            file_name=f"{selected_table}_filtered.csv",
            mime="text/csv",
            use_container_width=True
        )
    with dl_col2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name=selected_table[:30])
        st.download_button(
            "⬇️ Download as Excel",
            buf.getvalue(),
            file_name=f"{selected_table}_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # ── SCHEMA INFO ───────────────────────────────────────────
    with st.expander("🗄️ Table Schema"):
        schema_df = pd.DataFrame(schema, columns=["Column", "Type"])
        st.dataframe(schema_df, use_container_width=True, hide_index=True)
