import streamlit as st
import pandas as pd
import numpy as np
import datetime
import random
import io
import math

import plotly.graph_objs as go
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="BTC Price & Indicator - Correlation & Plot",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme overrides
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
# 3) Basic Color Palette & Helpers
######################################
COLOR_PALETTE = [
    "#E74C3C", "#F1C40F", "#2ECC71", "#3498DB", 
    "#9B59B6", "#1ABC9C", "#E67E22", "#FF00FF", 
    "#FF1493", "#FFD700"
]
random.shuffle(COLOR_PALETTE)

######################################
# 4) Table Dictionary for BTC PRICE + Others
######################################
TABLE_DICT = {
    "ACTIVE ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "REALIZED CAP AND PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
        "date_col": "DATE",
        "numeric_cols": [
            "REALIZED_PRICE_USD",
            "TOTAL_UNSPENT_BTC"
        ]
    },
    "BTC PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_USD",
        "date_col": "DATE",
        "numeric_cols": [
            "BTC_PRICE_USD"
        ]
    },
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",
        "numeric_cols": ["CDD_RAW"]
    },
    "EXCHANGE_FLOW": {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
        "date_col": "DAY",
        "numeric_cols": [
            "INFLOW_BTC", "OUTFLOW_BTC", "NETFLOW_BTC", "EXCHANGE_RESERVE_BTC"
        ]
    },
    "HOLDER REALIZED PRICES": {
        "table_name": "BTC_DATA.DATA.HOLDER_REALIZED_PRICES",
        "date_col": "DATE",
        "numeric_cols": ["STH_REALIZED_PRICE", "LTH_REALIZED_PRICE"]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",
        "numeric_cols": ["MVRV"]
    },
    "MVRV WITH HOLDER TYPES": {
        "table_name": "BTC_DATA.DATA.MVRV_HOLDERS",
        "date_col": "DATE",
        "numeric_cols": ["STH_MVRV", "LTH_MVRV"]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "date_col": "DATE",
        "numeric_cols": ["NUPL"]
    },
    "PUELL MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINTED_BTC",
            "PUELL_MULTIPLE"
        ]
    },
    "M2 GROWTH": {
        "table_name": "BTC_DATA.DATA.M2_GROWTH",
        "date_col": "DATE",
        "numeric_cols": [
            "M2_GLOBAL_SUPPLY"
        ]
    },
    "SOPR": {
        "table_name": "BTC_DATA.DATA.SOPR",
        "date_col": "DATE",
        "numeric_cols": ["SOPR"]
    },
    "SOPR WITH HOLDER TYPES": {
        "table_name": "BTC_DATA.DATA.SOPR_HOLDERS",
        "date_col": "DATE",
        "numeric_cols": ["STH_SOPR", "LTH_SOPR"]
    },
    "STOCK TO FLOW MODEL": {
        "table_name": "BTC_DATA.DATA.STOCK_TO_FLOW",
        "date_col": "DATE",
        "numeric_cols": ["STOCK", "FLOW", "STOCK_TO_FLOW_RATIO"]
    },
    "TX COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "DATE",
        "numeric_cols": ["TX_COUNT"]
    },
    "TRADE VOLUME": {
        "table_name": "BTC_DATA.DATA.TRADE_VOLUME",
        "date_col": "DATE",
        "numeric_cols": [ "TRADE_VOLUME", "DOMINANCE"]
    },
    "GOOGLE TREND": {
        "table_name": "BTC_DATA.DATA.GOOGLE_TREND",
        "date_col": "DATE",
        "numeric_cols": [ "INDEX"]
    },
    "FINANCIAL MARKET DATA": {
        "table_name": "BTC_DATA.DATA.FINANCIAL_MARKET_DATA",
        "date_col": "DATE",
        "numeric_cols": [
            "NASDAQ",
            "SP500",
            "VIX",
            "DXY",
            "IWM",
            "QQQ",
            "TLT",
            "GOLD",
            "PETROL"
        ]
    },
    "FEAR & GREED INDEX": {
        "table_name": "BTC_DATA.DATA.FEAR_GREED_INDEX",
        "date_col": "DATE",
        "numeric_cols": ["FNG_VALUE"]
    },  
    "MINERS REVENUE": {
        "table_name": "BTC_DATA.DATA.MINERS_REVENUE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINER_REVENUE"
        ]
    },    
    "DAILY HASHRATE": {
        "table_name": "BTC_DATA.DATA.DAILY_HASHRATE",
        "date_col": "DATE",
        "numeric_cols": [
            "HASHRATE_THS"
        ]
    },    
    "NETWORK DIFFICULTY": {
        "table_name": "BTC_DATA.DATA.NETWORK_DIFFICULTY",
        "date_col": "DATE",
        "numeric_cols": [
            "AVG_DIFFICULTY"
        ]
    },
}

