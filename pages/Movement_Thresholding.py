import streamlit as st
import pandas as pd
import numpy as np
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

# Set color for the on-chain indicator column and BTC price if not already set.
indicator_col = "PRICE_MOVEMENT_STATE"
if indicator_col not in st.session_state["colors"]:
    st.session_state["colors"][indicator_col] = st.session_state["color_palette"].pop()

if "BTC_PRICE" not in st.session_state["colors"]:
    st.session_state["colors"]["BTC_PRICE"] = st.session_state["color_palette"].pop()

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

    st.markdown("---")
    st.header("Threshold Analysis Options")
    # Date range for threshold analysis
    thresh_start_date = st.date_input("Threshold Analysis Start Date", value=selected_start_date, key="thresh_start")
    thresh_end_date = st.date_input("Threshold Analysis End Date", value=datetime.date.today(), key="thresh_end")
    show_threshold = st.checkbox("Show Threshold Analysis", value=False)
    threshold_multiplier = st.slider("Threshold Multiplier", min_value=0.5, max_value=3.0, value=1.0, step=0.1)

# Determine whether BTC price should use the secondary Y-axis.
price_secondary = False if same_axis_checkbox else True

######################################
# Main Dashboard Plot
######################################
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

    # Build Plotly Figure for on-chain indicators and BTC price
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Plot on-chain indicators.
    # We assume that all columns except "DATE" and BTC_PRICE_VALUE_COL are on-chain indicators.
    indicator_cols = [col for col in merged_df.columns if col not in ["DATE", BTC_PRICE_VALUE_COL]]
    for col in indicator_cols:
        if chart_type_indicators == "Line":
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df[col],
                    mode="lines",
                    name=col,
                    line=dict(color=st.session_state["colors"].get(col, "#FFFFFF"))
                ),
                secondary_y=False
            )
        else:
            fig.add_trace(
                go.Bar(
                    x=merged_df["DATE"],
                    y=merged_df[col],
                    name=col,
                    marker_color=st.session_state["colors"].get(col, "#FFFFFF")
                ),
                secondary_y=False
            )
    
    # Plot BTC Price if requested and available.
    if show_btc_price and BTC_PRICE_VALUE_COL in merged_df.columns:
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

    # Detect change points if selected, BTC price data exists, and change point detection is activated.
    if detect_cpd and show_btc_price and BTC_PRICE_VALUE_COL in merged_df.columns:
        btc_series = merged_df[BTC_PRICE_VALUE_COL].dropna()
        if not btc_series.empty:
            algo = rpt.Pelt(model="rbf").fit(btc_series.values)
            change_points = algo.predict(pen=pen_value)
            for cp in change_points:
                if cp < len(merged_df):
                    cp_date = merged_df["DATE"].iloc[cp]
                    fig.add_vline(x=cp_date, line_width=2, line_dash="dash", line_color="white")

    # Set x-axis range based on start and (if activated) end date.
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

######################################
# Threshold Analysis Section
######################################
if show_threshold:
    st.markdown("---")
    st.header("Threshold Analysis")

    # Generate synthetic time series data for threshold analysis using user-specified dates
    n_days = (thresh_end_date - thresh_start_date).days + 1
    date_range_th = pd.date_range(start=thresh_start_date, periods=n_days)
    prices_th = np.cumsum(np.random.randn(n_days)) + 100  # random walk starting at 100
    df_threshold = pd.DataFrame({"Date": date_range_th, "Price": prices_th})

    # Compute daily percentage change
    df_threshold["Pct_Change"] = df_threshold["Price"].pct_change()

    # Compute threshold as the standard deviation of percentage changes times the multiplier
    base_threshold = df_threshold["Pct_Change"].std()
    threshold_value = base_threshold * threshold_multiplier

    # Classification function for changes
    def classify_change(change, thresh):
        if pd.isna(change):
            return "No Change"
        if change >= thresh:
            return "Increase Significantly"
        elif change > 0:
            return "Increase Slightly"
        elif change <= -thresh:
            return "Decrease Significantly"
        elif change < 0:
            return "Decrease Slightly"
        else:
            return "No Change"

    # Apply classification to the percentage change column
    df_threshold["Change_Class"] = df_threshold["Pct_Change"].apply(lambda x: classify_change(x, threshold_value))

    # Define colors for each classification
    class_colors = {
        "Increase Significantly": "green",
        "Increase Slightly": "lightgreen",
        "Decrease Slightly": "orange",
        "Decrease Significantly": "red",
        "No Change": "gray"
    }

    # Create a Plotly figure for the Price series with classification markers
    fig_price_th = go.Figure()

    # Price line
    fig_price_th.add_trace(go.Scatter(
        x=df_threshold["Date"],
        y=df_threshold["Price"],
        mode="lines",
        name="Price",
        line=dict(color="white")
    ))

    # Overlay markers by classification
    for cl in df_threshold["Change_Class"].unique():
        sub_df = df_threshold[df_threshold["Change_Class"] == cl]
        fig_price_th.add_trace(go.Scatter(
            x=sub_df["Date"],
            y=sub_df["Price"],
            mode="markers",
            name=cl,
            marker=dict(color=class_colors.get(cl, "blue"), size=8)
        ))

    fig_price_th.update_layout(
        title="Price Series with Change Classification",
        xaxis_title="Date",
        yaxis_title="Price",
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font=dict(color="#f0f2f6")
    )

    # Create a second Plotly figure for percentage changes and threshold lines
    fig_pct_th = go.Figure()

    # Plot percentage change
    fig_pct_th.add_trace(go.Scatter(
        x=df_threshold["Date"],
        y=df_threshold["Pct_Change"],
        mode="lines",
        name="Pct Change",
        line=dict(color="white")
    ))

    # Add threshold lines for positive and negative changes
    fig_pct_th.add_trace(go.Scatter(
        x=df_threshold["Date"],
        y=[threshold_value] * len(df_threshold),
        mode="lines",
        name="Threshold (+)",
        line=dict(dash="dash", color="green")
    ))
    fig_pct_th.add_trace(go.Scatter(
        x=df_threshold["Date"],
        y=[-threshold_value] * len(df_threshold),
        mode="lines",
        name="Threshold (-)",
        line=dict(dash="dash", color="red")
    ))

    fig_pct_th.update_layout(
        title="Daily Percentage Change with Thresholds",
        xaxis_title="Date",
        yaxis_title="Percentage Change",
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font=dict(color="#f0f2f6")
    )

    # Display the threshold analysis charts
    st.plotly_chart(fig_price_th, use_container_width=True)
    st.plotly_chart(fig_pct_th, use_container_width=True)
    
    st.write(f"Calculated Threshold (std of pct change * multiplier): {threshold_value:.4f}")
