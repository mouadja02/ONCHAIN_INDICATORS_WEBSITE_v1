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
    page_title="Bitcoin On-chain Indicators Dashboard",
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


BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
BTC_PRICE_DATE_COL = "DATE"
BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"


######################################
# 6) SIDEBAR Controls
######################################
with st.sidebar:

    st.markdown("---")
    st.header("Chart Options")
    default_start_date = datetime.date(2015, 1, 1)
    selected_start_date = st.date_input("Start Date", value=default_start_date)
    
    # End Date Option - Disabled by default
    activate_end_date = st.checkbox("Activate End Date", value=False)
    if activate_end_date:
        default_end_date = datetime.date.today()
        selected_end_date = st.date_input("End Date", value=default_end_date)
    else:
        selected_end_date = None

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


plot_container = st.container()
with plot_container:
 
    query = f"""
        SELECT
            DATE AS DATE,
            PRICE_MOVEMENT_STATE
        FROM BTC_PRICE_MOVEMENT_PERCENTAGE
        WHERE DATE >= '{selected_start_date}'
    """
    if selected_end_date:
        query += f" AND DATE <= '{selected_end_date}'\n"
    query += "ORDER BY DATE"
    
    df = session.sql(query).to_pandas()

    # Query BTC Price if requested
    df_btc = pd.DataFrame()
    if show_btc_price:
        btc_query = f"""
            SELECT
                CAST({BTC_PRICE_DATE_COL} AS DATE) AS DATE,
                {BTC_PRICE_VALUE_COL}
            FROM {BTC_PRICE_TABLE}
            WHERE {BTC_PRICE_VALUE_COL} IS NOT NULL
              AND CAST({BTC_PRICE_DATE_COL} AS DATE) >= '{selected_start_date}'
        """
        if selected_end_date:
            btc_query += f" AND CAST({BTC_PRICE_DATE_COL} AS DATE) <= '{selected_end_date}'\n"
        btc_query += "ORDER BY DATE"
        df_btc = session.sql(btc_query).to_pandas()

    # Merge data using an outer join so all dates are captured
    if show_btc_price and not df_btc.empty:
        merged_df = pd.merge(df_btc, df, on="DATE", how="outer")
    else:
        merged_df = df

    merged_df.sort_values("DATE", inplace=True)
    if merged_df.empty:
        st.warning("No data returned. Check your date range or table selection.")
        st.stop()

    # Build Plotly Figure
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Plot on-chain indicators
    
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
    
    if detect_cpd:
        btc_series = merged_df[BTC_PRICE_VALUE_COL].dropna()
        if not btc_series.empty:
            algo = rpt.Pelt(model="rbf").fit(btc_series.values)
            change_points = algo.predict(pen=pen_value)
            for cp in change_points:
                if cp < len(merged_df):
                    cp_date = merged_df["DATE"].iloc[cp]
                    fig.add_vline(x=cp_date, line_width=2, line_dash="dash", line_color="white")

    # Set x-axis range based on start and (if activated) end date
    x_range = [selected_start_date.strftime("%Y-%m-%d")]
    if selected_end_date:
        x_range.append(selected_end_date.strftime("%Y-%m-%d"))
    else:
        x_range.append(merged_df["DATE"].max().strftime("%Y-%m-%d"))
    fig.update_xaxes(title_text="Date", gridcolor="#4f5b66", range=x_range)

    fig.update_layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        hovermode="x unified",
        font=dict(color="#f0f2f6"),
        legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
    )
    fig.update_yaxes(
        title_text="Movement Percentage",
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
            'drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'
        ]
    }
    st.plotly_chart(fig, use_container_width=True, config=config)
