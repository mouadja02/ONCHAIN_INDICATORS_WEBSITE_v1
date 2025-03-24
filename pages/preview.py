import streamlit as st
import pandas as pd
import numpy as np
import datetime
import random
import io
import math

import plotly.graph_objs as go
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="BTC Price & Indicator – Correlation & Plot",
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
    "#E74C3C", "#F1C40F", "#2ECC71", "#3498DB",
    "#9B59B6", "#1ABC9C", "#E67E22", "#FF00FF",
    "#FF1493", "#FFD700"
]
if "color_palette" not in st.session_state:
    st.session_state["color_palette"] = COLOR_PALETTE.copy()
    random.shuffle(st.session_state["color_palette"])
if "plot_lines" not in st.session_state:
    st.session_state["plot_lines"] = {}  # will hold final series for plotting

######################################
# 4) Table / Feature Mappings
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
            "REALIZED_PRICE_USD",
            "TOTAL_UNSPENT_BTC"
        ]
    },
    "BTC PRICE": {
        "table_name": "BTC_DATA.DATA.BTC_PRICE_USD",
        "date_col": "DATE",
        "numeric_cols": [
            "BTC_PRICE_USD"
        ]
    },
    "CDD": {
        "table_name": "BTC_DATA.DATA.CDD",
        "date_col": "DATE",
        "numeric_cols": ["CDD_RAW"]
    },
    "EXCHANGE_FLOW": {
        "table_name": "BTC_DATA.DATA.EXCHANGE_FLOW",
        "date_col": "DAY",
        "numeric_cols": [
            "INFLOW_BTC", "OUTFLOW_BTC", "NETFLOW_BTC", "EXCHANGE_RESERVE_BTC"
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
        "numeric_cols": ["NUPL"]
    },
    "PUELL MULTIPLE": {
        "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINTED_BTC",
            "PUELL_MULTIPLE"
        ]
    },
    "M2 GROWTH": {
        "table_name": "BTC_DATA.DATA.M2_GROWTH",
        "date_col": "DATE",
        "numeric_cols": [
            "M2_GLOBAL_SUPPLY"
        ]
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
    "STOCK TO FLOW MODEL": {
        "table_name": "BTC_DATA.DATA.STOCK_TO_FLOW",
        "date_col": "DATE",
        "numeric_cols": ["STOCK", "FLOW", "STOCK_TO_FLOW_RATIO"]
    },
    "TX COUNT": {
        "table_name": "BTC_DATA.DATA.TX_COUNT",
        "date_col": "DATE",
        "numeric_cols": ["TX_COUNT"]
    },
    "TRADE VOLUME": {
        "table_name": "BTC_DATA.DATA.TRADE_VOLUME",
        "date_col": "DATE",
        "numeric_cols": [ "TRADE_VOLUME", "DOMINANCE"]
    },
    "GOOGLE TREND": {
        "table_name": "BTC_DATA.DATA.GOOGLE_TREND",
        "date_col": "DATE",
        "numeric_cols": [ "INDEX"]
    },
    "FINANCIAL MARKET DATA": {
        "table_name": "BTC_DATA.DATA.FINANCIAL_MARKET_DATA",
        "date_col": "DATE",
        "numeric_cols": [
            "NASDAQ",
            "SP500",
            "VIX",
            "DXY",
            "IWM",
            "QQQ",
            "TLT",
            "GOLD",
            "PETROL"
        ]
    },
    "FEAR & GREED INDEX": {
        "table_name": "BTC_DATA.DATA.FEAR_GREED_INDEX",
        "date_col": "DATE",
        "numeric_cols": ["FNG_VALUE"]
    },  
    "MINERS REVENUE": {
        "table_name": "BTC_DATA.DATA.MINERS_REVENUE",
        "date_col": "DATE",
        "numeric_cols": [
            "MINER_REVENUE"
        ]
    },    
    "DAILY HASHRATE": {
        "table_name": "BTC_DATA.DATA.DAILY_HASHRATE",
        "date_col": "DATE",
        "numeric_cols": [
            "HASHRATE_THS"
        ]
    },    
    "NETWORK DIFFICULTY": {
        "table_name": "BTC_DATA.DATA.NETWORK_DIFFICULTY",
        "date_col": "DATE",
        "numeric_cols": [
            "AVG_DIFFICULTY"
        ]
    },
}


