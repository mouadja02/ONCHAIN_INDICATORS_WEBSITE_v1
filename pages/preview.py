import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import datetime
import random

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="Bitcoin Price Mouvement Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    body { background-color: #000000; color: #f0f2f6; }
    .css-18e3th9, .css-1dp5vir, .css-12oz5g7, .st-bq {
        background-color: #000000 !important;
    }
    .css-15zrgzn, .css-1hynb2t, .css-1xh633b, .css-17eq0hr {
        color: #f0f2f6;
    }
    .css-1xh633b a { color: #1FA2FF; }
    </style>
    """,
    unsafe_allow_html=True
)

######################################
# 2) Snowflake Connection
######################################
cx = st.connection("snowflake")
session = cx.session()

######################################
# 3) Define Color Palette & Session State
######################################
COLOR_PALETTE = ["#E74C3C", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6",
                 "#1ABC9C", "#E67E22", "#FF00FF", "#FF1493", "#FFD700"]

if "color_palette" not in st.session_state:
    st.session_state["color_palette"] = COLOR_PALETTE.copy()
    random.shuffle(st.session_state["color_palette"])

if "assigned_colors" not in st.session_state:
    st.session_state["assigned_colors"] = {}

if "colors" not in st.session_state:
    st.session_state["colors"] = {}

######################################
# 4) BTC Price Data Configuration
######################################
BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
BTC_PRICE_DATE_COL = "DATE"
BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"

######################################
# 5) Page Title
######################################
st.title("Bitcoin On-chain Indicators Dashboard")

######################################
# 6) SIDEBAR Controls
######################################
with st.sidebar:
    st.header("BTC Price Options")
    show_btc_price = st.checkbox("Show BTC Price?", value=True)
    chart_type_price = st.radio("BTC Price Chart Type", ["Line", "Bars"], index=0)
    scale_option_price = st.radio("BTC Price Axis", ["Linear", "Log"], index=0)

    st.markdown("---")
    st.header("Price Movement Detection")
    show_movement_scatter = st.checkbox("Show BTC Price Movement States?", value=True)
    movement_threshold = st.number_input("Threshold for unchanged state (%)", min_value=0.1, max_value=5.0, value=0.5)

    st.markdown("---")
    st.header("Date Range Selection")
    default_start_date = datetime.date(2015, 1, 1)
    selected_start_date = st.date_input("Start Date", value=default_start_date)

    activate_end_date = st.checkbox("Activate End Date", value=False)
    if activate_end_date:
        default_end_date = datetime.date.today()
        selected_end_date = st.date_input("End Date", value=default_end_date)
    else:
        selected_end_date = None

######################################
# 7) BTC PRICE MOVEMENT QUERY
######################################
btc_movement_query = f"""
    WITH price_changes AS (
        SELECT 
            CAST(DATE AS DATE) AS DATE,
            BTC_PRICE_USD,
            LAG(BTC_PRICE_USD) OVER (ORDER BY DATE) AS previous_price
        FROM {BTC_PRICE_TABLE}
    )
    SELECT 
        DATE,
        BTC_PRICE_USD,
        CASE 
            WHEN previous_price IS NULL THEN NULL  
            WHEN BTC_PRICE_USD > previous_price * (1 + {movement_threshold} / 100) THEN 1  
            WHEN BTC_PRICE_USD < previous_price * (1 - {movement_threshold} / 100) THEN -1  
            ELSE 0  
        END AS PRICE_MOVEMENT
    FROM price_changes
    WHERE BTC_PRICE_USD IS NOT NULL
      AND DATE >= '{selected_start_date}'
"""

if selected_end_date:
    btc_movement_query += f" AND DATE <= '{selected_end_date}'"

btc_movement_query += " ORDER BY DATE"

df_btc_movement = session.sql(btc_movement_query).to_pandas()

# Map movement states to colors
color_map = {1: "#2ECC71", 0: "#F1C40F", -1: "#E74C3C"}  
df_btc_movement["Color"] = df_btc_movement["PRICE_MOVEMENT"].map(color_map)

######################################
# 8) MAIN PLOT (BTC Price + Scatter)
######################################
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Plot BTC Price (Line or Bar)
if show_btc_price:
    if chart_type_price == "Line":
        fig.add_trace(
            go.Scatter(
                x=df_btc_movement["DATE"],
                y=df_btc_movement["BTC_PRICE_USD"],
                mode="lines",
                name="BTC Price (USD)",
                line=dict(color="#3498DB")
            ),
            secondary_y=True
        )
    else:
        fig.add_trace(
            go.Bar(
                x=df_btc_movement["DATE"],
                y=df_btc_movement["BTC_PRICE_USD"],
                name="BTC Price (USD)",
                marker_color="#3498DB"
            ),
            secondary_y=True
        )

# Scatter plot for BTC Price Movement States
if show_movement_scatter:
    fig.add_trace(
        go.Scatter(
            x=df_btc_movement["DATE"],
            y=df_btc_movement["BTC_PRICE_USD"],
            mode="markers",
            marker=dict(color=df_btc_movement["Color"], size=6),
            name="BTC Price Movement"
        ),
        secondary_y=True
    )

# Update Layout
fig.update_layout(
    title="Bitcoin Price & Movement States",
    xaxis_title="Date",
    yaxis_title="BTC Price (USD)",
    hovermode="x unified",
    font=dict(color="#f0f2f6"),
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
)

# Update Axis
fig.update_yaxes(
    title_text="BTC Price (USD)",
    type="log" if scale_option_price == "Log" else "linear",
    secondary_y=True,
    gridcolor="#4f5b66"
)

# Display Plot
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
**Legend:**  
🟢 **Green (🔼 Increase, > Threshold for unchanged state)**  
🟡 **Yellow (⏸ Unchanged, within ± Threshold for unchanged state)**  
🔴 **Red (🔽 Decrease, > Threshold for unchanged state)**
""", unsafe_allow_html=True)




