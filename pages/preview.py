import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
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


st.markdown("""
**Legend:**  
🟢 **Green (🔼 Increase, > Threshold for unchanged state)**  
🟡 **Yellow (⏸ Unchanged, within ± Threshold for unchanged state)**  
🔴 **Red (🔽 Decrease, > Threshold for unchanged state)**
""", unsafe_allow_html=True)

######################################
# 9) BTC Candlestick Chart with Dynamic Span
######################################
st.header("BTC Candlestick Chart")

# Sidebar selection for the candle chart span
candle_span = st.selectbox("Select Candle Chart Span", ["Daily", "Weekly", "Monthly"], index=0)

# Map the chosen span to the corresponding Snowflake date_trunc interval
if candle_span == "Daily":
    span_interval = "day"
elif candle_span == "Weekly":
    span_interval = "week"
elif candle_span == "Monthly":
    span_interval = "month"

# Build the query to aggregate open, high, low, close for each period
candle_query = f"""
WITH cte AS (
    SELECT 
        DATE_TRUNC('{span_interval}', {BTC_PRICE_DATE_COL}) AS period,
        {BTC_PRICE_DATE_COL} AS date,
        {BTC_PRICE_VALUE_COL} AS price,
        ROW_NUMBER() OVER (
            PARTITION BY DATE_TRUNC('{span_interval}', {BTC_PRICE_DATE_COL})
            ORDER BY {BTC_PRICE_DATE_COL} ASC
        ) AS rn_asc,
        ROW_NUMBER() OVER (
            PARTITION BY DATE_TRUNC('{span_interval}', {BTC_PRICE_DATE_COL})
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
    "ACTIVE ADDRESSES": {
        "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
        "date_col": "DATE", 
        "numeric_cols": ["ACTIVE_ADDRESSES"]
    },
    "ADDRESSES PROFIT LOSS PERCENT": {
        "table_name": "BTC_DATA.DATA.ADDRESSES_PROFIT_LOSS_PERCENT",
        "date_col": "sale_date", 
        "numeric_cols": ["PERCENT_PROFIT", "PERCENT_LOSS"]
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
    "BTC PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_USD",
        "date_col": "DATE",
        "numeric_cols": [
            "BTC_PRICE_USD",
        ]
    },
    "BTC PRICE MOUVEMENT": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_MOVEMENT",
        "date_col": "DATE",
        "numeric_cols": [
            "PRICE_MOVEMENT"
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
        "numeric_cols": ["INFLOW", "OUTFLOW", "NETFLOW"]
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
        "table_name": "BTC_DATA.DATA.MVRV_WITH_HOLDER_TYPES",
        "date_col": "DATE",
        "numeric_cols": ["OVERALL_MVRV", "STH_MVRV", "LTH_MVRV"]
    },
    "NUPL": {
        "table_name": "BTC_DATA.DATA.NUPL",
        "date_col": "DATE",
        "numeric_cols": ["NUPL", "NUPL_PERCENT"]
    },
     "PUELL MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINTED_BTC",
            "DAILY_ISSUANCE_USD",
            "MA_365_ISSUANCE_USD",
            "PUELL_MULTIPLE"
        ]
    },
    "REALIZED_CAP_VS_MARKET_CAP": {
        "table_name": "BTC_DATA.DATA.REALIZED_CAP_VS_MARKET_CAP",
        "date_col": "DATE",
        "numeric_cols": ["MARKET_CAP_USD", "REALIZED_CAP_USD"]
    },
    "SOPR": {
        "table_name": "BTC_DATA.DATA.SOPR",
        "date_col": "spent_date",
        "numeric_cols": ["SOPR"]
    },
    "SOPR WITH HOLDER TYPES": {
        "table_name": "BTC_DATA.DATA.SOPR_WITH_HOLDER_TYPES",
        "date_col": "sale_date",
        "numeric_cols": ["OVERALL_SOPR", "STH_SOPR", "LTH_SOPR"]
    },
    "STOCK TO FLOW MODEL": {
        "table_name": "BTC_DATA.DATA.STOCK_TO_FLOW_MODEL",
        "date_col": "DATE",
        "numeric_cols": ["STOCK", "FLOW", "STOCK_TO_FLOW", "MODEL_PRICE"]
    },
    "TX COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "BLOCK_TIMESTAMP",
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
    "TX BANDS": {
        "table_name": "BTC_DATA.DATA.TX_BANDS",
        "date_col": "TX_DATE",
        "numeric_cols": [
            "TX_GT_1_BTC",
            "TX_GT_10_BTC",
            "TX_GT_100_BTC",
            "TX_GT_1000_BTC",
            "TX_GT_10000_BTC",
            "TX_GT_100000_BTC"
            ]
    },
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
    
    # Date range: Start and optional End date (with unique keys)
    default_start_date = datetime.date(2015, 1, 1)
    start_date = st.date_input("Start Date", value=default_start_date, key="corr_start_date")
    
    activate_end_date = st.checkbox("Activate End Date", value=False, key="corr_activate_end")
    if activate_end_date:
        default_end_date = datetime.date.today()
        end_date = st.date_input("End Date", value=default_end_date, key="corr_end_date")
    else:
        end_date = None

    # Build the union of available features (renamed with table prefix)
    available_features = []
    for tbl in selected_tables:
        tbl_info = TABLE_DICT[tbl]
        for col in tbl_info["numeric_cols"]:
            available_features.append(f"{tbl}:{col}")
    
    # Let the user choose which features (from the selected tables) to include
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
        # Let user select from the features they already selected, which ones to EMA-transform
        ema_features = st.multiselect(
            "Select features to apply EMA on (raw values will be replaced):",
            selected_features,
            default=selected_features,
            key="ema_features"
        )
    else:
        ema_features = []

######################################
# Data Query & Merge
######################################
df_list = []
for tbl in selected_tables:
    tbl_info = TABLE_DICT[tbl]
    date_col = tbl_info["date_col"]
    # Determine which numeric columns from this table are selected by the user.
    table_features = {f"{tbl}:{col}" for col in tbl_info["numeric_cols"]}
    features_to_query = table_features.intersection(set(selected_features))
    if not features_to_query:
        continue  # Skip table if no feature is selected from it.
    # Map back to raw column names (remove prefix)
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
    # Rename raw columns to have the table prefix
    rename_dict = {col: f"{col}" for col in raw_cols}
    df.rename(columns=rename_dict, inplace=True)
    df_list.append(df)

if not df_list:
    st.error("No data returned for selected tables/features.")
    st.stop()

# Merge all dataframes on DATE using an outer join
merged_df = df_list[0]
for df in df_list[1:]:
    merged_df = pd.merge(merged_df, df, on="DATE", how="outer")
merged_df.sort_values("DATE", inplace=True)
merged_df = merged_df.dropna(how="all")

######################################
# Apply EMA (if selected)
######################################
if apply_ema:
    for feature in ema_features:
        if feature in merged_df.columns:
            # Compute EMA and replace raw values with EMA values
            ema_col = f"EMA_{feature}"
            merged_df[ema_col] = merged_df[feature].ewm(span=ema_period).mean()
            # Replace raw feature with EMA version
            merged_df[feature] = merged_df[ema_col]
            # Optionally drop the temporary EMA column:
            merged_df.drop(columns=[ema_col], inplace=True)

######################################
# Compute Correlation Matrix
######################################
# Remove DATE column for correlation computation
corr_matrix = merged_df.drop(columns=["DATE"]).corr(method='pearson')

######################################
# Plot Correlation Heatmap using Matplotlib/Seaborn
######################################
st.subheader("Correlation Matrix Heatmap")

num_features = len(corr_matrix.columns)
fig_width = max(8, num_features * 0.8)
fig_height = max(6, num_features * 0.8)
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

# Set dark background
fig.patch.set_facecolor("black")
ax.set_facecolor("black")

sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="RdBu_r",
    vmin=-1,
    vmax=1,
    square=True,
    ax=ax,
    fmt=".2f",
    cbar_kws={'shrink': 0.75, 'label': 'Correlation'}
)
ax.set_title("Correlation Matrix of On-chain Features", color="white")
plt.xticks(rotation=45, ha="right", color="white")
plt.yticks(rotation=0, color="white")

st.pyplot(fig)


"""
import io

