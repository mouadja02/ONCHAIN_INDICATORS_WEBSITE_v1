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
    page_title="Bitcoin On-chain Indicators Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    body { background-color: #000000; color: #f0f2f6; }
    .css-18e3th9, .css-1dp5vir, .css-12oz5g7, .st-bq { background-color: #000000 !important; }
    .css-15zrgzn, .css-1hynb2t, .css-1xh633b, .css-17eq0hr { color: #f0f2f6; }
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
# 3) Define Color Palette & Session Color Tracking
######################################
COLOR_PALETTE = [
    "#E74C3C",  # Red
    "#F1C40F",  # Yellow
    "#2ECC71",  # Green
    "#3498DB",  # Blue
    "#9B59B6",  # Purple
    "#1ABC9C",  # Teal
    "#E67E22",  # Orange
    "#FF00FF",  # Magenta
    "#FF1493",  # DeepPink
    "#FFD700",  # Gold
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
    "EXCHANGE_FLOW" : {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
        "date_col": "DAY",
        "numeric_cols": [
            "INFLOW","OUTFLOW","NETFLOW"
        ]
    },
    "HOLDER_REALIZED_PRICES" : {
        "table_name": "BTC_DATA.DATA.HOLDER_REALIZED_PRICES",
        "date_col": "DATE",
        "numeric_cols": [
            "SHORT_TERM_HOLDER_REALIZED_PRICE","LONG_TERM_HOLDER_REALIZED_PRICE"
        ]
    },
    "MVRV": {
        "table_name": "BTC_DATA.DATA.MVRV",
        "date_col": "DATE",
        "numeric_cols": [
            "MVRV"
        ]
    },    
    "MVRV_WITH_HOLDER_TYPES": {
        "table_name": "BTC_DATA.DATA.MVRV_WITH_HOLDER_TYPES",
        "date_col": "DATE",
        "numeric_cols": [
            "OVERALL_MVRV","STH_MVRV","LTH_MVRV"
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

# BTC Price configuration (handled separately)
BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
BTC_PRICE_DATE_COL = "DATE"
BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"

######################################
# 5) Page Title
######################################
st.title("Bitcoin On-chain Indicators Dashboard")

######################################
# 6) Select Plotting Mode
######################################
plotting_mode = st.radio(
    "Select Plotting Mode", 
    ["Single Table Plot", "Multi-Indicators Plot"],
    index=0,
    help="Choose 'Single Table Plot' for one table per plot (default) or 'Multi-Indicators Plot' to combine indicators from multiple tables into one chart."
)

######################################
# 7) Plotting Controls & Chart Building
######################################
if plotting_mode == "Single Table Plot":
    # ----- NORMAL / SINGLE TABLE PLOTTING -----
    control_container = st.container()
    with control_container:
        st.subheader("Chart Controls – Single Table Plot")
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
    
        # Option: Plot BTC Price on same axis or secondary axis
        same_axis_checkbox = st.checkbox("Plot BTC Price on the same Y-axis as Indicators?", value=False)
    
        st.markdown("---")
        st.markdown("**Customize Colors**")
    
    # ----- ASSIGN COLORS -----
    if not selected_columns:
        st.warning("Please select at least one indicator column.")
        st.stop()
    
    for i, col in enumerate(selected_columns):
        if col not in st.session_state["assigned_colors"]:
            assigned_color = st.session_state["color_palette"][i % len(st.session_state["color_palette"])]
            st.session_state["assigned_colors"][col] = assigned_color
        default_color = st.session_state["assigned_colors"][col]
        picked_color = st.color_picker(f"Color for {col}", value=default_color)
        st.session_state["assigned_colors"][col] = picked_color
        st.session_state["colors"][col] = picked_color
    
    # Handle BTC Price color if shown
    if show_btc_price:
        if "BTC_PRICE" not in st.session_state["assigned_colors"]:
            price_color_index = len(selected_columns) % len(st.session_state["color_palette"])
            st.session_state["assigned_colors"]["BTC_PRICE"] = st.session_state["color_palette"][price_color_index]
        default_btc_color = st.session_state["assigned_colors"]["BTC_PRICE"]
        picked_btc_color = st.color_picker("Color for BTC Price", value=default_btc_color)
        st.session_state["assigned_colors"]["BTC_PRICE"] = picked_btc_color
        st.session_state["colors"]["BTC_PRICE"] = picked_btc_color
    
    # ----- QUERY & PLOT -----
    plot_container = st.container()
    with plot_container:
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
            merged_df = pd.merge(btc_price_df, indicator_df, on="DATE", how="inner")
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
        # Plot each indicator on primary y-axis
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
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[f"EMA_{col}"],
                        mode="lines",
                        name=f"EMA({ema_period}) - {col}",
                        line=dict(color=st.session_state["colors"][col]),
                    ),
                    secondary_y=False
                )
    
        # Plot BTC Price if selected
        if show_btc_price and not btc_price_df.empty:
            price_secondary_y = not same_axis_checkbox
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
            else:
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
            legend=dict(x=0, y=1.05, bgcolor="rgba(0,0,0,0)", orientation="h")
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
                'drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'
            ]
        }
        st.plotly_chart(fig, use_container_width=True, config=config)

else:
    # ----- MULTI-INDICATORS PLOTTING: Combine Tables into One Chart -----
    control_container = st.container()
    with control_container:
        st.subheader("Chart Controls – Multi-Indicators Plot")
        # Let user select one or more tables to combine (order preserved)
        selected_tables = st.multiselect(
            "Select one or more tables to combine:",
            list(TABLE_DICT.keys()),
            default=list(TABLE_DICT.keys())[:2],
            help="Pick multiple tables. Their indicators will be merged on the DATE field."
        )
    
        # For each selected table, allow the user to pick which indicators to include.
        table_indicators = {}
        for tbl in selected_tables:
            default_cols = TABLE_DICT[tbl]["numeric_cols"]
            table_indicators[tbl] = st.multiselect(
                f"Select indicator(s) from {tbl}:",
                TABLE_DICT[tbl]["numeric_cols"],
                default=default_cols,
                key=f"{tbl}_indicators"
            )
    
        # Option to include BTC Price as an additional indicator.
        include_btc = st.checkbox("Include BTC Price as an Indicator", value=True)
    
        # Common chart options
        col1, col2, col3 = st.columns(3)
        with col1:
            scale_option = st.radio("Y-Axis Scale", ["Linear", "Log"], index=0)
        with col2:
            chart_type = st.radio("Chart Type", ["Line", "Bars"], index=0)
        with col3:
            same_axis_checkbox = st.checkbox("Plot BTC Price on same Y-axis?", value=False)
    
        # EMA options
        show_ema = st.checkbox("Add EMA to indicators", value=False)
        if show_ema:
            ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20)
    
        # Date range selector (all queries filter from this date onward)
        default_start_date = datetime.date(2015, 1, 1)
        selected_start_date = st.date_input("Start Date", value=default_start_date, help="Filter data from this date onward.")
    
        st.markdown("---")
        st.markdown("**Customize Colors**")
    
    # ----- ASSIGN COLORS FOR COMBINED INDICATORS -----
    # Build a unique list of indicator names (prefix with table name)
    combined_indicators = []
    for tbl, cols in table_indicators.items():
        for col in cols:
            combined_indicators.append(f"{tbl}:{col}")
    if include_btc:
        combined_indicators.append("BTC_PRICE")
    
    for i, ind in enumerate(combined_indicators):
        if ind not in st.session_state["assigned_colors"]:
            assigned_color = st.session_state["color_palette"][i % len(st.session_state["color_palette"])]
            st.session_state["assigned_colors"][ind] = assigned_color
        default_color = st.session_state["assigned_colors"][ind]
        picked_color = st.color_picker(f"Color for {ind}", value=default_color)
        st.session_state["assigned_colors"][ind] = picked_color
        st.session_state["colors"][ind] = picked_color
    
    # ----- QUERY & MERGE DATAFRAMES -----
    plot_container = st.container()
    with plot_container:
        df_list = []
        for tbl in selected_tables:
            cols = table_indicators[tbl]
            if not cols:
                continue
            date_col = TABLE_DICT[tbl]["date_col"]
            cols_str = ", ".join(cols)
            query = f"""
                SELECT
                    CAST({date_col} AS DATE) AS DATE,
                    {cols_str}
                FROM {TABLE_DICT[tbl]['table_name']}
                WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
                ORDER BY DATE
            """
            df = session.sql(query).to_pandas()
            rename_dict = {col: f"{tbl}:{col}" for col in cols}
            df.rename(columns=rename_dict, inplace=True)
            df_list.append(df)
    
        if include_btc:
            btc_query = f"""
                SELECT
                    CAST({BTC_PRICE_DATE_COL} AS DATE) AS DATE,
                    {BTC_PRICE_VALUE_COL}
                FROM {BTC_PRICE_TABLE}
                WHERE {BTC_PRICE_VALUE_COL} IS NOT NULL
                  AND CAST({BTC_PRICE_DATE_COL} AS DATE) >= '{selected_start_date}'
                ORDER BY DATE
            """
            btc_df = session.sql(btc_query).to_pandas()
            btc_df.rename(columns={BTC_PRICE_VALUE_COL: "BTC_PRICE"}, inplace=True)
            df_list.append(btc_df)
    
        if not df_list:
            st.warning("No data returned. Check your selections and date range.")
            st.stop()
    
        merged_df = df_list[0]
        for df in df_list[1:]:
            merged_df = pd.merge(merged_df, df, on="DATE", how="outer")
        merged_df.sort_values("DATE", inplace=True)
    
        if show_ema:
            for col in merged_df.columns:
                if col == "DATE":
                    continue
                merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()
    
        # ----- BUILD COMBINED FIGURE -----
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        for col in merged_df.columns:
            if col == "DATE":
                continue
            if col == "BTC_PRICE":
                secondary_y = not same_axis_checkbox
                if chart_type == "Line":
                    fig.add_trace(
                        go.Scatter(
                            x=merged_df["DATE"],
                            y=merged_df[col],
                            mode="lines",
                            name=col,
                            line=dict(color=st.session_state["colors"][col])
                        ),
                        secondary_y=secondary_y
                    )
                else:
                    fig.add_trace(
                        go.Bar(
                            x=merged_df["DATE"],
                            y=merged_df[col],
                            name=col,
                            marker_color=st.session_state["colors"][col]
                        ),
                        secondary_y=secondary_y
                    )
                if show_ema:
                    fig.add_trace(
                        go.Scatter(
                            x=merged_df["DATE"],
                            y=merged_df[f"EMA_{col}"],
                            mode="lines",
                            name=f"EMA({ema_period}) - {col}",
                            line=dict(color=st.session_state["colors"][col])
                        ),
                        secondary_y=secondary_y
                    )
            else:
                if chart_type == "Line":
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
    
        fig_title = "Combined Indicators Chart"
        fig.update_layout(
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            title=fig_title,
            hovermode="x unified",
            font=dict(color="#f0f2f6"),
            legend=dict(x=0, y=1.05, bgcolor="rgba(0,0,0,0)", orientation="h")
        )
        fig.update_xaxes(title_text="Date", gridcolor="#4f5b66")
        fig.update_yaxes(
            title_text="Indicator Value",
            type="log" if scale_option == "Log" else "linear",
            secondary_y=False,
            gridcolor="#4f5b66"
        )
        fig.update_yaxes(
            title_text="BTC Price (USD)" if not same_axis_checkbox else "",
            type="log" if scale_option == "Log" else "linear",
            secondary_y=True,
            gridcolor="#4f5b66"
        )
    
        config = {
            'editable': True,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']
        }
        st.plotly_chart(fig, use_container_width=True, config=config)