######################################
# 5) Page Title
######################################
st.title("BTC Price vs. Indicator – Lag/Derivative, Correlation & Plot")

######################################
# (A) Sidebar – Global & Feature Settings
######################################
with st.sidebar:
    st.header("Configuration")

    # Date range for querying & plotting
    st.subheader("Date Range")
    default_start = datetime.date(2015, 1, 1)
    query_start_date = st.date_input("Query Start Date", value=default_start, key="query_start")
    enable_query_end = st.checkbox("Set Query End Date", value=False, key="query_end_checkbox")
    if enable_query_end:
        query_end_date = st.date_input("Query End Date", value=datetime.date.today(), key="query_end")
    else:
        query_end_date = None

    st.markdown("---")

    # Correlation method
    corr_method = st.selectbox("Correlation Method", ["pearson", "spearman"], index=0)

    st.markdown("---")

    # 1. Choose Indicators for Correlation
    st.subheader("Choose Features for Correlation")
    all_tables = list(TABLE_DICT.keys())
    default_tables = ["BTC PRICE", "ACTIVE ADDRESSES", "CDD"]  # adjust as needed
    selected_tables = st.multiselect("Select tables to include:", all_tables, default=default_tables)
    
    available_features = []
    for tbl in selected_tables:
        for col in TABLE_DICT[tbl]["numeric_cols"]:
            feat_name = f"{tbl}:{col}"
            available_features.append(feat_name)
    # Ensure BTC PRICE is included, if not
    if "BTC PRICE:BTC_PRICE_USD" not in available_features:
        available_features.append("BTC PRICE:BTC_PRICE_USD")
    
    # Multi-select: for correlation, you can pick any number
    selected_features = st.multiselect("Select features for correlation:", available_features, default=available_features)

    st.markdown("---")

    # 2. Lag & Derivative Settings per Feature
    st.subheader("Lag & Derivative Settings")
    shifts = {}
    derivatives = {}
    
    # For BTC PRICE, always no lag; derivative optional.
    st.write("**BTC PRICE:BTC_PRICE_USD** (no lag)")
    btc_deriv = st.checkbox("Take derivative of BTC Price?", key="btc_deriv", value=False)
    shifts["BTC PRICE:BTC_PRICE_USD"] = 0
    derivatives["BTC PRICE:BTC_PRICE_USD"] = btc_deriv
    st.markdown("---")
    
    # For all other selected features:
    for feat in selected_features:
        if feat == "BTC PRICE:BTC_PRICE_USD":
            continue
        st.write(f"**{feat}**")
        shift_val = st.slider(f"Lag (days) for {feat}", -30, 30, 0, key=f"shift_{feat}")
        shifts[feat] = shift_val
        deriv_flag = st.checkbox(f"Take derivative of {feat}?", key=f"deriv_{feat}", value=False)
        derivatives[feat] = deriv_flag
        st.markdown("---")
        
    # 3. Interactive Plot – Choose ONE additional indicator (from selected_features, excluding BTC PRICE)
    st.subheader("Interactive Plot Settings")
    inter_options = [f for f in selected_features if f != "BTC PRICE:BTC_PRICE_USD"]
    if inter_options:
        interactive_indicator = st.selectbox("Select Indicator for Interactive Plot (with BTC Price):", options=inter_options, index=0)
    else:
        interactive_indicator = None
        
    # 4. Plotting Date Range (for final plots)
    st.subheader("Plotting Date Range")
    plot_start_date = st.date_input("Plot Start Date", value=default_start, key="plot_start")
    enable_plot_end = st.checkbox("Set Plot End Date", value=False, key="plot_end_checkbox")
    if enable_plot_end:
        plot_end_date = st.date_input("Plot End Date", value=datetime.date.today(), key="plot_end")
    else:
        plot_end_date = None

    st.markdown("---")
    
    # 5. Plot Button (for multi-line correlation plot)
    do_plot = st.button("Plot All Selected Features")