st.title("Correlation Matrix of On-chain Features")


######################################
# Table Configurations
######################################
TABLE_DICT = {
    "ACTIVE ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "ADDRESSES PROFIT LOSS PERCENT": {
        "table_name": "BTC_DATA.DATA.ADDRESSES_PROFIT_LOSS_PERCENT",
        "date_col": "sale_date", 
        "numeric_cols": ["PERCENT_PROFIT", "PERCENT_LOSS"]
    },
    "REALIZED CAP AND PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
        "date_col": "DATE",
        "numeric_cols": [
            "REALIZED_CAP_USD",
            "REALIZED_PRICE_USD",
            "TOTAL_UNSPENT_BTC"
        ]
    },
    "BTC PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_USD",
        "date_col": "DATE",
        "numeric_cols": [
            "BTC_>PRICE_USD",
        ]
    },
    "BTC PRICE MOUVEMENT": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_MOVEMENT",
        "date_col": "DATE",
        "numeric_cols": [
            "PRICE_MOVEMENT"
        ]
    },
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",
        "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
    },
    "EXCHANGE_FLOW": {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
        "date_col": "DAY",
        "numeric_cols": ["INFLOW", "OUTFLOW", "NETFLOW"]
    },
    "HOLDER REALIZED PRICES": {
        "table_name": "BTC_DATA.DATA.HOLDER_REALIZED_PRICES",
        "date_col": "DATE",
        "numeric_cols": ["SHORT_TERM_HOLDER_REALIZED_PRICE", "LONG_TERM_HOLDER_REALIZED_PRICE"]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",
        "numeric_cols": ["MVRV"]
    },
    "MVRV WITH HOLDER TYPES": {
        "table_name": "BTC_DATA.DATA.MVRV_WITH_HOLDER_TYPES",
        "date_col": "DATE",
        "numeric_cols": ["OVERALL_MVRV", "STH_MVRV", "LTH_MVRV"]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "date_col": "DATE",
        "numeric_cols": ["NUPL", "NUPL_PERCENT"]
    },
    "REALIZED_CAP_VS_MARKET_CAP": {
        "table_name": "BTC_DATA.DATA.REALIZED_CAP_VS_MARKET_CAP",
        "date_col": "DATE",
        "numeric_cols": ["MARKET_CAP_USD", "REALIZED_CAP_USD"]
    },
    "SOPR": {
        "table_name": "BTC_DATA.DATA.SOPR",
        "date_col": "spent_date",
        "numeric_cols": ["SOPR"]
    },
    "SOPR WITH HOLDER TYPES": {
        "table_name": "BTC_DATA.DATA.SOPR_WITH_HOLDER_TYPES",
        "date_col": "sale_date",
        "numeric_cols": ["OVERALL_SOPR", "STH_SOPR", "LTH_SOPR"]
    },
    "STOCK TO FLOW MODEL": {
        "table_name": "BTC_DATA.DATA.STOCK_TO_FLOW_MODEL",
        "date_col": "DATE",
        "numeric_cols": ["STOCK", "FLOW", "STOCK_TO_FLOW", "MODEL_PRICE"]
    },
    "TX COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "BLOCK_TIMESTAMP",
        "numeric_cols": ["TX_COUNT"]
    },
    "TX VOLUME": {
        "table_name": "BTC_DATA.DATA.TX_VOLUME",
        "date_col": "DATE",
        "numeric_cols": ["DAILY_TX_VOLUME_BTC"]
    },
    "UTXO LIFECYCLE": {
        "table_name": "BTC_DATA.DATA.UTXO_LIFECYCLE",
        "date_col": "CREATED_TIMESTAMP",
        "numeric_cols": ["BTC_VALUE"]
    },
    "PUELL MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINTED_BTC",
            "DAILY_ISSUANCE_USD",
            "MA_365_ISSUANCE_USD",
            "PUELL_MULTIPLE"
        ]
    },
}
######################################
# Sidebar Controls
######################################
with st.sidebar:
    st.header("Correlation Settings")
    
    # Let user select one or more tables for correlation analysis.
    selected_tables = st.multiselect(
        "Select tables to include:",
        list(TABLE_DICT.keys()),
        default=list(TABLE_DICT.keys())[:3],
        help="Choose the on-chain tables you want to analyze."
    )
    
    # Date range: Start date and optional End date.
    default_start_date = datetime.date(2015, 1, 1)
    start_date = st.date_input("Start Date", value=default_start_date)
    
    activate_end_date = st.checkbox("Activate End Date", value=False)
    if activate_end_date:
        default_end_date = datetime.date.today()
        end_date = st.date_input("End Date", value=default_end_date)
    else:
        end_date = None

