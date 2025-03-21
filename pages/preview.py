import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import random
import io
import math

######################################
# 1) Page Configuration & Dark Theme
######################################
st.set_page_config(
    page_title="Bitcoin Price Movement Dashboard",
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

# We'll store in session_state a dictionary for "plot_lines", 
# where each key=feature_name, value=DataFrame with "DATE" + the final transformed column.
if "plot_lines" not in st.session_state:
    st.session_state["plot_lines"] = {}  # { feature_name : pd.DataFrame(...), ... }


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
st.title("Correlation Matrix + On‐demand Plot of Lagged/Derived Features")

######################################
# (A) Correlation Settings in Sidebar
######################################
with st.sidebar:
    st.header("Correlation Settings")

    default_corr_start = datetime.date(2015, 1, 1)
    start_date_corr = st.date_input("Start Date (corr)", value=default_corr_start)

    activate_end_date_corr = st.checkbox("Activate End Date (corr)", value=False)
    if activate_end_date_corr:
        default_corr_end = datetime.date.today()
        end_date_corr = st.date_input("End Date (corr)", value=default_corr_end)
    else:
        end_date_corr = None

    # Correlation method
    corr_method = st.selectbox(
        "Select Correlation Method:",
        ["pearson", "spearman"],
        index=0
    )

    st.markdown("---")

    st.subheader("1. Choose Indicators")
    all_tables = list(TABLE_DICT.keys())
    default_selected = ["BTC PRICE"] 
    selected_tables = st.multiselect(
        "Select tables to include:",
        all_tables,
        default=default_selected,
    )

    # Build the full list of available features
    available_features = []
    for tbl in selected_tables:
        for col in TABLE_DICT[tbl]["numeric_cols"]:
            feat_name = f"{tbl}:{col}"
            available_features.append(feat_name)

    if "BTC PRICE:BTC_PRICE_USD" not in available_features:
        available_features.append("BTC PRICE:BTC_PRICE_USD")

    selected_features = st.multiselect(
        "Select Features for Correlation:",
        available_features,
        default=available_features
    )

    st.markdown("---")

    st.subheader("2. Lag & Derivative per Feature, plus Plot Button")

    # We'll create placeholders to store user-chosen shift and derivative for each feature
    shifts = {}
    derivatives = {}

    # We create a function so we can apply transformations and store them in session state
    def plot_button_callback(feature):
        """
        Called when user clicks the 'Plot' button next to a feature. 
        We'll retrieve the final data for that single feature (with chosen shift/derivative),
        then store it in session_state['plot_lines'] for later multi-line plotting.
        """
        # 1) Query data
        tbl, col = feature.split(":", 1)
        tbl_info = TABLE_DICT[tbl]
        date_col = tbl_info["date_col"]

        query_start = start_date_corr
        query_end = end_date_corr

        query = f"""
            SELECT
                CAST({date_col} AS DATE) AS DATE,
                {col}
            FROM {tbl_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{query_start}'
        """
        if query_end:
            query += f" AND CAST({date_col} AS DATE) <= '{query_end}'"
        query += " ORDER BY DATE"

        df_temp = session.sql(query).to_pandas()
        df_temp.rename(columns={col: feature}, inplace=True)

        df_temp.sort_values("DATE", inplace=True)
        df_temp.dropna(subset=[feature], how="any", inplace=True)

        # 2) Apply derivative if asked
        if derivatives[feature]:
            df_temp[feature] = df_temp[feature].diff()
            df_temp.dropna(subset=[feature], how="any", inplace=True)

        # 3) Apply shift
        shift_val = shifts[feature]
        if shift_val > 0:
            df_temp[feature] = df_temp[feature].shift(shift_val)
            df_temp.dropna(subset=[feature], how="any", inplace=True)

        # Now we store the result in session_state so we can plot them all together
        df_temp.reset_index(drop=True, inplace=True)

        # Save to session state
        st.session_state["plot_lines"][feature] = df_temp[["DATE", feature]]

        st.success(f"Plotted {feature} with shift={shift_val}, deriv={derivatives[feature]}")

    # Now for each selected feature, we show a row with a slider, checkbox, and a plot button
    for feat in selected_features:
        # SHIFT
        if feat == "BTC PRICE:BTC_PRICE_USD":
            # Force shift=0, but derivative optional
            st.write(f"**{feat}** (no shift, derivative optional)")
            derivatives[feat] = st.checkbox(f"Take derivative of {feat}?", key=f"deriv_{feat}", value=False)
            shifts[feat] = 0
            # Plot button
            if st.button(f"Plot {feat}", key=f"plotbtn_{feat}"):
                plot_button_callback(feat)
            st.markdown("---")
        else:
            st.write(f"**{feat}**")
            shift_val = st.slider(f"Lag (days) for {feat}", 0, 30, 0, key=f"shift_{feat}")
            shifts[feat] = shift_val
            derivatives[feat] = st.checkbox(f"Take derivative of {feat}?", key=f"deriv_{feat}", value=False)
            if st.button(f"Plot {feat}", key=f"plotbtn_{feat}"):
                plot_button_callback(feat)
            st.markdown("---")

######################################
# (B) Build Correlation Matrix from all final transforms
######################################

# We can do correlation only on the final set of features that the user plotted,
# each stored in st.session_state["plot_lines"]. We merge them by DATE.
# But if you prefer correlation on all selected features at once, ignoring the separate plot lines,
# see the original approach. We'll do it on all features at once in the final approach.

st.header("Final Merged Data & Correlation")

if len(st.session_state["plot_lines"]) < 2:
    st.info("Please plot at least 2 features to compute correlation.")
    st.stop()
    
# Merge all plotted lines on DATE
df_merged_final = None
for feat, df_feat in st.session_state["plot_lines"].items():
    if df_merged_final is None:
        df_merged_final = df_feat.copy()
    else:
        df_merged_final = pd.merge(df_merged_final, df_feat, on="DATE", how="outer")

if df_merged_final is None or df_merged_final.empty:
    st.warning("No data to display.")
    st.stop()

df_merged_final.sort_values("DATE", inplace=True)
df_merged_final.dropna(how="any", inplace=True)  # optional

if len(df_merged_final.columns) < 2:
    st.warning("Not enough columns to compute correlation. Need at least 2 features plotted.")
    st.stop()

st.write("## Data After Plot Selections")
st.dataframe(df_merged_final)

corr_method = st.selectbox("Correlation Method for Final Plotted Data:", ["pearson", "spearman"], index=0)
df_for_corr = df_merged_final.drop(columns=["DATE"]).copy()

if len(df_for_corr.columns) >= 2:
    if corr_method == "pearson":
        corr_matrix = df_for_corr.corr(method="pearson")
    else:
        corr_matrix = df_for_corr.corr(method="spearman")

    num_features = len(corr_matrix.columns)
    fig_width = max(8, num_features * 0.8)
    fig_height = max(6, num_features * 0.8)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Dark theme for the heatmap
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
    ax.set_title(f"{corr_method.capitalize()} Correlation on Plotted Features", color="white")
    plt.xticks(rotation=45, ha="right", color="white")
    plt.yticks(rotation=0, color="white")

    st.pyplot(fig)

    if st.button("Save This Correlation Plot (White BG)"):
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
        ax_save.set_title(f"{corr_method.capitalize()} Correlation on Plotted Features", color="black")
        plt.xticks(rotation=45, ha="right", color="black")
        plt.yticks(rotation=0, color="black")

        buf = io.BytesIO()
        fig_save.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        buf.seek(0)
        st.download_button(
            "Download Plot as PNG",
            data=buf,
            file_name=f"plotted_correlation_{corr_method}.png",
            mime="image/png"
        )
        plt.close(fig_save)

######################################
# (C) Multi-line Chart with All Plotted Features
######################################
st.header("Multi-line Chart of All Plotted Features")

if st.session_state["plot_lines"]:
    df_plot_all = None
    for feat, df_feat in st.session_state["plot_lines"].items():
        if df_plot_all is None:
            df_plot_all = df_feat.copy()
        else:
            df_plot_all = pd.merge(df_plot_all, df_feat, on="DATE", how="outer")
    if df_plot_all is not None and not df_plot_all.empty:
        df_plot_all.sort_values("DATE", inplace=True)
        df_plot_all.dropna(how="any", inplace=True)

        if len(df_plot_all.columns) > 1:
            fig_all, ax_all = plt.subplots(figsize=(10,6))
            fig_all.patch.set_facecolor("white")
            ax_all.set_facecolor("white")

            color_iter = iter(st.session_state["color_palette"])

            for col in df_plot_all.columns:
                if col == "DATE":
                    continue
                c = next(color_iter, "tab:blue")
                ax_all.plot(df_plot_all["DATE"], df_plot_all[col], label=col, color=c)

            ax_all.set_xlabel("Date")
            ax_all.set_ylabel("Value")
            ax_all.set_title("All Plotted Features (Lag/Deriv) on Single Chart")
            ax_all.grid(True)
            ax_all.legend()
            st.pyplot(fig_all)
        else:
            st.warning("Not enough columns to plot.")
    else:
        st.warning("df_plot_all is empty or None.")
else:
    st.info("No features have been plotted yet. Click 'Plot' beside each feature to add them.")
