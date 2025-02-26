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
    layout="wide",  # We'll use a wide layout to have a sidebar + large chart
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
        "friendly_name": "Active Addresses",
        "date_col": "DATE",
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "friendly_name": "NUPL",
        "date_col": "DATE",
        "numeric_cols": ["NUPL", "NUPL_PERCENT"]
    },
    "PUELL_MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "friendly_name": "Puell Multiple",
        "date_col": "DATE",
        "numeric_cols": ["MINTED_BTC","DAILY_ISSUANCE_USD","MA_365_ISSUANCE_USD","PUELL_MULTIPLE"]
    },
    # ... Add the rest of your tables similarly ...
}

BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
BTC_PRICE_DATE_COL = "DATE"
BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"

######################################
# 5) Page Title
######################################
st.title("Bitcoin On-chain Indicators Dashboard")

######################################
# 6) SIDEBAR - Glassnode-style
######################################
# We'll use the sidebar to show a search bar, a list of indicators, and other controls.

with st.sidebar:
    st.header("Select Indicators")

    # 6.1) Search bar
    search_query = st.text_input("Search indicators", "").strip().lower()

    # 6.2) Build a list of (table_key, col_name, label) for all indicators
    #     e.g. [("PUELL_MULTIPLE","PUELL_MULTIPLE","Puell Multiple : PUELL_MULTIPLE"), ...]
    all_indicators = []
    for tbl_key, tbl_info in TABLE_DICT.items():
        for col in tbl_info["numeric_cols"]:
            label_str = f"{tbl_info['friendly_name']} : {col}"
            # We'll store a tuple for easy reference
            all_indicators.append((tbl_key, col, label_str))

    # 6.3) Filter by the search query if typed
    if search_query:
        filtered_indicators = [
            (tbl_key, col, label)
            for (tbl_key, col, label) in all_indicators
            if search_query in label.lower()
        ]
    else:
        filtered_indicators = all_indicators

    # 6.4) Checkboxes for each filtered indicator
    selected_indicators = []
    for (tbl_key, col, label) in filtered_indicators:
        checked = st.checkbox(label, value=False)
        if checked:
            selected_indicators.append((tbl_key, col))

    # 6.5) Additional controls (date range, chart type, etc.)
    st.markdown("---")
    st.subheader("Chart Settings")

    default_start_date = datetime.date(2015, 1, 1)
    selected_start_date = st.date_input("Start Date", value=default_start_date)

    scale_option = st.radio("Y-axis Scale", ["Linear", "Log"], index=0)
    chart_type = st.radio("Chart Type", ["Line", "Bars"], index=0)

    show_ema = st.checkbox("Add EMA to indicators", value=False)
    if show_ema:
        ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20)

    # 6.6) BTC Price toggle & CPD
    st.markdown("---")
    st.subheader("BTC Price Options")
    include_btc = st.checkbox("Include BTC Price", value=True)
    same_axis_checkbox = st.checkbox("Plot BTC Price on same Y-axis?", value=False)
    detect_cpd = st.checkbox("Detect BTC Price Change Points?", value=False)
    pen_value = st.number_input("CPD Penalty (if CPD on)", min_value=1, max_value=200, value=10)

