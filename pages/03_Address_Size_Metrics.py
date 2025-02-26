# 03_Address_Size_Metrics.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import random

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="Address Balance Bands",
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
# 3) Color Palette & Session State
######################################
COLOR_PALETTE = [
    "#E74C3C", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6",
    "#1ABC9C", "#E67E22", "#FF00FF", "#FF1493", "#FFD700"
]
if "color_palette" not in st.session_state:
    st.session_state["color_palette"] = COLOR_PALETTE.copy()
    random.shuffle(st.session_state["color_palette"])

######################################
# 4) Title
######################################
st.title("Address Balance Bands Over Time")

######################################
# 5) Sidebar Controls
######################################
with st.sidebar:
    st.header("Balance Bands Controls")

    default_start_date = datetime.date(2015, 1, 1)
    selected_start_date = st.date_input(
        "Start Date for Bands",
        value=default_start_date,
        help="Filter data from this date onward."
    )
    
    # Query distinct balance bands
    band_query = """
        SELECT DISTINCT BALANCE_BAND
        FROM BTC_DATA.DATA.ADDRESS_BALANCE_BANDS_DAILY
        ORDER BY BALANCE_BAND
    """
    band_list_df = session.sql(band_query).to_pandas()
    all_bands = band_list_df["BALANCE_BAND"].tolist()
    
    selected_bands = st.multiselect(
        "Select one or more balance bands:",
        options=all_bands,
        default=[all_bands[0]] if all_bands else []
    )

    scale_option_bands = st.radio("Y-axis Scale for Bands", ["Linear", "Log"], index=0)
    
    show_bands_ema = st.checkbox("Add EMA for Bands?", value=False)
    if show_bands_ema:
        bands_ema_period = st.number_input(
            "Bands EMA Period (days)",
            min_value=2, max_value=200,
            value=20
        )

######################################
# 6) Main Chart
######################################
if not selected_bands:
    st.warning("Please select at least one balance band.")
    st.stop()

bands_str = ", ".join([f"'{b}'" for b in selected_bands])
daily_counts_query = f"""
    SELECT
        DAY,
        BALANCE_BAND,
        ADDRESS_COUNT
    FROM BTC_DATA.DATA.ADDRESS_BALANCE_BANDS_DAILY
    WHERE DAY >= '{selected_start_date}'
      AND BALANCE_BAND IN ({bands_str})
    ORDER BY DAY
"""
bands_df = session.sql(daily_counts_query).to_pandas()
if bands_df.empty:
    st.warning("No data returned for the selected balance bands and date range.")
    st.stop()

# Pivot so each band is a separate column
pivot_df = bands_df.pivot(
    index="DAY",
    columns="BALANCE_BAND",
    values="ADDRESS_COUNT"
).fillna(0).reset_index()

# If user wants EMA, compute for each band
if show_bands_ema:
    for band in selected_bands:
        ema_column_name = f"EMA_{band}"
        pivot_df[ema_column_name] = pivot_df[band].ewm(span=bands_ema_period).mean()

fig_bands = go.Figure()
for band in selected_bands:
    # Original band trace
    fig_bands.add_trace(
        go.Scatter(
            x=pivot_df["DAY"],
            y=pivot_df[band],
            mode="lines",
            name=band
        )
    )
    # If EMA is enabled, add a dashed line
    if show_bands_ema:
        ema_col = f"EMA_{band}"
        fig_bands.add_trace(
            go.Scatter(
                x=pivot_df["DAY"],
                y=pivot_df[ema_col],
                mode="lines",
                name=f"EMA({bands_ema_period}) - {band}",
                line=dict(dash="dash"),
                opacity=0.7
            )
        )

fig_bands.update_layout(
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    title="Daily Address Count by Balance Band",
    hovermode="x unified",
    font=dict(color="#f0f2f6"),
    legend=dict(x=0, y=1.05, bgcolor="rgba(0,0,0,0)", orientation="h")
)
fig_bands.update_xaxes(title_text="Date", gridcolor="#4f5b66")
fig_bands.update_yaxes(
    title_text="Address Count",
    type="log" if scale_option_bands == "Log" else "linear",
    gridcolor="#4f5b66"
)

st.plotly_chart(fig_bands, use_container_width=True)
