import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
