import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import random
import calendar



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
    SELECT DATE, AVG_PRICE, PRICE_MOVEMENT_STATE 
    FROM BTC_DATA.DATA.BTC_PRICE_MOVEMENT_WEEKLY
    WHERE AVG_PRICE IS NOT NULL
      AND DATE >= '{selected_start_date}'
"""

if selected_end_date:
    btc_movement_query += f" AND DATE <= '{selected_end_date}'"

btc_movement_query += " ORDER BY DATE"

df_btc_movement = session.sql(btc_movement_query).to_pandas()

# Define mapping for five distinct states with colors and labels:
state_color_label = {
    2: {"color": "#ad0c00", "label": "Increase significantly"},
    1: {"color": "#ff6f00", "label": "Moderate increase"},
    0: {"color": "#fffb00", "label": "Unchanged"},
    -1: {"color": "#55ff00", "label": "Moderate decrease"},
    -2: {"color": "#006e07", "label": "Decrease significantly"}
}

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
                y=df_btc_movement["AVG_PRICE"],
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
                y=df_btc_movement["AVG_PRICE"],
                name="BTC Price (USD)",
                marker_color="#3498DB"
            ),
            secondary_y=True
        )

# Scatter plot for BTC Price Movement States:
# Loop through each state to add a separate scatter trace with its unique color.
if show_movement_scatter:
    for state in sorted(state_color_label.keys(), reverse=True):  # ordering: 2,1,0,-1,-2
        state_data = df_btc_movement[df_btc_movement["PRICE_MOVEMENT_STATE"] == state]
        if not state_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=state_data["DATE"],
                    y=state_data["AVG_PRICE"],
                    mode="markers",
                    marker=dict(color=state_color_label[state]["color"], size=6),
                    name=state_color_label[state]["label"]
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

######################################
# 9) BTC Candlestick Chart with Dynamic Span
######################################
st.header("BTC Candlestick Chart")

# Sidebar selection for the candle chart span
candle_span = st.selectbox("Select Candle Chart Span", ["Daily", "Weekly", "Monthly"], index=0)

# Determine the period expression based on the selected span
if candle_span == "Daily":
    period_expr = f"DATE_TRUNC('day', {BTC_PRICE_DATE_COL})"
elif candle_span == "Weekly":
    # For weekly grouping from Monday to Sunday, calculate Monday as the period start.
    # In Snowflake, DAYOFWEEK returns 1 for Sunday, 2 for Monday, ..., 7 for Saturday.
    # For a Sunday record, subtract 6 days; otherwise, subtract (DAYOFWEEK - 2) days.
    period_expr = (
        f"DATEADD(day, CASE WHEN DAYOFWEEK({BTC_PRICE_DATE_COL}) = 1 "
        f"THEN -6 ELSE 2 - DAYOFWEEK({BTC_PRICE_DATE_COL}) END, {BTC_PRICE_DATE_COL})"
    )
elif candle_span == "Monthly":
    period_expr = f"DATE_TRUNC('month', {BTC_PRICE_DATE_COL})"

# Build the query to aggregate open, high, low, close for each period
candle_query = f"""
WITH cte AS (
    SELECT 
        {period_expr} AS period,
        {BTC_PRICE_DATE_COL} AS date,
        {BTC_PRICE_VALUE_COL} AS price,
        ROW_NUMBER() OVER (
            PARTITION BY {period_expr}
            ORDER BY {BTC_PRICE_DATE_COL} ASC
        ) AS rn_asc,
        ROW_NUMBER() OVER (
            PARTITION BY {period_expr}
            ORDER BY {BTC_PRICE_DATE_COL} DESC
        ) AS rn_desc
    FROM {BTC_PRICE_TABLE}
    WHERE {BTC_PRICE_DATE_COL} >= '{selected_start_date}'
"""

if selected_end_date:
    candle_query += f" AND {BTC_PRICE_DATE_COL} <= '{selected_end_date}'"

candle_query += f"""
)
SELECT
    period,
    MAX(CASE WHEN rn_asc = 1 THEN price END) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    MAX(CASE WHEN rn_desc = 1 THEN price END) AS close
