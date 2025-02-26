# onchain_indicators.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import random
import ruptures as rpt

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="On-chain Indicators Dashboard",
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
COLOR_PALETTE = [
    "#E74C3C", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6",
    "#1ABC9C", "#E67E22", "#FF00FF", "#FF1493", "#FFD700"
]
if "color_palette" not in st.session_state:
    st.session_state["color_palette"] = COLOR_PALETTE.copy()
    random.shuffle(st.session_state["color_palette"])

if "assigned_colors" not in st.session_state:
    st.session_state["assigned_colors"] = {}
if "colors" not in st.session_state:
    st.session_state["colors"] = {}

######################################
# 4) Table Configurations
######################################
TABLE_DICT = {
    "ACTIVE_ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "ADDRESSES_PROFIT_LOSS_PERCENT": {
        "table_name": "BTC_DATA.DATA.ADDRESSES_PROFIT_LOSS_PERCENT",
        "date_col": "sale_date", 
        "numeric_cols": ["PERCENT_PROFIT","PERCENT_LOSS"]
    },
    "BTC_REALIZED_CAP_AND_PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
        "date_col": "DATE",
        "numeric_cols": [
            "REALIZED_CAP_USD",
            "REALIZED_PRICE_USD",
            "TOTAL_UNSPENT_BTC"
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
    "HOLDER_REALIZED_PRICES": {
        "table_name": "BTC_DATA.DATA.HOLDER_REALIZED_PRICES",
        "date_col": "DATE",
        "numeric_cols": ["SHORT_TERM_HOLDER_REALIZED_PRICE", "LONG_TERM_HOLDER_REALIZED_PRICE"]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",
        "numeric_cols": ["MVRV"]
    },
    "MVRV_WITH_HOLDER_TYPES": {
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
    "SOPR_WITH_HOLDER_TYPES": {
        "table_name": "BTC_DATA.DATA.SOPR_WITH_HOLDER_TYPES",
        "date_col": "sale_date",
        "numeric_cols": ["OVERALL_SOPR","STH_SOPR","LTH_SOPR"]
    },
    "TX_COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "BLOCK_TIMESTAMP",
        "numeric_cols": ["TX_COUNT"]
    },
    "TX_VOLUME": {
        "table_name": "BTC_DATA.DATA.TX_VOLUME",
        "date_col": "DATE",
        "numeric_cols": ["DAILY_TX_VOLUME_BTC"]
    },
    "UTXO_LIFECYCLE": {
        "table_name": "BTC_DATA.DATA.UTXO_LIFECYCLE",
        "date_col": "CREATED_TIMESTAMP",
        "numeric_cols": ["BTC_VALUE"]
    },
    "PUELL_MULTIPLE": {
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
    st.header("Select On-chain Indicator")
    # Choose one table
    selected_table = st.selectbox(
        "Select a Table (Metric Set)",
        list(TABLE_DICT.keys()),
        help="Pick which table (indicator set) to visualize."
    )
    table_info = TABLE_DICT[selected_table]
    all_numeric_cols = table_info["numeric_cols"]
    selected_cols = st.multiselect(
        "Select Indicator(s):",
        all_numeric_cols,
        default=all_numeric_cols,
        help="Pick one or more numeric columns to plot."
    )

    st.markdown("---")
    st.header("Chart Options")

    default_start_date = datetime.date(2015, 1, 1)
    selected_start_date = st.date_input(
        "Start Date",
        value=default_start_date
    )

    scale_option_indicator = st.radio("Indicator Axis Scale", ["Linear", "Log"], index=0)
    chart_type_indicators = st.radio("Indicator Chart Type", ["Line", "Bars"], index=0)

    show_ema = st.checkbox("Add EMA for Indicators", value=False)
    if show_ema:
        ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20)

    st.markdown("---")
    st.header("BTC Price Options")

    show_btc_price = st.checkbox("Show BTC Price?", value=True)
    same_axis_checkbox = st.checkbox("Plot BTC Price on same Y-axis?", value=False)
    chart_type_price = st.radio("BTC Price Chart Type", ["Line", "Bars"], index=0)
    scale_option_price = st.radio("BTC Price Axis", ["Linear", "Log"], index=0)
    detect_cpd = st.checkbox("Detect BTC Price Change Points?", value=False)
    if detect_cpd:
        pen_value = st.number_input("CPD Penalty", min_value=1, max_value=200, value=10)

######################################
# 7) MAIN CHART
######################################
if not selected_cols:
    st.warning("Please select at least one indicator column.")
    st.stop()

# Assign colors
for i, col in enumerate(selected_cols):
    if col not in st.session_state["assigned_colors"]:
        color_assigned = st.session_state["color_palette"][i % len(st.session_state["color_palette"])]
        st.session_state["assigned_colors"][col] = color_assigned
    default_color = st.session_state["assigned_colors"][col]
    picked_color = st.color_picker(f"Color for {col}", default_color)
    st.session_state["assigned_colors"][col] = picked_color
    st.session_state["colors"][col] = picked_color

if show_btc_price:
    if "BTC_PRICE" not in st.session_state["assigned_colors"]:
        idx = len(selected_cols) % len(st.session_state["color_palette"])
        st.session_state["assigned_colors"]["BTC_PRICE"] = st.session_state["color_palette"][idx]
    default_btc_color = st.session_state["assigned_colors"]["BTC_PRICE"]
    picked_btc_color = st.color_picker("Color for BTC Price", default_btc_color)
    st.session_state["assigned_colors"]["BTC_PRICE"] = picked_btc_color
    st.session_state["colors"]["BTC_PRICE"] = picked_btc_color

# Query the chosen table
date_col = table_info["date_col"]
cols_for_query = ", ".join(selected_cols)
query = f"""
    SELECT
        CAST({date_col} AS DATE) AS IND_DATE,
        {cols_for_query}
    FROM {table_info['table_name']}
    WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
    ORDER BY IND_DATE
"""
df_indicators = session.sql(query).to_pandas()
df_indicators.rename(columns={"IND_DATE": "DATE"}, inplace=True)

# Query BTC Price if requested
df_btc = pd.DataFrame()
if show_btc_price:
    btc_query = f"""
        SELECT
            CAST({BTC_PRICE_DATE_COL} AS DATE) AS PRICE_DATE,
            {BTC_PRICE_VALUE_COL}
        FROM {BTC_PRICE_TABLE}
        WHERE {BTC_PRICE_VALUE_COL} IS NOT NULL
          AND CAST({BTC_PRICE_DATE_COL} AS DATE) >= '{selected_start_date}'
        ORDER BY PRICE_DATE
    """
    df_btc = session.sql(btc_query).to_pandas()
    df_btc.rename(columns={"PRICE_DATE": "DATE"}, inplace=True)

if df_indicators.empty and df_btc.empty:
    st.warning("No data returned. Check your date range or table selection.")
    st.stop()

# Merge if BTC Price is shown
if show_btc_price and not df_btc.empty:
    merged_df = pd.merge(df_btc, df_indicators, on="DATE", how="inner")
else:
    merged_df = df_indicators

if merged_df.empty:
    st.warning("No overlapping data. Check your date range or table selection.")
    st.stop()

# Calculate EMA
if show_ema:
    for col in selected_cols:
        merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()

# Build Plotly figure
fig = make_subplots(specs=[[{"secondary_y": True}]])
# Plot indicators on primary axis
for col in selected_cols:
    if chart_type_indicators == "Line":
        fig.add_trace(
            go.Scatter(
                x=merged_df["DATE"],
                y=merged_df[col],
                mode="lines",
                name=col,
                line=dict(color=st.session_state["colors"][col])
            ),
            secondary_y=False
        )
    else:
        fig.add_trace(
            go.Bar(
                x=merged_df["DATE"],
                y=merged_df[col],
                name=col,
                marker_color=st.session_state["colors"][col]
            ),
            secondary_y=False
        )
    if show_ema:
        ema_col = f"EMA_{col}"
        if ema_col in merged_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df[ema_col],
                    mode="lines",
                    name=f"EMA({ema_period}) - {col}",
                    line=dict(color=st.session_state["colors"][col], dash="dot")
                ),
                secondary_y=False
            )

