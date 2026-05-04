import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io
from database.db import init_db, list_tables, query_df

st.set_page_config(page_title="Graph Builder | ZERA Analytics", page_icon="📉", layout="wide")
init_db()

st.markdown("## 📉 Graph Builder")
st.caption("Tableau-style visualization — pick a table, choose columns, select chart type, and plot")
st.divider()

tables = list_tables()
if not tables:
    st.warning("No data loaded. Go to Home or Data Manager to load data first.")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION PANEL
# ═══════════════════════════════════════════════════════════════
st.markdown("### ⚙️ Chart Configuration")

conf_col1, conf_col2 = st.columns([1, 1])

with conf_col1:
    selected_table = st.selectbox("📂 Data Source (Table)", tables, key="gb_table")
    df = query_df(f"SELECT * FROM {selected_table}")

    if len(df) == 0:
        st.warning("Selected table is empty.")
        st.stop()

    st.caption(f"{len(df):,} rows × {len(df.columns)} columns")

    # Separate numeric and categorical columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
    all_cols = df.columns.tolist()
    date_cols = [c for c in all_cols if "date" in c.lower() or "time" in c.lower() or "datetime" in c.lower()]

with conf_col2:
    chart_type = st.selectbox(
        "📊 Chart Type",
        [
            "Bar Chart", "Horizontal Bar", "Grouped Bar",
            "Line Chart", "Area Chart",
            "Scatter Plot", "Bubble Chart",
            "Pie Chart", "Donut Chart",
            "Histogram", "Box Plot",
            "Treemap", "Sunburst",
            "Heatmap",
        ],
        key="gb_chart"
    )

st.divider()

# ═══════════════════════════════════════════════════════════════
# AXIS & PARAMETER SELECTION (adapts to chart type)
# ═══════════════════════════════════════════════════════════════
st.markdown("### 🎯 Select Columns")

ax_col1, ax_col2, ax_col3 = st.columns(3)

x_col, y_col, color_col, size_col = None, None, None, None

with ax_col1:
    if chart_type in ["Pie Chart", "Donut Chart"]:
        x_col = st.selectbox("🏷️ Labels (Names)", all_cols, key="gb_x")
    elif chart_type in ["Histogram"]:
        x_col = st.selectbox("📊 Column to histogram", all_cols, key="gb_x")
    elif chart_type == "Heatmap":
        x_col = st.selectbox("↔️ X-Axis", all_cols, key="gb_x")
    else:
        x_col = st.selectbox("↔️ X-Axis", all_cols, index=0, key="gb_x")

with ax_col2:
    if chart_type in ["Pie Chart", "Donut Chart"]:
        y_col = st.selectbox("📏 Values", numeric_cols if numeric_cols else all_cols, key="gb_y")
    elif chart_type == "Histogram":
        bins = st.slider("Number of bins", 5, 100, 30, key="gb_bins")
    elif chart_type == "Heatmap":
        y_col = st.selectbox("↕️ Y-Axis", all_cols, index=min(1, len(all_cols)-1), key="gb_y")
    elif chart_type in ["Box Plot"]:
        y_col = st.selectbox("↕️ Value Column", numeric_cols if numeric_cols else all_cols, key="gb_y")
    else:
        default_y = 1 if len(all_cols) > 1 else 0
        y_col = st.selectbox("↕️ Y-Axis", all_cols, index=default_y, key="gb_y")

with ax_col3:
    if chart_type not in ["Histogram", "Heatmap"]:
        color_options = ["(none)"] + all_cols
        color_col = st.selectbox("🎨 Color By", color_options, key="gb_color")
        if color_col == "(none)":
            color_col = None

    if chart_type in ["Scatter Plot", "Bubble Chart"]:
        size_options = ["(none)"] + numeric_cols
        size_col = st.selectbox("📏 Size By", size_options, key="gb_size")
        if size_col == "(none)":
            size_col = None

# ── OPTIONAL: Aggregation ─────────────────────────────────────
with st.expander("🔧 Aggregation (optional)", expanded=False):
    agg_col1, agg_col2 = st.columns(2)
    with agg_col1:
        do_agg = st.checkbox("Aggregate data before plotting", key="gb_agg")
    with agg_col2:
        agg_func = st.selectbox("Function", ["sum", "mean", "count", "min", "max", "median"], key="gb_agg_func")

    if do_agg and x_col and y_col and chart_type not in ["Histogram", "Pie Chart", "Donut Chart"]:
        try:
            if agg_func == "count":
                df = df.groupby(x_col).size().reset_index(name=y_col)
            else:
                df = df.groupby(x_col).agg({y_col: agg_func}).reset_index()
            st.success(f"Aggregated: {agg_func}({y_col}) grouped by {x_col} → {len(df):,} rows")
        except Exception as e:
            st.warning(f"Aggregation failed: {e}")