######################################
# 7) MAIN CHART AREA
######################################
plot_container = st.container()
with plot_container:
    # 7.1) If no indicators selected and BTC Price not included, show a warning
    if not selected_indicators and not include_btc:
        st.warning("Please select at least one indicator or enable BTC Price.")
        st.stop()

    # 7.2) Build dataframes for each selected indicator
    df_list = []
    for (tbl_key, col) in selected_indicators:
        tbl_info = TABLE_DICT[tbl_key]
        date_col = tbl_info["date_col"]
        query = f"""
            SELECT
                CAST({date_col} AS DATE) AS DATE,
                {col}
            FROM {tbl_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
            ORDER BY DATE
        """
        df = session.sql(query).to_pandas()
        # rename the numeric column to something unique: "tbl_key:col"
        unique_col_name = f"{tbl_key}:{col}"
        df.rename(columns={col: unique_col_name}, inplace=True)
        df_list.append(df)

    # 7.3) BTC Price (if selected)
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
        st.warning("No data returned. Check your selections or date range.")
        st.stop()

    # 7.4) Merge all dataframes on DATE
    merged_df = df_list[0]
    for df in df_list[1:]:
        merged_df = pd.merge(merged_df, df, on="DATE", how="outer")
    merged_df.sort_values("DATE", inplace=True)

    # 7.5) Add EMA if requested
    if show_ema:
        for col in merged_df.columns:
            if col == "DATE":
                continue
            merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()

    # 7.6) Build the Plotly figure
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # We'll track which columns are "BTC_PRICE" vs others
    # If col == "BTC_PRICE", we plot on secondary axis if same_axis_checkbox is False
    # or if detect_cpd is enabled, we do CPD lines.

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
                        line=dict(color=st.session_state["colors"].get(col, "#FFFFFF"))
                    ),
                    secondary_y=secondary_y
                )
            else:
                fig.add_trace(
                    go.Bar(
                        x=merged_df["DATE"],
                        y=merged_df[col],
                        name=col,
                        marker_color=st.session_state["colors"].get(col, "#FFFFFF")
                    ),
                    secondary_y=secondary_y
                )
            if show_ema and f"EMA_{col}" in merged_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[f"EMA_{col}"],
                        mode="lines",
                        name=f"EMA({ema_period}) - {col}",
                        line=dict(color=st.session_state["colors"].get(col, "#FFFFFF"), dash="dot")
                    ),
                    secondary_y=secondary_y
                )
            # CPD for BTC Price
            if detect_cpd:
                price_series = merged_df[col].dropna()
                if not price_series.empty:
                    algo = rpt.Pelt(model="rbf").fit(price_series.values)
                    cpd_points = algo.predict(pen=pen_value)
                    for cp in cpd_points:
                        if cp < len(merged_df):
                            cp_date = merged_df["DATE"].iloc[cp]
                            fig.add_vline(x=cp_date, line_width=2, line_dash="dash", line_color="white")

        else:
            # Normal indicator
            if chart_type == "Line":
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
            if show_ema and f"EMA_{col}" in merged_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[f"EMA_{col}"],
                        mode="lines",
                        name=f"EMA({ema_period}) - {col}",
                        line=dict(color=st.session_state["colors"].get(col, "#FFFFFF"), dash="dot")
                    ),
                    secondary_y=False
                )

    # 7.7) Final chart styling
    fig.update_layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        title="Bitcoin On-chain Indicators",
        hovermode="x unified",
        font=dict(color="#f0f2f6"),
        legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
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
        'modeBarButtonsToAdd': [
            'drawline','drawopenpath','drawclosedpath',
            'drawcircle','drawrect','eraseshape'
        ]
    }
    st.plotly_chart(fig, use_container_width=True, config=config)

######################################
# 8) ADDRESS BALANCE BANDS SECTION
######################################
# We keep this section unchanged, or you can also move it into the sidebar style if you prefer.
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
    selected_bands_start_date = st.date_input("Start Date for Bands", value=default_bands_start_date)
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
    WHERE DAY >= '{selected_bands_start_date}'
      AND BALANCE_BAND IN ({bands_str})
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
        go.Scatter(
            x=pivot_df["DAY"],
            y=pivot_df[band],
            mode="lines",
            name=band
        )
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
    legend=dict(x=0, y=1.05, orientation="h", bgcolor="rgba(0,0,0,0)")
)
fig_bands.update_xaxes(title_text="Date", gridcolor="#4f5b66")
fig_bands.update_yaxes(
    title_text="Address Count",
    type="log" if scale_option_bands == "Log" else "linear",
    gridcolor="#4f5b66"
)
st.plotly_chart(fig_bands, use_container_width=True)
