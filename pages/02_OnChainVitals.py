import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import random
import ruptures as rpt
import numpy as np
import io
import plotly.io as pio

######################################
# 1) Page Configuration & Theme Setup
######################################
st.set_page_config(
    page_title="Bitcoin On-chain Indicators Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar: Select Theme
theme_choice = st.sidebar.radio("Select Theme:", ["Dark", "Bright"], index=0)

# Set colors based on theme choice
if theme_choice == "Dark":
    bg_color = "#000000"
    text_color = "#f0f2f6"
    grid_color = "#4f5b66"
else:
    bg_color = "#FFFFFF"
    text_color = "#000000"
    grid_color = "#CCCCCC"

# Apply CSS styling dynamically so that all texts are visible
css_style = f"""
    <style>
    body {{ background-color: {bg_color}; color: {text_color}; }}
    .css-18e3th9, .css-1dp5vir, .css-12oz5g7, .st-bq {{
        background-color: {bg_color} !important;
    }}
    .css-15zrgzn, .css-1dp5vir, .css-1xh633b, .css-17eq0hr {{
        color: {text_color};
    }}
    .css-1xh633b a {{ color: #1FA2FF; }}
    </style>
"""
st.markdown(css_style, unsafe_allow_html=True)

######################################
# 2) Snowflake Connection
######################################
cx = st.connection(
    "",
    type="snowflake",
    account="vulyokn-irb92128",
    user="InternProject",
    password="ThisISInternAccount2002",
    role="SYSADMIN",
    warehouse="BG_WH",
    database="BTC_DATA",
    schema="DATA",
    authenticator="snowflake",
)
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
    "ACTIVE ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
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
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",
        "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
    },
    "EXCHANGE_FLOW": {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
        "date_col": "DAY",
        "numeric_cols": [
            "INFLOW_BTC", "OUTFLOW_BTC", "NETFLOW_BTC", "EXCHANGE_RESERVE_BTC",
            "INFLOW_USD", "OUTFLOW_USD", "NETFLOW_USD", "EXCHANGE_RESERVE_USD"
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
        "numeric_cols": ["NUPL", "NUPL_PERCENT"]
    },
    "REALIZED_CAP_VS_MARKET_CAP": {
        "table_name": "BTC_DATA.DATA.REALIZED_CAP_VS_MARKET_CAP",
        "date_col": "DATE",
        "numeric_cols": ["MARKET_CAP_USD", "REALIZED_CAP_USD"]
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
    "STOCK TO FLOW": {
        "table_name": "BTC_DATA.DATA.STOCK_TO_FLOW",
        "date_col": "DATE",
        "numeric_cols": [
            "STOCK", "FLOW", "AVG_RATIO_365", "AVG_RATIO_463", "MODEL_PRICE_365",
            "MODEL_PRICE_463", "MODEL_VARIANCE"
        ]
    },
    "TX COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "DATE",
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
    "M2 GROWTH": {
        "table_name": "BTC_DATA.DATA.m2_growth",
        "date_col": "DATE",
        "numeric_cols": [
            "M2_Growth_YoY", "M2_Global_Supply"
        ]
    },
    "PUELL MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINTED_BTC", "DAILY_ISSUANCE_USD", "MA_365_ISSUANCE_USD",
            "PUELL_MULTIPLE"
        ]
    },
    "TRADE VOLUME": {
        "table_name": "BTC_DATA.DATA.TRADE_VOLUME",
        "date_col": "DATE",
        "numeric_cols": [ "TRADE_VOLUME","DOMINANCE"]
    },   
    "GOOGLE TREND": {
        "table_name": "BTC_DATA.DATA.google_trend",
        "date_col": "DATE",
        "numeric_cols": [ "INDEX"]
    },
    "FEAR & GREED INDEX": {
        "table_name": "BTC_DATA.DATA.FEAR_GREED_INDEX",
        "date_col": "DATE",
        "numeric_cols": ["FNG_VALUE"]
    },
    "TWITTER SENTIMENT": {
        "table_name": "BTC_DATA.DATA.TWITTER_SENTIMENT",
        "date_col": "DATE",
        "numeric_cols": [
            "TWITTER_FOMO",
            "TWITTER_BULLISH",
            "TWITTER_BEARISH",
            "TWITTER_FEARFUL_CONCERNED",
            "TWITTER_PRICE"
        ]
    },    
    "REDDIT SENTIMENT": {
        "table_name": "BTC_DATA.DATA.REDDIT_SENTIMENT",
        "date_col": "DATE",
        "numeric_cols": [
            "REDDIT_FOMO",
            "REDDIT_BULLISH",
            "REDDIT_BEARISH",
            "REDDIT_FEARFUL_CONCERNED",
            "REDDIT_PRICE"
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
    selected_table = st.selectbox(
        "Select a Table (Metric Set)",
        list(TABLE_DICT.keys()),
        help="Pick which table (indicator set) to visualize."
    )
    table_info = TABLE_DICT[selected_table]

    # ---------------------------
    # Default start date:
    # For Fear & Greed => 2018-02-01
    # Otherwise => 2015-01-01
    # ---------------------------
    if selected_table == "FEAR & GREED INDEX":
        default_start_date = datetime.date(2010, 1, 1)
    else:
        default_start_date = datetime.date(2015, 1, 1)

    # Let user pick the start date (default above)
    selected_start_date = st.date_input("Start Date", value=default_start_date)
    
    # End Date Option
    activate_end_date = st.checkbox("Activate End Date", value=False)
    if activate_end_date:
        default_end_date = datetime.date.today()
        selected_end_date = st.date_input("End Date", value=default_end_date)
    else:
        selected_end_date = None

    # For the selected table, let user pick from numeric_cols
    all_numeric_cols = table_info["numeric_cols"]
    selected_cols = st.multiselect(
        "Select Indicator(s):",
        all_numeric_cols,
        default=all_numeric_cols,
        help="Pick one or more numeric columns to plot."
    )

    st.markdown("---")
    st.header("Chart Options")
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

    # Enable CPD
    detect_cpd = st.checkbox("Detect BTC Price Change Points?", value=False)
    pen_value = None
    if detect_cpd:
        pen_value = st.number_input("CPD Penalty", min_value=1, max_value=200, value=10)

    # Normalization Options
    st.markdown("---")
    st.header("Normalization")
    st.write("Choose which columns to normalize (including BTC price if you want).")
    
    # Gather columns to possibly normalize
    columns_for_normalization = list(selected_cols)
    if show_btc_price:
        columns_for_normalization = [BTC_PRICE_VALUE_COL] + columns_for_normalization

    NORMALIZATION_METHODS = ["None", "Z-Score", "Min-Max", "Robust", "Log Transform"]

    col_to_norm_method = {}
    for col in columns_for_normalization:
        method = st.selectbox(
            f"Normalization method for {col}",
            NORMALIZATION_METHODS,
            index=0  # default "None"
        )
        col_to_norm_method[col] = method

######################################
# 7) Assign Colors for Each Selected Indicator
######################################
if not selected_cols:
    st.warning("Please select at least one indicator column.")
    st.stop()

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

######################################
# 8) MAIN INDICATORS CHART
######################################
plot_container = st.container()
with plot_container:
    # --- 8.1) Special Case: FEAR & GREED INDEX ---
    if selected_table == "FEAR & GREED INDEX":
        # 1) Query Fear & Greed data
        date_col = table_info["date_col"]
        cols_for_query = ", ".join(selected_cols)

        # Build query for Fear & Greed
        query_fng = f"""
            SELECT
                CAST({date_col} AS DATE) AS DATE,
                {cols_for_query},
                FNG_CLASS
            FROM {table_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
        """
        if selected_end_date:
            query_fng += f" AND CAST({date_col} AS DATE) <= '{selected_end_date}'\n"
        query_fng += "ORDER BY DATE"

        df_fng = session.sql(query_fng).to_pandas()
        df_fng.rename(columns={"DATE": "DATE"}, inplace=True)

        # 2) Query BTC Price
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

        # 3) Merge on DATE (outer join to capture all dates)
        merged_df = pd.merge(df_btc, df_fng, on="DATE", how="outer")
        merged_df.sort_values("DATE", inplace=True)
        if merged_df.empty:
            st.warning("No data returned. Check your date range.")
            st.stop()

        # 4) Create figure: BTC Price line + scatter colored by FNG_VALUE
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Plot BTC Price as a line
        if show_btc_price and not df_btc.empty and BTC_PRICE_VALUE_COL in merged_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df[BTC_PRICE_VALUE_COL],
                    mode="lines",
                    name="BTC Price (USD)",
                    line=dict(color="white")
                ),
                secondary_y=False
            )

        # Plot Fear & Greed as a heatmap of points
        if "FNG_VALUE" in merged_df.columns:
            # We'll store FNG_CLASS in customdata, and use a custom hovertemplate.
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    # If BTC price is shown, align points vertically with BTC price
                    # otherwise, place them at 0 on the y-axis.
                    y=merged_df[BTC_PRICE_VALUE_COL] if show_btc_price else [0]*len(merged_df),
                    mode="markers",
                    name="Fear & Greed (Heatmap)",
                    marker=dict(
                        color=merged_df["FNG_VALUE"],   # numeric FNG value
                        colorscale="RdYlGn",            # red -> yellow -> green
                        cmin=0,
                        cmax=100,                       # typical range of FNG
                        showscale=True,
                        colorbar=dict(title="FNG"),
                        size=5
                    ),
                    customdata=merged_df["FNG_CLASS"],
                    hovertemplate=(
                        "Date: %{x|%Y-%m-%d}<br>"
                        "FNG Value: %{marker.color}<br>"
                        "FNG Class: %{customdata}"
                        "<extra></extra>"
                    )
                ),
                secondary_y=False
            )

        # Layout updates
        fig.update_layout(
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            hovermode="x unified",
            font=dict(color="#f0f2f6"),
            title="Fear & Greed Index vs BTC Price" if show_btc_price else "Fear & Greed Index",
            legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
        )
        fig.update_xaxes(title_text="Date", gridcolor="#4f5b66")
        fig.update_yaxes(
            title_text="BTC Price (USD)" if show_btc_price else "FNG (no BTC Price)",
            type="log" if scale_option_price == "Log" else "linear",
            gridcolor="#4f5b66"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.stop()

    # -------------------------
    # ELSE: REGULAR INDICATORS
    # -------------------------
    date_col = table_info["date_col"]
    cols_for_query = ", ".join(selected_cols)
    
    # Build query with date range
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {cols_for_query}
        FROM {table_info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
    """
    if selected_end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{selected_end_date}'\n"
    query += "ORDER BY DATE"
    
    df_indicators = session.sql(query).to_pandas()
    df_indicators.rename(columns={"DATE": "DATE"}, inplace=True)

    # 8.2) Query BTC Price if requested
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

    # 8.3) Merge data
    if show_btc_price and not df_btc.empty:
        merged_df = pd.merge(df_btc, df_indicators, on="DATE", how="outer")
    else:
        merged_df = df_indicators

    merged_df.sort_values("DATE", inplace=True)
    if merged_df.empty:
        st.warning("No data returned. Check your date range or table selection.")
        st.stop()

    # 8.4) CPD on BTC Price if enabled
    change_points = []
    if detect_cpd and show_btc_price and BTC_PRICE_VALUE_COL in merged_df.columns:
        btc_series = merged_df[BTC_PRICE_VALUE_COL].dropna().values
        if len(btc_series) > 2:
            algo = rpt.Pelt(model="rbf").fit(btc_series)
            change_points = algo.predict(pen=pen_value)
        else:
            st.warning("Not enough BTC Price data for change point detection.")

    # --- Helper functions for normalization ---
    def z_score(series: pd.Series):
        mu = series.mean()
        sigma = series.std()
        return (series - mu) / sigma if sigma != 0 else series

    def min_max(series: pd.Series):
        min_val = series.min()
        max_val = series.max()
        return (series - min_val) / (max_val - min_val) if max_val != min_val else series

    def robust_scale(series: pd.Series):
        median_val = series.median()
        iqr = series.quantile(0.75) - series.quantile(0.25)
        return (series - median_val) / iqr if iqr != 0 else series

    def log_transform(series: pd.Series):
        # Add small constant to avoid log(0)
        return np.log(series + 1e-9).replace(-np.inf, np.nan)

    def apply_normalization(series: pd.Series, method: str) -> pd.Series:
        s = series.copy()
        if method == "Z-Score":
            s = z_score(s)
        elif method == "Min-Max":
            s = min_max(s)
        elif method == "Robust":
            s = robust_scale(s)
        elif method == "Log Transform":
            s = log_transform(s)
        return s

    # --- 8.5) Apply Normalization ---
    def normalize_per_segment(df: pd.DataFrame, segments: list, columns_to_normalize: dict):
        prev_cp = 0
        for cp in segments:
            seg_indices = df.index[prev_cp:cp]
            for col, method in columns_to_normalize.items():
                if col in df.columns and method != "None":
                    seg_data = df.loc[seg_indices, col]
                    df.loc[seg_indices, col] = apply_normalization(seg_data, method)
            prev_cp = cp

    columns_with_methods = {
        c: col_to_norm_method[c] for c in col_to_norm_method if col_to_norm_method[c] != "None"
    }

    if detect_cpd and change_points:
        normalize_per_segment(merged_df, change_points, columns_with_methods)
    else:
        for col, method in columns_with_methods.items():
            if col in merged_df.columns and method != "None":
                merged_df[col] = apply_normalization(merged_df[col], method)

    # 8.6) Calculate EMA if requested
    if show_ema:
        for col in selected_cols:
            if col in merged_df.columns:
                merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()
        if show_btc_price and not df_btc.empty and BTC_PRICE_VALUE_COL in merged_df.columns:
            merged_df["EMA_BTC_PRICE"] = merged_df[BTC_PRICE_VALUE_COL].ewm(span=ema_period).mean()

    # 8.7) Build Plotly Figure
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # --- Plot On-chain Indicators ---
    for col in selected_cols:
        if show_ema and f"EMA_{col}" in merged_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df[f"EMA_{col}"],
                    mode="lines",
                    name=f"EMA({ema_period}) - {col}",
                    line=dict(color=st.session_state["colors"][col])
                ),
                secondary_y=False
            )
        else:
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

    # --- Plot BTC Price ---
    if show_btc_price and not df_btc.empty and BTC_PRICE_VALUE_COL in merged_df.columns:
        price_secondary = not same_axis_checkbox
        if show_ema and "EMA_BTC_PRICE" in merged_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df["EMA_BTC_PRICE"],
                    mode="lines",
                    name=f"EMA({ema_period}) - BTC Price",
                    line=dict(color=st.session_state["colors"]["BTC_PRICE"])
                ),
                secondary_y=price_secondary
            )
        else:
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
        
        # --- Visualize CPD lines on the chart
        if detect_cpd and change_points:
            for cp in change_points:
                if cp < len(merged_df):
                    cp_date = merged_df["DATE"].iloc[cp]
                    fig.add_vline(x=cp_date, line_width=2, line_dash="dash", line_color="white")

    # 8.8) Set X-axis range
    x_range = [selected_start_date.strftime("%Y-%m-%d")]
    if selected_end_date:
        x_range.append(selected_end_date.strftime("%Y-%m-%d"))
    else:
        x_range.append(merged_df["DATE"].max().strftime("%Y-%m-%d"))

    fig.update_xaxes(title_text="Date", gridcolor="#4f5b66", range=x_range)

    # 8.9) Layout Settings
    fig.update_layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        title=f"{selected_table} vs BTC Price" if show_btc_price else f"{selected_table}", 
        hovermode="x unified",
        font=dict(color="#f0f2f6"),
        legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
    )
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
            'drawline', 'drawopenpath', 'drawclosedpath',
            'drawcircle', 'drawrect', 'eraseshape'
        ]
    }
    st.plotly_chart(fig, use_container_width=True, config=config)

######################################
# 9) Save Figure Button
######################################
if st.button("Save Figure"):
    buffer = io.BytesIO()
    fig.write_image(buffer, format="png", scale=2)
    buffer.seek(0)

    # Provide download link
    st.download_button(
        label="Download Plot as PNG",
        data=buffer,
        file_name=f"btc_dashboard_{theme_choice.lower()}.png",
        mime="image/png"
    )