FROM cte
GROUP BY period
ORDER BY period
"""

# Execute the query and convert the result to a pandas DataFrame
df_candle = session.sql(candle_query).to_pandas()

# For Weekly and Monthly spans, optionally compute the period_end for display purposes.
if candle_span == "Weekly":
    # For a week that starts on Monday, the period end is 6 days later (Sunday).
    df_candle['period_end'] = pd.to_datetime(df_candle['PERIOD']) + pd.Timedelta(days=6)
elif candle_span == "Monthly":
    # For monthly span, compute the last day of the month.
    df_candle['period_end'] = pd.to_datetime(df_candle['PERIOD']).apply(
        lambda d: d.replace(day=calendar.monthrange(d.year, d.month)[1])
    )

# Create and display the candlestick chart
fig_candle = go.Figure(data=[go.Candlestick(
    x=df_candle["PERIOD"],
    open=df_candle["OPEN"],
    high=df_candle["HIGH"],
    low=df_candle["LOW"],
    close=df_candle["CLOSE"],
    increasing_line_color='green',
    decreasing_line_color='red',
)])

fig_candle.update_yaxes(
    type="log" if scale_option_price == "Log" else "linear",
    gridcolor="#4f5b66"
)

fig_candle.update_layout(
    title=f"BTC Candlestick Chart ({candle_span} Span)",
    xaxis_title="Date",
    yaxis_title="BTC Price (USD)",
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    font=dict(color="#f0f2f6"),
    xaxis=dict(rangeslider_visible=False)
)

st.plotly_chart(fig_candle, use_container_width=True)

# Convert DataFrame to CSV and add a download button
csv_data = df_candle.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name=f"btc_candlestick_{candle_span.lower()}.csv",
    mime="text/csv",
)


st.title("Correlation Matrix of On-chain Features")



######################################
# Table Configurations
######################################
TABLE_DICT = {
    "BTC_PRICE_MOVEMENT": {
         "table_name": "BTC_DATA.DATA.BTC_PRICE_MOVEMENT_WEEKLY",
         "date_col": "DATE",
         "numeric_cols": ["AVG_PRICE", "PRICE_MOVEMENT_STATE"]
    },
    "ACTIVE_ADDRESSES": {
         "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
         "date_col": "DATE",
         "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "BTC_REALIZED_CAP_AND_PRICE": {
         "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
         "date_col": "DATE",
         "numeric_cols": ["REALIZED_CAP_USD", "TOTAL_UNSPENT_BTC", "REALIZED_PRICE_USD"]
    },
    "CDD": {
         "table_name": "BTC_DATA.DATA.CDD",
         "date_col": "DATE",
         "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
    },
    "EXCHANGE_FLOW": {
         "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
         "date_col": "DATE",
         "numeric_cols": ["INFLOW", "OUTFLOW", "NETFLOW"]
    },
    "HOLDER_REALIZED_PRICES": {
         "table_name": "BTC_DATA.DATA.HOLDER_REALIZED_PRICES",
         "date_col": "DATE",
         "numeric_cols": ["STH_REALIZED_PRICE", "LTH_REALIZED_PRICE"]
    },
    "MVRV": {
         "table_name": "BTC_DATA.DATA.MVRV",
         "date_col": "DATE",
         "numeric_cols": ["REALIZED_CAP_USD", "TOTAL_UNSPENT_BTC", "MARKET_CAP_USD", "MVRV"]
    },
    "MVRV_WITH_HOLDER_TYPES": {
         "table_name": "BTC_DATA.DATA.MVRV_WITH_HOLDER_TYPES",
         "date_col": "DATE",
         "numeric_cols": ["OVERALL_MVRV", "STH_MVRV", "LTH_MVRV"]
    },
    "NUPL": {
         "table_name": "BTC_DATA.DATA.NUPL",
         "date_col": "DATE",
         "numeric_cols": ["MARKET_CAP_USD", "REALIZED_CAP_USD", "NUPL", "NUPL_PERCENT"]
    },
    "PUELL_MULTIPLE": {
         "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
         "date_col": "DATE",
         "numeric_cols": ["MINTED_BTC", "DAILY_ISSUANCE_USD", "MA_365_ISSUANCE_USD", "PUELL_MULTIPLE"]
    },
    "SOPR": {
         "table_name": "BTC_DATA.DATA.SOPR",
         "date_col": "SPENT_DATE",
         "numeric_cols": ["SOPR"]
    },
    "SOPR_WITH_HOLDER_TYPES": {
         "table_name": "BTC_DATA.DATA.SOPR_WITH_HOLDER_TYPES",
         "date_col": "DATE",
         "numeric_cols": ["OVERALL_SOPR", "STH_SOPR", "LTH_SOPR"]
    },
    "TX_VOLUME": {
         "table_name": "BTC_DATA.DATA.TX_VOLUME",
         "date_col": "DATE",
         "numeric_cols": ["DAILY_TX_VOLUME_BTC"]
    }
}

######################################
# Sidebar Controls
######################################
with st.sidebar:
    st.header("Correlation Settings")
    
    # Select tables to include
    selected_tables = st.multiselect(
        "Select tables to include:",
        list(TABLE_DICT.keys()),
        default=list(TABLE_DICT.keys())[:3],
        help="Choose the on-chain tables you want to analyze."
    )
    
    # Date range: Start and optional End date
    default_start_date = datetime.date(2015, 1, 1)
    start_date = st.date_input("Start Date", value=default_start_date, key="corr_start_date")
    
    activate_end_date = st.checkbox("Activate End Date", value=False, key="corr_activate_end")
    if activate_end_date:
        default_end_date = datetime.date.today()
        end_date = st.date_input("End Date", value=default_end_date, key="corr_end_date")
    else:
        end_date = None

    # Build available features with table prefix (e.g. "TABLE:column")
    available_features = []
    for tbl in selected_tables:
        tbl_info = TABLE_DICT[tbl]
        for col in tbl_info["numeric_cols"]:
            available_features.append(f"{tbl}:{col}")
    
    # Let the user choose which features to include for correlation
    selected_features = st.multiselect(
        "Select Features for Correlation:",
        available_features,
        default=available_features,
        key="selected_features"
    )
    
    # Option to apply EMA on selected features
    apply_ema = st.checkbox("Apply EMA on selected features", value=False, key="apply_ema")
    if apply_ema:
        ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20, key="ema_period")
        ema_features = st.multiselect(
            "Select features to apply EMA on (raw values will be replaced):",
            selected_features,
            default=selected_features,
            key="ema_features"
        )
    else:
        ema_features = []

######################################
# DAILY DATA: Query & Merge (Raw Data)
######################################
df_list = []
for tbl in selected_tables:
    tbl_info = TABLE_DICT[tbl]
    date_col = tbl_info["date_col"]
    # Only query numeric columns that are in the selected features (formatted as "TABLE:column")
    table_features = {f"{tbl}:{col}" for col in tbl_info["numeric_cols"]}
    features_to_query = table_features.intersection(set(selected_features))
    if not features_to_query:
        continue  # Skip table if no feature is selected.
    # Get raw column names from the selected features
    raw_cols = [feat.split(":", 1)[1] for feat in features_to_query]
    cols_for_query = ", ".join(raw_cols)
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {cols_for_query}
        FROM {tbl_info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{start_date}'
    """
    if end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date}'\n"
    query += "ORDER BY DATE"
    df = session.sql(query).to_pandas()
    # Rename raw columns to include the table prefix (e.g. "TABLE:column")
    rename_dict = {col: f"{tbl}:{col}" for col in raw_cols}
    df.rename(columns=rename_dict, inplace=True)
    df_list.append(df)

