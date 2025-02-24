import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# Set page config at the TOP of the file
st.set_page_config(
    page_title="Bitcoin On-chain Indicators Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1) Dark Theme Styling (full black background)
# Inject Bootstrap + custom style
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">

<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
body {
  background-color: #000000;
  color: #f0f2f6;
}
.navbar-custom {
  background-color: #111111 !important;
}
.container {
  margin-top: 80px;
}
</style>

<!-- Optional: Reuse the same navbar if you wish -->
<nav class="navbar navbar-expand-lg navbar-dark navbar-custom fixed-top">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">OnChain Explorer</a>
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item">
          <a class="nav-link" href="/?page=OnChainVitals">OnChainVitals</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/?page=BlockchainScope">BlockchainScope</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
""", unsafe_allow_html=True)


# 2) Snowflake Connection
cx = st.connection("snowflake")
session = cx.session()

# 3) Table Configurations
TABLE_DICT = {
    "ACTIVE_ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "BTC_REALIZED_CAP_AND_PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
        "date_col": "DATE",
        "numeric_cols": [
            "REALIZED_CAP_USD",
            "REALIZED_PRICE_USD"
        ]
    },
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",
        "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",
        "numeric_cols": [
            "MVRV"
        ]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "date_col": "DATE",
        "numeric_cols": [
            "NUPL",
            "NUPL_PERCENT"
        ]
    },
    "REALIZED_CAP_VS_MARKET_CAP": {
        "table_name": "BTC_DATA.DATA.REALIZED_CAP_VS_MARKET_CAP",
        "date_col": "DATE",
        "numeric_cols": [
            "MARKET_CAP_USD",
            "REALIZED_CAP_USD"
        ]
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

# 4) Page Title
st.title("Bitcoin On-chain Indicators Dashboard")

#########################
# 5) CONTROLS (TOP)
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

    # NEW CHECKBOX: Plot BTC Price on same axis or secondary axis
    same_axis_checkbox = st.checkbox("Plot BTC Price on the same Y-axis as Indicators?", value=False)

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

#########################
# 6) CHART (BOTTOM) — Plot Immediately
#########################
plot_container = st.container()
with plot_container:
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
    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    import plotly.graph_objects as go
    
    # Plot each indicator on the left axis
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

    # BTC Price
    if show_btc_price and not btc_price_df.empty:
        price_secondary_y = (not same_axis_checkbox)

        if chart_type_price == "Line":
            fig.add_trace(
                go.Scatter(
                    x=merged_df["DATE"],
                    y=merged_df[BTC_PRICE_VALUE_COL],
                    mode="lines",
                    name="BTC Price (USD)",
                    line=dict(color=st.session_state["colors"]["BTC_PRICE"]),
                ),
                secondary_y=price_secondary_y
            )
        else:  # Bars
            fig.add_trace(
                go.Bar(
                    x=merged_df["DATE"],
                    y=merged_df[BTC_PRICE_VALUE_COL],
                    name="BTC Price (USD)",
                    marker_color=st.session_state["colors"]["BTC_PRICE"]
                ),
                secondary_y=price_secondary_y
            )

    # Dynamic title
    fig_title = f"{selected_table} vs BTC Price" if show_btc_price else f"{selected_table}"

    fig.update_layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        title=fig_title,
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

    # Left Y-axis
    fig.update_yaxes(
        title_text="Indicator Value",
        type="log" if scale_option_indicator == "Log" else "linear",
        secondary_y=False,
        gridcolor="#4f5b66"
    )
    # Right Y-axis (only used if same_axis_checkbox is False)
    fig.update_yaxes(
        title_text="BTC Price (USD)" if not same_axis_checkbox else "",
        type="log" if scale_option_price == "Log" else "linear",
        secondary_y=True,
        gridcolor="#4f5b66"
    )

    st.plotly_chart(fig, use_container_width=True)