# ── Chart Title ───────────────────────────────────────────────
chart_title = st.text_input("📝 Chart Title (optional)", value="", key="gb_title")
if not chart_title:
    chart_title = f"{chart_type}: {selected_table}"

st.divider()

# ═══════════════════════════════════════════════════════════════
# RENDER CHART
# ═══════════════════════════════════════════════════════════════
st.markdown("### 📊 Visualization")

try:
    fig = None
    color_seq = px.colors.qualitative.Set2

    if chart_type == "Bar Chart":
        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=chart_title,
                     color_discrete_sequence=color_seq)

    elif chart_type == "Horizontal Bar":
        fig = px.bar(df, x=y_col, y=x_col, color=color_col, orientation="h",
                     title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Grouped Bar":
        fig = px.bar(df, x=x_col, y=y_col, color=color_col, barmode="group",
                     title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Line Chart":
        fig = px.line(df.sort_values(x_col), x=x_col, y=y_col, color=color_col,
                      title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Area Chart":
        fig = px.area(df.sort_values(x_col), x=x_col, y=y_col, color=color_col,
                      title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Scatter Plot":
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, size=size_col,
                         title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Bubble Chart":
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, size=size_col,
                         title=chart_title, size_max=40, color_discrete_sequence=color_seq)

    elif chart_type == "Pie Chart":
        fig = px.pie(df, names=x_col, values=y_col, title=chart_title,
                     color_discrete_sequence=color_seq)

    elif chart_type == "Donut Chart":
        fig = px.pie(df, names=x_col, values=y_col, title=chart_title,
                     hole=0.45, color_discrete_sequence=color_seq)

    elif chart_type == "Histogram":
        fig = px.histogram(df, x=x_col, nbins=bins, color=color_col,
                          title=chart_title, color_discrete_sequence=color_seq)

    elif chart_type == "Box Plot":
        fig = px.box(df, x=x_col, y=y_col, color=color_col, title=chart_title,
                     color_discrete_sequence=color_seq)

    elif chart_type == "Treemap":
        path_cols = [x_col]
        if color_col:
            path_cols = [color_col, x_col]
        fig = px.treemap(df, path=path_cols, values=y_col, title=chart_title,
                        color_discrete_sequence=color_seq)

    elif chart_type == "Sunburst":
        path_cols = [x_col]
        if color_col:
            path_cols = [color_col, x_col]
        fig = px.sunburst(df, path=path_cols, values=y_col, title=chart_title,
                         color_discrete_sequence=color_seq)

    elif chart_type == "Heatmap":
        # Pivot for heatmap
        try:
            pivot = df.pivot_table(index=y_col, columns=x_col, aggfunc="size", fill_value=0)
            fig = px.imshow(pivot, title=chart_title, color_continuous_scale="Viridis",
                           aspect="auto")
        except Exception:
            st.warning("Could not create heatmap — try different X and Y columns with categorical data.")

    if fig:
        fig.update_layout(
            height=550, margin=dict(t=60, b=40, l=40, r=40),
            font=dict(size=12)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Download chart as image
        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            html_bytes = fig.to_html(include_plotlyjs="cdn").encode()
            st.download_button(
                "⬇️ Download Chart (HTML)",
                html_bytes,
                file_name=f"{chart_title.replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True
            )
        with dl2:
            csv_data = df.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Data (CSV)",
                csv_data,
                file_name=f"{selected_table}_chart_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        with dl3:
            try:
                img_bytes = fig.to_image(format="png", width=1200, height=600)
                st.download_button(
                    "⬇️ Download Chart (PNG)",
                    img_bytes,
                    file_name=f"{chart_title.replace(' ', '_')}.png",
                    mime="image/png",
                    use_container_width=True
                )
            except Exception:
                st.caption("PNG export requires `kaleido` package. HTML export available.")
    else:
        st.info("Configure the chart options above and a visualization will appear here.")

except Exception as e:
    st.error(f"Chart rendering error: {e}")
    st.info("💡 Try selecting different columns or a different chart type for this data.")

# ── Data preview ──────────────────────────────────────────────
with st.expander("📋 Preview Source Data"):
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)