if not df_list:
    st.error("No data returned for selected tables/features.")
    st.stop()

# Merge all daily dataframes on DATE using an outer join
merged_df = df_list[0]
for df in df_list[1:]:
    merged_df = pd.merge(merged_df, df, on="DATE", how="outer")
merged_df.sort_values("DATE", inplace=True)
merged_df = merged_df.dropna(how="all")

# Optionally apply EMA on daily data if selected
if apply_ema:
    for feature in ema_features:
        if feature in merged_df.columns:
            ema_col = f"EMA_{feature}"
            merged_df[ema_col] = merged_df[feature].ewm(span=ema_period).mean()
            merged_df[feature] = merged_df[ema_col]
            merged_df.drop(columns=[ema_col], inplace=True)

# ----- DAILY CORRELATION -----
# For daily correlation, we want BTC price (AVG_PRICE) by default.
daily_features = [col for col in selected_features if col != "BTC_PRICE_MOVEMENT:PRICE_MOVEMENT_STATE"]
if "BTC_PRICE_MOVEMENT:AVG_PRICE" not in daily_features:
    daily_features.append("BTC_PRICE_MOVEMENT:AVG_PRICE")

daily_corr_df = merged_df[[col for col in merged_df.columns if col in daily_features]]
daily_corr_matrix = daily_corr_df.corr(method='pearson')