######################################
# Data Query & Merge
######################################
df_list = []
for tbl in selected_tables:
    tbl_info = TABLE_DICT[tbl]
    date_col = tbl_info["date_col"]
    numeric_cols = tbl_info["numeric_cols"]
    # Build the query for this table
    cols_for_query = ", ".join(numeric_cols)
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {cols_for_query}
        FROM {tbl_info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{start_date}'
    """
    if end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date}'\n"
    query += "ORDER BY DATE"
    
    df = session.sql(query).to_pandas()
    # Rename numeric columns to include table name prefix (to avoid duplicate names)
    rename_dict = {col: f"{tbl}:{col}" for col in numeric_cols}
    df.rename(columns=rename_dict, inplace=True)
    df_list.append(df)

if not df_list:
    st.error("No tables selected or no data returned.")
    st.stop()

# Merge all dataframes on DATE using outer join
merged_df = df_list[0]
for df in df_list[1:]:
    merged_df = pd.merge(merged_df, df, on="DATE", how="outer")
merged_df.sort_values("DATE", inplace=True)

# Option: drop rows where all values are NaN
merged_df = merged_df.dropna(how="all")

######################################
# Compute Correlation Matrix
######################################
# Remove the DATE column for correlation computation
corr_matrix = merged_df.drop(columns=["DATE"]).corr()

######################################
# Plot Correlation Heatmap
######################################
st.subheader("Correlation Matrix Heatmap")
fig = px.imshow(corr_matrix,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                origin="lower",
                title="Correlation Matrix of On-chain Features")
st.plotly_chart(fig, use_container_width=True)