# Plot BTC Price
if show_btc_price and "BTC_PRICE_USD" in df_btc.columns:
    # Actually after rename, the col is BTC_PRICE_USD in df_btc. But we merged with the same name?
    # We can just use merged_df[BTC_PRICE_VALUE_COL].
    # We'll assume the user wants to call it "BTC_PRICE" in the final chart name.
    price_secondary = not same_axis_checkbox
    if chart_type_price == "Line":
        fig.add_trace(
            go.Scatter(
                x=merged_df["DATE"],
                y=merged_df[BTC_PRICE_VALUE_COL],
                mode="lines",
                name="BTC Price (USD)",
                line=dict(color=st.session_state["colors"]["BTC_PRICE"])
            ),
            secondary_y=price_secondary
        )
    else:
        fig.add_trace(
            go.Bar(
                x=merged_df["DATE"],
                y=merged_df[BTC_PRICE_VALUE_COL],
                name="BTC Price (USD)",
                marker_color=st.session_state["colors"]["BTC_PRICE"]
            ),
            secondary_y=price_secondary
        )

    # CPD if enabled
    if detect_cpd:
        btc_series = merged_df[BTC_PRICE_VALUE_COL].dropna()
        if not btc_series.empty:
            algo = rpt.Pelt(model="rbf").fit(btc_series.values)
            change_points = algo.predict(pen=pen_value)
            for cp in change_points:
                if cp < len(merged_df):
                    cp_date = merged_df["DATE"].iloc[cp]
                    fig.add_vline(x=cp_date, line_width=2, line_dash="dash", line_color="white")

fig_title = f"{selected_table} vs BTC Price" if show_btc_price else f"{selected_table}"
fig.update_layout(
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    title=fig_title,
    hovermode="x unified",
    font=dict(color="#f0f2f6"),
    legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
)
fig.update_xaxes(title_text="Date", gridcolor="#4f5b66")
fig.update_yaxes(
    title_text="Indicator Value",
    type="log" if scale_option_indicator == "Log" else "linear",
    secondary_y=False,
    gridcolor="#4f5b66"
)
fig.update_yaxes(
    title_text="BTC Price (USD)" if not same_axis_checkbox else "",
    type="log" if scale_option_price == "Log" else "linear",
    secondary_y=True,
    gridcolor="#4f5b66"
)

config = {
    'editable': True,
    'modeBarButtonsToAdd': [
        'drawline','drawopenpath','drawclosedpath','drawcircle','drawrect','eraseshape'
    ]
}
st.plotly_chart(fig, use_container_width=True, config=config)