######################################
# Plot Correlation Heatmap using Matplotlib/Seaborn
######################################
st.subheader("Correlation Matrix Heatmap")

num_features = len(corr_matrix.columns)
fig_width = max(8, num_features * 0.8)
fig_height = max(6, num_features * 0.8)
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

# Paramètres pour le thème sombre (affiché dans l'app)
fig.patch.set_facecolor("black")
ax.set_facecolor("black")
sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="RdBu_r",
    vmin=-1,
    vmax=1,
    square=True,
    ax=ax,
    fmt=".2f",
    cbar_kws={'shrink': 0.75, 'label': 'Correlation'}
)
ax.set_title("Correlation Matrix of On-chain Features", color="white")
plt.xticks(rotation=45, ha="right", color="white")
plt.yticks(rotation=0, color="white")

st.plotly_chart(fig, use_container_width=True)  # ou st.pyplot(fig) selon votre préférence

######################################
# Option to Save Plot on White Background
######################################
if st.button("Save Correlation Plot (White Background)"):
    # Créer une nouvelle figure identique mais avec fond blanc
    fig_save, ax_save = plt.subplots(figsize=(fig_width, fig_height))
    fig_save.patch.set_facecolor("white")
    ax_save.set_facecolor("white")
    
    sns.heatmap(
        corr_matrix,
        annot=True,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        square=True,
        ax=ax_save,
        fmt=".2f",
        cbar_kws={'shrink': 0.75, 'label': 'Correlation'}
    )
    ax_save.set_title("Correlation Matrix of On-chain Features", color="black")
    plt.xticks(rotation=45, ha="right", color="black")
    plt.yticks(rotation=0, color="black")
    
    # Enregistrer la figure dans un buffer
    buf = io.BytesIO()
    fig_save.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    st.download_button("Download Plot as PNG", data=buf, file_name="correlation_heatmap.png", mime="image/png")
    
    plt.close(fig_save)
"""