######################################
# 9) ADDRESS BALANCE BANDS SECTION (unchanged)
######################################
st.header("Address Balance Bands Over Time")
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
colA, colB, colC = st.columns(3)
with colA:
    default_bands_start_date = datetime.date(2015, 1, 1)
    selected_bands_start_date = st.date_input("Start Date for Bands", value=default_bands_start_date, help="Filter data from this date onward.")
with colB:
    scale_option_bands = st.radio("Y-axis Scale for Bands", ["Linear", "Log"], index=0)
with colC:
    show_bands_ema = st.checkbox("Add EMA for Bands?", value=False)
    if show_bands_ema:
        bands_ema_period = st.number_input("Bands EMA Period (days)", min_value=2, max_value=200, value=20)
if not selected_bands:
    st.warning("Please select at least one band.")
    st.stop()
bands_str = ", ".join([f"'{b}'" for b in selected_bands])
daily_counts_query = f"""
    SELECT DAY, BALANCE_BAND, ADDRESS_COUNT
    FROM BTC_DATA.DATA.ADDRESS_BALANCE_BANDS_DAILY
    WHERE DAY >= '{selected_bands_start_date}' AND BALANCE_BAND IN ({bands_str})
    ORDER BY DAY
"""
bands_df = session.sql(daily_counts_query).to_pandas()
if bands_df.empty:
    st.warning("No data returned for the selected balance bands and date range.")
    st.stop()
pivot_df = bands_df.pivot(index="DAY", columns="BALANCE_BAND", values="ADDRESS_COUNT").fillna(0).reset_index()
if show_bands_ema:
    for band in selected_bands:
        ema_column_name = f"EMA_{band}"
        pivot_df[ema_column_name] = pivot_df[band].ewm(span=bands_ema_period).mean()
fig_bands = go.Figure()
for band in selected_bands:
    fig_bands.add_trace(
        go.Scatter(x=pivot_df["DAY"], y=pivot_df[band], mode="lines", name=band)
    )
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