######################################
# (B) Data Query & Transform for Correlation
######################################
def load_feature(feature, start_date, end_date):
    """Load a single feature (table column) from Snowflake within the given date range."""
    tbl, col = feature.split(":", 1)
    info = TABLE_DICT[tbl]
    date_col = info["date_col"]
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {col}
        FROM {info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{start_date}'
    """
    if end_date:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date}'"
    query += " ORDER BY DATE"
    
    df = session.sql(query).to_pandas()
    df.rename(columns={col: feature}, inplace=True)
    df.sort_values("DATE", inplace=True)
    df.dropna(subset=[feature], inplace=True)
    return df.reset_index(drop=True)

# Query and transform each selected feature
dfs = {}
for feat in selected_features:
    df_feat = load_feature(feat, query_start_date, query_end_date)
    
    # Apply derivative if selected
    if derivatives.get(feat, False):
        df_feat[feat] = df_feat[feat].diff()
        df_feat.dropna(subset=[feat], inplace=True)
    
    # Apply shift if needed
    shift_val = shifts.get(feat, 0)
    if shift_val > 0:
        df_feat[feat] = df_feat[feat].shift(shift_val)
        df_feat.dropna(subset=[feat], inplace=True)
    
    dfs[feat] = df_feat

# Merge all features on DATE (using inner join)
merged_df = None
for feat, df_feat in dfs.items():
    if merged_df is None:
        merged_df = df_feat.copy()
    else:
        merged_df = pd.merge(merged_df, df_feat, on="DATE", how="inner")
if merged_df is not None:
    merged_df.sort_values("DATE", inplace=True)
    merged_df.dropna(inplace=True)

######################################
# (C) Correlation Matrix (on all selected features with applied lags)
######################################
st.subheader("Correlation Matrix of Selected Features (with applied lags)")
if merged_df is None or merged_df.empty or len(merged_df.columns) < 2:
    st.warning("Not enough data to compute correlation.")
else:
    # We need to apply lags properly for each feature in the correlation matrix
    # instead of just using the already merged dataframe
    
    # 1. Start with raw data for each feature (without derivatives or shifts yet)
    raw_dfs = {}
    for feat in selected_features:
        raw_dfs[feat] = load_feature(feat, query_start_date, query_end_date)
    
    # 2. Create a base date range (intersection of all feature date ranges)
    date_dfs = [df[["DATE"]] for df in raw_dfs.values()]
    base_dates = date_dfs[0].copy()
    for df in date_dfs[1:]:
        base_dates = pd.merge(base_dates, df, on="DATE", how="inner")
    base_dates.sort_values("DATE", inplace=True)
    
    # 3. For each feature, apply its derivative and lag properly
    lag_adjusted_dfs = {}
    for feat in selected_features:
        # Start with raw data and filter to base date range
        df_feat = pd.merge(base_dates, raw_dfs[feat], on="DATE", how="left")
        
        # Apply derivative if selected
        if derivatives.get(feat, False):
            df_feat[feat] = df_feat[feat].diff()
            
        # Apply shift if needed (correctly applying lag)
        shift_val = shifts.get(feat, 0)
        if shift_val != 0:
            # Note: positive shift means indicator from the past affecting current price
            # negative shift means current indicator affecting future price
            df_feat[feat] = df_feat[feat].shift(shift_val)
        
        lag_adjusted_dfs[feat] = df_feat
    
    # 4. Merge all lag-adjusted features
    lag_adjusted_df = base_dates.copy()
    for feat, df_feat in lag_adjusted_dfs.items():
        lag_adjusted_df = pd.merge(lag_adjusted_df, df_feat[["DATE", feat]], on="DATE", how="left")
    
    # 5. Drop rows with NaN values (introduced by derivative and lag operations)
    lag_adjusted_df.dropna(inplace=True)
    
    # 6. Compute correlation matrix
    if not lag_adjusted_df.empty and len(lag_adjusted_df) > 1:
        df_corr = lag_adjusted_df.drop(columns=["DATE"]).copy()
        if corr_method == "pearson":
            corr_matrix = df_corr.corr(method="pearson")
        else:
            corr_matrix = df_corr.corr(method="spearman")
        
        # Add lag information to feature names in correlation matrix
        new_index = []
        for feat in corr_matrix.index:
            lag_val = shifts.get(feat, 0)
            deriv = "Δ" if derivatives.get(feat, False) else ""
            if lag_val != 0:
                new_index.append(f"{deriv}{feat} (lag:{lag_val})")
            else:
                new_index.append(f"{deriv}{feat}")
        
        corr_matrix.index = new_index
        corr_matrix.columns = new_index
        
        # 7. Display correlation matrix
        num_features = len(corr_matrix.columns)
        fig_width = max(8, num_features * 0.8)
        fig_height = max(6, num_features * 0.8)
        fig_corr, ax_corr = plt.subplots(figsize=(fig_width, fig_height))
        fig_corr.patch.set_facecolor("black")
        ax_corr.set_facecolor("black")
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="RdBu_r",
            vmin=-1,
            vmax=1,
            square=True,
            ax=ax_corr,
            fmt=".2f",
            cbar_kws={'shrink': 0.8, 'label': 'Correlation'}
        )
        ax_corr.set_title(f"{corr_method.capitalize()} Correlation Matrix with Applied Lags", color="white")
        plt.xticks(rotation=45, ha="right", color="white")
        plt.yticks(rotation=0, color="white")
        st.pyplot(fig_corr)
        
        # 8. Option to save the correlation matrix with white background
        if st.button("Save Correlation Plot (White Background)"):
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
            ax_save.set_title(f"{corr_method.capitalize()} Correlation Matrix with Applied Lags", color="black")
            plt.xticks(rotation=45, ha="right", color="black")
            plt.yticks(rotation=0, color="black")
            
            buf = io.BytesIO()
            fig_save.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
            buf.seek(0)
            st.download_button(
                "Download Plot as PNG",
                data=buf,
                file_name=f"correlation_heatmap_with_lags_{corr_method}.png",
                mime="image/png"
            )
            plt.close(fig_save)
    else:
        st.warning("Not enough data after applying lags and derivatives to compute correlation.")

######################################
# (D) Interactive Plotly Chart (BTC Price vs. Interactive Indicator with Lags and Derivatives)
######################################
st.subheader("Interactive Plot: BTC Price vs. Indicator")
if merged_df is None or merged_df.empty:
    st.warning("No data to plot.")
elif interactive_indicator is None:
    st.info("Please select an indicator for the interactive plot.")
else:
    # Instead of using the merged_df directly, we'll prepare the data with proper lags and derivatives
    # This ensures consistency with the correlation calculations
    
    # 1. Get raw data for BTC price and the selected indicator
    btc_feat = "BTC PRICE:BTC_PRICE_USD"
    df_btc = load_feature(btc_feat, query_start_date, query_end_date)
    df_ind = load_feature(interactive_indicator, query_start_date, query_end_date)
    
    # 2. Merge on DATE
    plot_df = pd.merge(df_btc, df_ind, on="DATE", how="inner")
    
    # 3. Apply derivatives if selected
    btc_has_deriv = derivatives.get(btc_feat, False)
    ind_has_deriv = derivatives.get(interactive_indicator, False)
    
    if btc_has_deriv:
        plot_df[btc_feat] = plot_df[btc_feat].diff()
        btc_display_name = f"Δ{btc_feat}"
    else:
        btc_display_name = btc_feat
        
    if ind_has_deriv:
        plot_df[interactive_indicator] = plot_df[interactive_indicator].diff()
        ind_display_name = f"Δ{interactive_indicator}"
    else:
        ind_display_name = interactive_indicator
    
    # 4. Apply lag to indicator if specified
    ind_lag = shifts.get(interactive_indicator, 0)
    if ind_lag != 0:
        # Apply lag to the indicator
        plot_df[interactive_indicator] = plot_df[interactive_indicator].shift(ind_lag)
        ind_display_name = f"{ind_display_name} (lag:{ind_lag})"
    
    # 5. Drop NaN values introduced by derivatives or lags
    plot_df.dropna(inplace=True)
    
    # 6. Filter by plotting date range if specified
    if plot_start_date:
        plot_df = plot_df[plot_df["DATE"] >= plot_start_date]
    if plot_end_date:
        plot_df = plot_df[plot_df["DATE"] <= plot_end_date]
    
    # 7. Create the plot if we have data
    if plot_df.empty:
        st.warning("Not enough data to plot after applying lags and derivatives.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df["DATE"],
            y=plot_df[btc_feat],
            mode="lines",
            name=btc_display_name,
            line=dict(color=COLOR_PALETTE[0]),
            yaxis="y1"
        ))
        fig.add_trace(go.Scatter(
            x=plot_df["DATE"],
            y=plot_df[interactive_indicator],
            mode="lines",
            name=ind_display_name,
            line=dict(color=COLOR_PALETTE[1]),
            yaxis="y2"
        ))
        
        # Determine title with derivative and lag info
        plot_title = f"{btc_display_name} (Left Axis) vs. {ind_display_name} (Right Axis)"
        
        fig.update_layout(
            xaxis=dict(domain=[0.1, 0.9]),
            yaxis=dict(
                title=dict(text=btc_display_name, font=dict(color=COLOR_PALETTE[0])),
                tickfont=dict(color=COLOR_PALETTE[0]),
                anchor="x",
                side="left"
            ),
            yaxis2=dict(
                title=dict(text=ind_display_name, font=dict(color=COLOR_PALETTE[1])),
                tickfont=dict(color=COLOR_PALETTE[1]),
                anchor="x",
                overlaying="y",
                side="right"
            ),
            margin=dict(l=50, r=50, t=50, b=50),
            paper_bgcolor="black",
            plot_bgcolor="black",
            legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            title=plot_title
        )
        fig.update_xaxes(
            showgrid=True, gridcolor="grey", zeroline=False, linecolor="white", 
            tickfont=dict(color="white")
        )
        fig.update_yaxes(showgrid=True, gridcolor="grey")
        st.plotly_chart(fig, use_container_width=True)
        
        # 8. Optional explanation of the plot
        with st.expander("About this plot"):
            st.markdown("""
            This plot shows the relationship between BTC price and the selected indicator, with the following applied:
            
            - **Left Y-axis (blue)**: BTC Price{btc_deriv_info}
            - **Right Y-axis (orange)**: {ind_name}{ind_deriv_info}{ind_lag_info}
            
            The correlation between these series is shown in the correlation matrix above.
            """.format(
                btc_deriv_info=" (with derivative applied)" if btc_has_deriv else "",
                ind_name=interactive_indicator,
                ind_deriv_info=" (with derivative applied)" if ind_has_deriv else "",
                ind_lag_info=f" (lagged by {ind_lag} days)" if ind_lag != 0 else ""
            ))

######################################
# (E) Multi-line Chart of All Selected Features (Optional)
######################################
st.subheader("Multi-line Chart of All Selected Features")
if merged_df is not None and not merged_df.empty:
    # Let user select features to include in the multi-line chart
    all_cols = list(merged_df.columns)
    # Default: all selected features for correlation
    default_plot_feats = selected_features.copy()
    if "DATE" in default_plot_feats:
        default_plot_feats.remove("DATE")
    features_to_plot = st.multiselect("Select features to plot:", options=all_cols, default=default_plot_feats)
    if features_to_plot:
        fig_multi = go.Figure()
        color_iter = iter(st.session_state["color_palette"])
        for feat in features_to_plot:
            if feat == "DATE":
                continue
            fig_multi.add_trace(go.Scatter(
                x=merged_df["DATE"],
                y=merged_df[feat],
                mode="lines",
                name=feat,
                line=dict(color=next(color_iter, "tab:blue"))
            ))
        fig_multi.update_layout(
            title="Multi-line Plot of Selected Features",
            xaxis_title="Date",
            yaxis_title="Value",
            paper_bgcolor="black",
            plot_bgcolor="black",
            legend=dict(x=0.01, y=0.99, font=dict(color="white")),
            font=dict(color="white")
        )
        st.plotly_chart(fig_multi, use_container_width=True)
    else:
        st.info("Please select at least one feature for the multi-line chart.")
else:
    st.warning("No merged data available for plotting.")


######################################
# (F) Correlation Over Lags: Single Indicator vs. BTC Price
######################################
st.subheader("Lag-based Correlation: Single Indicator vs. BTC Price")

st.markdown(
    """
    **Lag Explanation:**  
    A **negative lag** (e.g., –1) means the indicator’s value from yesterday is compared with today’s BTC Price (the indicator leads the price).  
    A **positive lag** would compare a future indicator with today’s BTC Price (the indicator lags behind).
    """
)

with st.expander("Lag-Correlation Settings", expanded=True):
    # 1. Pick the single indicator (from TABLE_DICT)
    tables_for_lag = list(TABLE_DICT.keys())
    chosen_table_lag = st.selectbox("Select Table for the Indicator:", tables_for_lag, index=0)
    
    # 2. Pick the numeric column from that table
    numeric_cols_lag = TABLE_DICT[chosen_table_lag]["numeric_cols"]
    chosen_col_lag = st.selectbox("Select Column (Indicator) from Table:", numeric_cols_lag, index=0)
    chosen_indicator_lag = f"{chosen_table_lag}:{chosen_col_lag}"
    
    # 3. Derivative flags
    btc_deriv_lag = st.checkbox("Derivative of BTC Price?", value=False)
    indicator_deriv_lag = st.checkbox("Derivative of this Indicator?", value=False)
    
    # 4. Range of lags
    st.write("Choose the range of lag days (negative to positive).")
    default_min_lag = -30
    default_max_lag = 30
    min_lag = st.number_input("Minimum Lag (can be negative)", value=default_min_lag, step=1)
    max_lag = st.number_input("Maximum Lag", value=default_max_lag, step=1)

# Automatically compute lag correlation without a button press.
btc_feat_name = "BTC PRICE:BTC_PRICE_USD"
df_btc = load_feature(btc_feat_name, query_start_date, query_end_date)
df_btc.sort_values("DATE", inplace=True)
df_btc.dropna(subset=[btc_feat_name], inplace=True)

df_ind = load_feature(chosen_indicator_lag, query_start_date, query_end_date)
df_ind.sort_values("DATE", inplace=True)
df_ind.dropna(subset=[chosen_indicator_lag], inplace=True)

df_merge_lag = pd.merge(df_btc, df_ind, on="DATE", how="inner").dropna()

if btc_deriv_lag:
    df_merge_lag[btc_feat_name] = df_merge_lag[btc_feat_name].diff()
if indicator_deriv_lag:
    df_merge_lag[chosen_indicator_lag] = df_merge_lag[chosen_indicator_lag].diff()
df_merge_lag.dropna(inplace=True)

if df_merge_lag.empty:
    st.warning("Not enough data to compute lag correlation.")
else:
    lag_values = list(range(int(min_lag), int(max_lag) + 1))
    correlations = []
    
    for lag in lag_values:
        df_temp = df_merge_lag.copy()
        if lag != 0:
            # If lag is positive, shifting the indicator downwards (using its past value)
            # If lag is negative, this automatically shifts upwards (using a future value)
            df_temp[chosen_indicator_lag] = df_temp[chosen_indicator_lag].shift(lag)
        
        df_temp.dropna(inplace=True)
        
        if len(df_temp) > 1:
            if corr_method == "pearson":
                corr_val = df_temp[[btc_feat_name, chosen_indicator_lag]].corr(method="pearson").iloc[0,1]
            else:
                corr_val = df_temp[[btc_feat_name, chosen_indicator_lag]].corr(method="spearman").iloc[0,1]
        else:
            corr_val = np.nan
        
        correlations.append(corr_val)
    
    df_lag_corr = pd.DataFrame({
        "Lag": lag_values,
        "Correlation": correlations
    })
    
    fig_lag = go.Figure()
    fig_lag.add_trace(go.Scatter(
        x=df_lag_corr["Lag"],
        y=df_lag_corr["Correlation"],
        mode="lines+markers",
        name="Correlation"
    ))
    fig_lag.update_layout(
        title=f"Lag-Correlation: BTC_PRICE vs. {chosen_indicator_lag}",
        xaxis_title="Lag (days)",
        yaxis_title=f"{corr_method.capitalize()} Correlation",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        hovermode="x unified"
    )
    fig_lag.update_xaxes(showgrid=True, gridcolor="grey", linecolor="white")
    fig_lag.update_yaxes(showgrid=True, gridcolor="grey", zeroline=True, zerolinecolor="grey")
    
    st.plotly_chart(fig_lag, use_container_width=True)
    
    max_corr_idx = np.nanargmax(np.abs(df_lag_corr["Correlation"]))
    best_lag = df_lag_corr["Lag"][max_corr_idx]
    best_corr = df_lag_corr["Correlation"][max_corr_idx]
    st.write(f"**Highest absolute correlation** occurs at lag = {best_lag} days, correlation = {best_corr:.3f}.")