######################################
# 5) Title
######################################
st.title("BTC Price vs. Single Indicator – Lag/Derivative, Correlation & Plot")

######################################
# 6) Sidebar - Query & Transform Settings
######################################
st.sidebar.header("Configuration")

# A) Date Range
st.sidebar.subheader("Date Range")
default_start = datetime.date(2015, 1, 1)
start_date = st.sidebar.date_input("Start Date", value=default_start)
enable_end = st.sidebar.checkbox("Enable End Date", value=False)
if enable_end:
    default_end = datetime.date.today()
    end_date = st.sidebar.date_input("End Date", value=default_end)
else:
    end_date = None

# B) Correlation Method
corr_method = st.sidebar.selectbox("Correlation Method", ["pearson", "spearman"], index=0)

st.sidebar.markdown("---")

# C) BTC Price derivative
st.sidebar.subheader("BTC Price Settings")
derive_btc = st.sidebar.checkbox("Take derivative of BTC Price?", value=False)

# BTC Price always shift=0
shift_btc = 0

st.sidebar.markdown("---")

# D) Choose 1 other indicator
st.sidebar.subheader("Indicator Settings")
all_other_tables = [k for k in TABLE_DICT.keys() if k != "BTC PRICE"]
all_feats = []
for t in all_other_tables:
    for c in TABLE_DICT[t]["numeric_cols"]:
        all_feats.append(f"{t}:{c}")

indicator_choice = st.sidebar.selectbox(
    "Select One Indicator", 
    options=all_feats,
    help="Pick exactly one other feature to compare against BTC Price."
)

shift_indicator = st.sidebar.slider("Lag (days) for indicator", 0, 30, 0)
derive_indicator = st.sidebar.checkbox("Take derivative of indicator?", value=False)

st.sidebar.markdown("---")