st.subheader("Daily Correlation Matrix Heatmap (Selected Features)")
num_features = len(daily_corr_matrix.columns)
fig_width = max(8, num_features * 0.8)
fig_height = max(6, num_features * 0.8)
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
fig.patch.set_facecolor("black")
ax.set_facecolor("black")
sns.heatmap(
    daily_corr_matrix,
    annot=True,
    cmap="RdBu_r",
    vmin=-1,
    vmax=1,
    square=True,
    ax=ax,
    fmt=".2f",
    cbar_kws={'shrink': 0.75, 'label': 'Correlation'}
)
ax.set_title("Correlation Matrix of Selected On-chain Features (Daily)", color="white")
plt.xticks(rotation=45, ha="right", color="white")
plt.yticks(rotation=0, color="white")
st.pyplot(fig)

####################################################################################
# WEEKLY AGGREGATED DATA: Query & Merge (Indicators Movement)
####################################################################################
st.subheader("Weekly Aggregated Correlation: BTC Price Movement & Indicators Movement")

# Helper function to query weekly aggregated data for a given table (using AVG aggregation)
def get_weekly_data(tbl_info, start_date, end_date):
    date_col = tbl_info["date_col"]
    numeric_cols = tbl_info["numeric_cols"]
    agg_cols = ", ".join([f"AVG({col}) AS {col}" for col in numeric_cols])
    query = f"""
        WITH weekly_data AS (
            SELECT 
                DATEADD(day, 
                    CASE 
                        WHEN DAYOFWEEK(CAST({date_col} AS DATE)) = 1 THEN -6 
                        ELSE 2 - DAYOFWEEK(CAST({date_col} AS DATE)) 
                    END, CAST({date_col} AS DATE)) AS week_start,
                {agg_cols}
            FROM {tbl_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{start_date}'
    """
    if end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date}'\n"
    query += f"""
            GROUP BY DATEADD(day, 
                    CASE 
                        WHEN DAYOFWEEK(CAST({date_col} AS DATE)) = 1 THEN -6 
                        ELSE 2 - DAYOFWEEK(CAST({date_col} AS DATE)) 
                    END, CAST({date_col} AS DATE))
        )
        SELECT week_start AS DATE, {', '.join(numeric_cols)}
        FROM weekly_data
        ORDER BY week_start
    """
    return session.sql(query).to_pandas()

