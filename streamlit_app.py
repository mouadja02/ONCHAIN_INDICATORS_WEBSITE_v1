# streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# 1) Page Config
st.set_page_config(
    page_title="Bitcoin On-chain Indicators Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2) Snowflake Connection
cx = st.connection("snowflake")
session = cx.session()

# 3) Dark Theme Styling (full black background)
st.markdown(
    """
    <style>
    body {
        background-color: #000000;
        color: #f0f2f6;
    }
    .css-18e3th9, .css-1dp5vir, .css-12oz5g7, .st-bq {
        background-color: #000000 !important;
    }
    .css-15zrgzn, .css-1hynb2t, .css-1xh633b, .css-17eq0hr {
        color: #f0f2f6;
    }
    .css-1xh633b a {
        color: #1FA2FF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 4) Table Configurations
TABLE_DICT = {
    "ACTIVE_ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "BTC_REALIZED_CAP_AND_PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
        "date_col": "DATE",  # VARCHAR(16777216), can cast to DATE
        "numeric_cols": [
            "REALIZED_CAP_USD",
            "TOTAL_UNSPENT_BTC",
            "REALIZED_PRICE_USD"
        ]
    },
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
    },
    "EXCHANGE_FLOWS": {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOWS",
        "date_col": "DATE",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["INFLOWS_BTC", "OUTFLOWS_BTC", "NETFLOW_BTC"]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",  # DATE
        "numeric_cols": [
            "REALIZED_CAP_USD",
            "TOTAL_UNSPENT_BTC",
            "MARKET_CAP_USD",
            "MVRV"
        ]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "date_col": "DATE",  # DATE
        "numeric_cols": [
            "MARKET_CAP_USD",
            "REALIZED_CAP_USD",
            "NUPL",
            "NUPL_PERCENT"
        ]
    },
    "TX_COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "BLOCK_TIMESTAMP",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["TX_COUNT"]
    },
    "TX_VOLUME": {
        "table_name": "BTC_DATA.DATA.TX_VOLUME",
        "date_col": "DATE",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["DAILY_TX_VOLUME_BTC"]
    },
    "UTXO_LIFECYCLE": {
        "table_name": "BTC_DATA.DATA.UTXO_LIFECYCLE",
        "date_col": "CREATED_TIMESTAMP",  # TIMESTAMP_NTZ(9)
        "numeric_cols": ["BTC_VALUE"]
    },
    # New Entry: Puell Multiple
    "PUELL_MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",  # Should be a DATE column
        "numeric_cols": ["PUELL_MULTIPLE"]
    }
}

BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
BTC_PRICE_DATE_COL = "DATE"
BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"

# 5) Page Title
st.title("Bitcoin On-chain Indicators Dashboard")

#########################
# 6) CONTROLS (TOP)
#########################
control_container = st.container()
with control_container:
    st.subheader("Chart Controls")

    # Table & Indicators
    selected_table = st.selectbox(
        "Select a Table (Metric Set)",
        list(TABLE_DICT.keys()),
        help="Pick which table (indicator set) to visualize."
    )

    table_info = TABLE_DICT[selected_table]
    all_numeric_cols = table_info["numeric_cols"]
    selected_columns = st.multiselect(
        "Select Indicator(s):",
        all_numeric_cols,
        default=all_numeric_cols,
        help="Pick one or more numeric columns to plot on the left axis."
    )

    # Axis Scales & Chart Types
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        scale_option_indicator = st.radio("Indicator Axis", ["Linear", "Log"], index=0)
    with col2:
        scale_option_price = st.radio("BTC Price Axis", ["Linear", "Log"], index=0)
    with col3:
        chart_type_indicators = st.radio("Indicators", ["Line", "Bars"], index=0)
    with col4:
        chart_type_price = st.radio("BTC Price", ["Line", "Bars"], index=0)

    # EMA Option
    show_ema = st.checkbox("Add EMA for Indicators", value=False)
    if show_ema:
        ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20)

    # Date & BTC Price toggle
    col5, col6 = st.columns(2)
    with col5:
        default_start_date = datetime.date(2015, 1, 1)
        selected_start_date = st.date_input(
            "Start Date",
            value=default_start_date,
            help="Filter data from this date onward."
        )
    with col6:
        show_btc_price = st.checkbox("Show BTC Price?", value=True)

    # Color Pickers
    st.markdown("---")
    st.markdown("**Colors**")
    if "colors" not in st.session_state:
        st.session_state["colors"] = {}

    # BTC Price color (if enabled)
    if show_btc_price:
        btc_price_color = st.color_picker(
            "BTC Price Color",
            value=st.session_state["colors"].get("BTC_PRICE", "#FFA500")
        )
        st.session_state["colors"]["BTC_PRICE"] = btc_price_color

    for col in selected_columns:
        default_col_color = st.session_state["colors"].get(col, "#0000FF")
        picked_color = st.color_picker(f"Color for {col}", value=default_col_color)
        st.session_state["colors"][col] = picked_color

    # Plot Button
    st.markdown("---")
    plot_button = st.button("Plot Data")

#########################
# 7) CHART (BOTTOM)
#########################
plot_container = st.container()
with plot_container:
    if plot_button:
        if not selected_columns:
            st.warning("Please select at least one indicator column.")
            st.stop()

        # Query BTC Price if requested
        btc_price_df = pd.DataFrame()
        if show_btc_price:
            btc_price_query = f"""
                SELECT
                    CAST({BTC_PRICE_DATE_COL} AS DATE) AS PRICE_DATE,
                    {BTC_PRICE_VALUE_COL}
                FROM {BTC_PRICE_TABLE}
                WHERE {BTC_PRICE_VALUE_COL} IS NOT NULL
                  AND CAST({BTC_PRICE_DATE_COL} AS DATE) >= '{selected_start_date}'
                ORDER BY PRICE_DATE
            """
            btc_price_df = session.sql(btc_price_query).to_pandas()
            btc_price_df.rename(columns={"PRICE_DATE": "DATE"}, inplace=True)

        # Query Selected Indicator(s)
        date_col = table_info["date_col"]
        columns_for_query = ", ".join(selected_columns)
        indicator_query = f"""
            SELECT
                CAST({date_col} AS DATE) AS IND_DATE,
                {columns_for_query}
            FROM {table_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
            ORDER BY IND_DATE
        """
        indicator_df = session.sql(indicator_query).to_pandas()
        indicator_df.rename(columns={"IND_DATE": "DATE"}, inplace=True)

        if indicator_df.empty and btc_price_df.empty:
            st.warning("No data returned. Check your date range or table.")
            st.stop()

        # Merge if BTC Price is shown
        if show_btc_price and not btc_price_df.empty:
            merged_df = pd.merge(
                btc_price_df,
                indicator_df,
                on="DATE",
                how="inner"
            )
        else:
            merged_df = indicator_df

        if merged_df.empty:
            st.warning("No overlapping data in the selected date range.")
            st.stop()

        # EMA Calculation
        if show_ema:
            for col in selected_columns:
                merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()

        # Build Plotly Figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Plot each indicator on left axis
        for col in selected_columns:
            if chart_type_indicators == "Line":
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[col],
                        mode="lines",
                        name=col,
                        line=dict(color=st.session_state["colors"][col]),
                    ),
                    secondary_y=False
                )
            else:  # Bars
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
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[f"EMA_{col}"],
                        mode="lines",
                        name=f"EMA({ema_period}) - {col}",
                        line=dict(color=st.session_state["colors"][col], dash="dash"),
                        opacity=0.8
                    ),
                    secondary_y=False
                )

        # BTC Price on right axis (if enabled)
        if show_btc_price and not btc_price_df.empty:
            if chart_type_price == "Line":
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[BTC_PRICE_VALUE_COL],
                        mode="lines",
                        name="BTC Price (USD)",
                        line=dict(color=st.session_state["colors"]["BTC_PRICE"]),
                    ),
                    secondary_y=True
                )
            else:  # Bars
                fig.add_trace(
                    go.Bar(
                        x=merged_df["DATE"],
                        y=merged_df[BTC_PRICE_VALUE_COL],
                        name="BTC Price (USD)",
                        marker_color=st.session_state["colors"]["BTC_PRICE"]
                    ),
                    secondary_y=True
                )

        # Update Layout
        fig.update_layout(
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            title=f"{selected_table} vs BTC Price" if show_btc_price else f"{selected_table}",
            hovermode="x unified",
            font=dict(color="#f0f2f6"),
            legend=dict(
                x=0,
                y=1.05,
                bgcolor="rgba(0,0,0,0)",
                orientation="h"
            )
        )
        fig.update_xaxes(title_text="Date", gridcolor="#4f5b66")
        fig.update_yaxes(
            title_text="Indicator Value",
            type="log" if scale_option_indicator == "Log" else "linear",
            secondary_y=False,
            gridcolor="#4f5b66"
        )
        fig.update_yaxes(
            title_text="BTC Price (USD)",
            type="log" if scale_option_price == "Log" else "linear",
            secondary_y=True,
            gridcolor="#4f5b66"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Select your table, indicator(s), chart types, date range, then click 'Plot Data'.")