######################################
# 7) Data Retrieval & Transform
######################################
def load_data_from_snowflake(feature_name, start_date, end_date):
    """Query a single feature from Snowflake, given start/end date constraints."""
    tbl, col = feature_name.split(":", 1)
    info = TABLE_DICT[tbl]
    date_col = info["date_col"]
    
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {col}
        FROM {info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{start_date}'
    """
    if end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date}'"
    query += " ORDER BY DATE"
    
    df = session.sql(query).to_pandas()
    df.rename(columns={col: feature_name}, inplace=True)
    df.sort_values("DATE", inplace=True)
    df.dropna(subset=[feature_name], how="any", inplace=True)
    return df.reset_index(drop=True)

# 1) BTC Price
btc_feat_name = "BTC PRICE:BTC_PRICE_USD"
df_btc = load_data_from_snowflake(btc_feat_name, start_date, end_date)

# Derivative?
if derive_btc:
    df_btc[btc_feat_name] = df_btc[btc_feat_name].diff()
    df_btc.dropna(subset=[btc_feat_name], how="any", inplace=True)

# Shift=0 => do nothing for BTC

# 2) Indicator
df_ind = load_data_from_snowflake(indicator_choice, start_date, end_date)

# Derivative
if derive_indicator:
    df_ind[indicator_choice] = df_ind[indicator_choice].diff()
    df_ind.dropna(subset=[indicator_choice], how="any", inplace=True)

# Shift for indicator
if shift_indicator > 0:
    df_ind[indicator_choice] = df_ind[indicator_choice].shift(shift_indicator)
    df_ind.dropna(subset=[indicator_choice], how="any", inplace=True)

# Merge them
df_merged = pd.merge(df_btc, df_ind, on="DATE", how="inner")
df_merged.sort_values("DATE", inplace=True)
df_merged.dropna(how="any", inplace=True)

######################################
# 8) Correlation (2x2)
######################################
st.subheader("Correlation Matrix")

if len(df_merged) < 2:
    st.warning("Not enough data points after transformations.")
else:
    subset_for_corr = df_merged.drop(columns=["DATE"]).copy()
    if len(subset_for_corr.columns) >= 2:
        if corr_method == "pearson":
            cmat = subset_for_corr.corr(method="pearson")
        else:
            cmat = subset_for_corr.corr(method="spearman")

        # We'll do a quick seaborn heatmap
        fig_corr, ax_corr = plt.subplots(figsize=(4,4))  # 2x2 or so
        fig_corr.patch.set_facecolor("black")
        ax_corr.set_facecolor("black")

        sns.heatmap(
            cmat,
            annot=True,
            cmap="RdBu_r",
            vmin=-1,
            vmax=1,
            square=True,
            ax=ax_corr,
            fmt=".2f",
            cbar_kws={'shrink': 0.8, 'label': 'Correlation'}
        )
        ax_corr.set_title("Correlation of BTC vs. Indicator", color="white")
        plt.xticks(color="white", rotation=45, ha="right")
        plt.yticks(color="white", rotation=0)
        st.pyplot(fig_corr)

        st.write(cmat)
    else:
        st.warning("Need at least 2 columns for correlation.")

######################################
# 9) Plotly Chart with 2 y-axes
######################################
st.subheader("Price & Indicator – Plotly Chart")

if df_merged.empty:
    st.warning("No data to plot.")
else:
    # We'll put BTC Price on the left y-axis, the indicator on the right y-axis
    btc_vals = df_merged[btc_feat_name]
    ind_vals = df_merged[indicator_choice]
    dates = df_merged["DATE"]

    fig = go.Figure()

    # 1) BTC Price on yaxis="y"
    fig.add_trace(go.Scatter(
        x=dates,
        y=btc_vals,
        mode='lines',
        name=btc_feat_name,
        line=dict(color=COLOR_PALETTE[0]),
        yaxis="y1"
    ))

    # 2) Indicator on yaxis="y2"
    fig.add_trace(go.Scatter(
        x=dates,
        y=ind_vals,
        mode='lines',
        name=indicator_choice,
        line=dict(color=COLOR_PALETTE[1]),
        yaxis="y2"
    ))

    fig.update_layout(
        xaxis=dict(
            domain=[0.1, 0.9],  # a bit of spacing
        ),
        yaxis=dict(
            title=btc_feat_name,
            titlefont=dict(color=COLOR_PALETTE[0]),
            tickfont=dict(color=COLOR_PALETTE[0]),
            anchor="x",
            side="left"
        ),
        yaxis2=dict(
            title=indicator_choice,
            titlefont=dict(color=COLOR_PALETTE[1]),
            tickfont=dict(color=COLOR_PALETTE[1]),
            anchor="x",
            overlaying="y",
            side="right"
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor="black",
        plot_bgcolor="black",
        legend=dict(
            x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)"
        ),
        hovermode="x unified",
        title="BTC Price (Left Axis) vs. Indicator (Right Axis)"
    )

    # X-axis in white
    fig.update_xaxes(
        showgrid=True, gridcolor="grey", 
        zeroline=False, linecolor="white", 
        tickfont=dict(color="white"), 
        titlefont=dict(color="white")
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="grey"
    )

    st.plotly_chart(fig, use_container_width=True)