weekly_df_list = []
for tbl in selected_tables:
    tbl_info = TABLE_DICT[tbl]
    if tbl == "BTC_PRICE_MOVEMENT":
        # Use the provided BTC price movement weekly query
        btc_price_query = f"""
        WITH weekly_avg AS (
            SELECT 
                DATEADD(day, 
                    CASE 
                        WHEN DAYOFWEEK(DATE) = 1 THEN -6 
                        ELSE 2 - DAYOFWEEK(DATE) 
                    END, DATE) AS week_start,
                AVG(BTC_PRICE_USD) AS avg_price
            FROM BTC_DATA.DATA.BTC_PRICE_USD
            GROUP BY DATEADD(day, 
                CASE 
                    WHEN DAYOFWEEK(DATE) = 1 THEN -6 
                    ELSE 2 - DAYOFWEEK(DATE) 
                END, DATE)
        )
        SELECT
            week_start AS DATE,
            avg_price,
            LAG(avg_price) OVER (ORDER BY week_start) AS prev_avg,
            CASE 
                WHEN LAG(avg_price) OVER (ORDER BY week_start) IS NULL THEN NULL
                WHEN NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) IS NULL THEN 0
                WHEN ABS((avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                       / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100) <= 0.5 THEN 0
                WHEN (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 > 0.5 
                     AND (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 < 8.0 THEN 1
                WHEN (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 >= 8.0 THEN 2
                WHEN (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 < -0.5 
                     AND (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 > -8.0 THEN -1
                WHEN (avg_price - LAG(avg_price) OVER (ORDER BY week_start))
                     / NULLIF(LAG(avg_price) OVER (ORDER BY week_start), 0) * 100 <= -8.0 THEN -2
                ELSE 0
            END AS price_movement_state
        FROM weekly_avg
        ORDER BY week_start;
        """
        df_btc_weekly = session.sql(btc_price_query).to_pandas()
        # Rename columns so they include the table prefix
        df_btc_weekly.rename(columns={
            "avg_price": "BTC_PRICE_MOVEMENT:AVG_PRICE",
            "price_movement_state": "BTC_PRICE_MOVEMENT:PRICE_MOVEMENT_STATE"
        }, inplace=True)
        weekly_df_list.append(df_btc_weekly)
    else:
        df_tbl = get_weekly_data(tbl_info, start_date, end_date)
        rename_dict = {col: f"{tbl}:{col}" for col in tbl_info["numeric_cols"]}
        df_tbl.rename(columns=rename_dict, inplace=True)
        weekly_df_list.append(df_tbl)

if not weekly_df_list:
    st.error("No weekly data returned for selected tables/features.")
    st.stop()

# Merge all weekly dataframes on DATE using an outer join
weekly_merged_df = weekly_df_list[0]
for df in weekly_df_list[1:]:
    weekly_merged_df = pd.merge(weekly_merged_df, df, on="DATE", how="outer")
weekly_merged_df.sort_values("DATE", inplace=True)
weekly_merged_df = weekly_merged_df.dropna(how="all")

# Optionally apply EMA on weekly data if selected
if apply_ema:
    for feature in ema_features:
        if feature in weekly_merged_df.columns:
            ema_col = f"EMA_{feature}"
            weekly_merged_df[ema_col] = weekly_merged_df[feature].ewm(span=ema_period).mean()
            weekly_merged_df[feature] = weekly_merged_df[ema_col]
            weekly_merged_df.drop(columns=[ema_col], inplace=True)

# ----- WEEKLY CORRELATION -----
# For weekly correlation, we want BTC price movement state by default.
weekly_features = [col for col in selected_features if col != "BTC_PRICE_MOVEMENT:AVG_PRICE"]
if "BTC_PRICE_MOVEMENT:PRICE_MOVEMENT_STATE" not in weekly_features:
    weekly_features.append("BTC_PRICE_MOVEMENT:PRICE_MOVEMENT_STATE")

weekly_corr_df = weekly_merged_df[[col for col in weekly_merged_df.columns if col in weekly_features]]
weekly_corr_matrix = weekly_corr_df.corr(method='pearson')

st.subheader("Weekly Aggregated Correlation Matrix Heatmap (Selected Features)")
num_features = len(w
