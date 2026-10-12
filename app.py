
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Supply Chain Analytics",
    page_icon="📦",
    layout="wide"
)

# CUSTOM STYLING
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
    }
    [data-testid="stMetric"] {
        background-color: #f1f5f9;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    [data-testid="stMetricLabel"] {
        color: #334155;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a;
    }
</style>
""", unsafe_allow_html=True)

# LOAD DATA
@st.cache_data
def load_data():
    file_path = Path(__file__).parent / "supply_chain_practice.csv"
    data = pd.read_csv(file_path)
    data.columns = data.columns.str.strip()
    data = data.drop_duplicates().copy()

    data["Snapshot Date"] = pd.to_datetime(
        data["Snapshot Date"], errors="coerce"
    )

    numeric_cols = [
        "Free Stock", "On Order", "Weekly Sales",
        "Unit Cost GBP", "Lead Time Days"
    ]

    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    return data

try:
    df = load_data()
except Exception as error:
    st.error(f"Unable to load CSV: {error}")
    st.stop()

# SIDEBAR
st.sidebar.title("📦 Supply Chain")
st.sidebar.caption("Inventory Analytics Dashboard")
st.sidebar.divider()

st.sidebar.subheader("Filters")

supplier_options = sorted(df["Supplier"].dropna().unique())
warehouse_options = sorted(df["Warehouse"].dropna().unique())
status_options = sorted(df["Product Status"].dropna().unique())

selected_suppliers = st.sidebar.multiselect(
    "Supplier",
    supplier_options,
    default=supplier_options
)

selected_warehouses = st.sidebar.multiselect(
    "Warehouse",
    warehouse_options,
    default=warehouse_options
)

selected_statuses = st.sidebar.multiselect(
    "Product Status",
    status_options,
    default=status_options
)

low_stock_limit = st.sidebar.slider(
    "Low Stock Threshold",
    min_value=0,
    max_value=500,
    value=50,
    step=10
)

filtered = df[
    df["Supplier"].isin(selected_suppliers)
    & df["Warehouse"].isin(selected_warehouses)
    & df["Product Status"].isin(selected_statuses)
].copy()

# SNAPSHOT SELECTION
st.sidebar.divider()
st.sidebar.subheader("Snapshot")

valid_dates = filtered["Snapshot Date"].dropna()

if not valid_dates.empty:
    latest_date = valid_dates.max()
    selected_date = st.sidebar.selectbox(
        "Inventory Snapshot Date",
        sorted(valid_dates.dt.date.unique(), reverse=True)
    )

    snapshot = filtered[
        filtered["Snapshot Date"].dt.date == selected_date
    ].copy()
else:
    selected_date = None
    snapshot = filtered.iloc[0:0].copy()

st.sidebar.caption(
    "Stock KPIs use one selected snapshot date to avoid "
    "adding inventory from multiple weeks together."
)

# HEADER
st.title("📊 Supply Chain Analytics Dashboard")
st.caption(
    "Inventory Visibility | Supplier Performance | "
    "Demand Planning Portfolio"
)

if selected_date:
    st.info(f"Viewing inventory snapshot: {selected_date}")

if snapshot.empty:
    st.warning("No records match the selected filters and date.")
    st.stop()

# KPI CALCULATIONS
total_skus = snapshot["SKU"].nunique()
total_stock = snapshot["Free Stock"].sum()
total_on_order = snapshot["On Order"].sum()
total_suppliers = snapshot["Supplier"].nunique()

low_stock = snapshot[
    snapshot["Free Stock"].notna()
    & (snapshot["Free Stock"] < low_stock_limit)
].copy()

missing_stock = snapshot["Free Stock"].isna().sum()
missing_sales = snapshot["Weekly Sales"].isna().sum()

# KPI CARDS
col1, col2, col3, col4 = st.columns(4)

col1.metric("Unique SKUs", f"{total_skus:,}")
col2.metric("Free Stock", f"{total_stock:,.0f}")
col3.metric("On Order", f"{total_on_order:,.0f}")
col4.metric("Suppliers", f"{total_suppliers:,}")

st.write("")

col5, col6, col7 = st.columns(3)

col5.metric("Low Stock Records", len(low_stock))
col6.metric("Missing Stock Values", int(missing_stock))
col7.metric("Missing Sales Values", int(missing_sales))

st.divider()

# STOCK ANALYSIS
left, right = st.columns(2)

with left:
    st.subheader("📦 Free Stock by Supplier")

    supplier_stock = (
        snapshot.groupby("Supplier", as_index=False)
        .agg({"Free Stock": "sum"})
        .sort_values("Free Stock", ascending=False)
    )

    fig_supplier = px.bar(
        supplier_stock,
        x="Supplier",
        y="Free Stock",
        color="Supplier",
        text_auto=".0f",
        title="Supplier Stock Distribution"
    )

    fig_supplier.update_layout(
        showlegend=False,
        height=390,
        xaxis_title="",
        yaxis_title="Free Stock"
    )

    st.plotly_chart(fig_supplier, use_container_width=True)

with right:
    st.subheader("🏭 Free Stock by Warehouse")

    warehouse_stock = (
        snapshot.groupby("Warehouse", as_index=False)
        .agg({"Free Stock": "sum"})
    )

    fig_warehouse = px.pie(
        warehouse_stock,
        names="Warehouse",
        values="Free Stock",
        hole=0.55,
        title="Warehouse Stock Distribution"
    )

    fig_warehouse.update_layout(height=390)

    st.plotly_chart(fig_warehouse, use_container_width=True)

st.divider()

# SALES ANALYSIS
st.subheader("📈 Top 10 Products by Weekly Sales")

top_products = (
    snapshot.groupby(["SKU", "Product"], as_index=False)
    .agg({"Weekly Sales": "sum"})
    .nlargest(10, "Weekly Sales")
)

fig_sales = px.bar(
    top_products,
    x="Weekly Sales",
    y="Product",
    orientation="h",
    color="Weekly Sales",
    color_continuous_scale="Blues",
    title="Highest Weekly Sales"
)

fig_sales.update_layout(
    height=450,
    yaxis={"categoryorder": "total ascending"},
    coloraxis_showscale=False
)

st.plotly_chart(fig_sales, use_container_width=True)

st.divider()

# LOW STOCK
st.subheader("🚨 Low Stock Alerts")

st.caption(
    f"Products with Free Stock below {low_stock_limit} units."
)

if low_stock.empty:
    st.success("No low-stock records found.")
else:
    st.dataframe(
        low_stock[
            [
                "SKU", "Product", "Supplier",
                "Warehouse", "Free Stock",
                "On Order", "Weekly Sales"
            ]
        ].sort_values("Free Stock"),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# INVENTORY DETAIL
st.subheader("📋 Inventory Details")

st.dataframe(
    snapshot,
    use_container_width=True,
    hide_index=True
)

# DOWNLOAD
csv_data = snapshot.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Inventory",
    data=csv_data,
    file_name="filtered_inventory.csv",
    mime="text/csv"
)

st.divider()

# DATA QUALITY
with st.expander("🔎 Data Quality Report"):
    st.write("Missing values across the full dataset:")
    st.dataframe(
        df.isnull().sum().rename("Missing Values"),
        use_container_width=True
    )

    st.write(f"Rows after duplicate removal: {len(df)}")

st.caption(
    "Portfolio Project | Built with Python, Pandas, "
    "Plotly and Streamlit"
)
