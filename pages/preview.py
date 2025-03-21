import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import random
import calendar
import io
import math

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

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

######################################
# 5) Page Title
######################################
st.title("Correlation Matrix of On-chain Features (Option to Use Derivatives)")

######################################
# (A) Table Configurations
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
        "numeric_cols": ["NUPL", "NUPL_PERCENT"]
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
            "M2_GROWTH_YOY", "M2_GLOBAL_SUPPLY"
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
# (B) Sidebar Controls for Correlation Settings
######################################
with st.sidebar:
    st.header("Correlation Settings")

    # 1) Date range selection for correlation data
    default_corr_start = datetime.date(2015, 1, 1)
    start_date_corr = st.date_input("Start Date (corr)", value=default_corr_start, key="corr_start_date")

    activate_end_date_corr = st.checkbox("Activate End Date (corr)", value=False, key="corr_activate_end")
    if activate_end_date_corr:
        default_corr_end = datetime.date.today()
        end_date_corr = st.date_input("End Date (corr)", value=default_corr_end, key="corr_end_date")
    else:
        end_date_corr = None

    # 2) Correlation method
    corr_method = st.selectbox(
        "Select Correlation Method:",
        ["pearson", "spearman"],
        index=0,
        help="Spearman (rank-based) may detect monotonic relationships better."
    )

    st.markdown("---")

    st.subheader("1. Choose Indicators")
    all_tables = list(TABLE_DICT.keys())
    default_selected = ["BTC PRICE"] 

    selected_tables = st.multiselect(
        "Select tables to include:",
        all_tables,
        default=default_selected,
        help="Choose which on-chain data tables you want to analyze."
    )

    available_features = []
    for tbl in selected_tables:
        tbl_info = TABLE_DICT[tbl]
        for col in tbl_info["numeric_cols"]:
            available_features.append(f"{tbl}:{col}")

    # Always ensure BTC PRICE is included
    if "BTC PRICE:BTC_PRICE_USD" not in available_features:
        available_features.append("BTC PRICE:BTC_PRICE_USD")

    selected_features = st.multiselect(
        "Select Features for Correlation:",
        available_features,
        default=available_features, 
        key="selected_features"
    )

    st.markdown("---")
    st.subheader("2. Lag & Derivative Per Feature")

    # A dictionary to store shift (lag) and derivative settings
    shifts = {}
    derivatives = {}

    # For the BTC PRICE specifically, we have a separate checkbox for derivative
    st.write("**BTC PRICE:BTC_PRICE_USD** - top-level derivative checkbox, no shift allowed.")
    derive_btc_price = st.checkbox("Take derivative of BTC PRICE?", value=False)
    # Force shift=0 for BTC Price
    shifts["BTC PRICE:BTC_PRICE_USD"] = 0
    derivatives["BTC PRICE:BTC_PRICE_USD"] = derive_btc_price
    st.markdown("---")

    # For all other features, we show a slider (lag) and a checkbox for derivative
    for feat in selected_features:
        if feat == "BTC PRICE:BTC_PRICE_USD":
            continue  # already handled above

        st.write(f"**{feat}**")
        # Shift slider
        shift_val = st.slider(f"Lag (days) for {feat}", 0, 30, 0)
        shifts[feat] = shift_val

        # Derivative checkbox
        derive_flag = st.checkbox(f"Take derivative of {feat}?", value=False)
        derivatives[feat] = derive_flag

        st.markdown("---")


######################################
# (C) Data Query & Merge for Correlation
######################################
df_list = []
for tbl_feat in selected_features:
    tbl, col = tbl_feat.split(":", 1)
    tbl_info = TABLE_DICT[tbl]

    date_col = tbl_info["date_col"]
    query = f"""
        SELECT
            CAST({date_col} AS DATE) AS DATE,
            {col}
        FROM {tbl_info['table_name']}
        WHERE CAST({date_col} AS DATE) >= '{start_date_corr}'
    """
    if end_date_corr:
        query += f" AND CAST({date_col} AS DATE) <= '{end_date_corr}'"
    query += " ORDER BY DATE"

    df_temp = session.sql(query).to_pandas()

    # Rename the data column to the combined feature name (e.g. "BTC PRICE:BTC_PRICE_USD")
    df_temp.rename(columns={col: tbl_feat}, inplace=True)
    df_list.append(df_temp)

# Merge all data frames on DATE
if not df_list:
    st.error("No data returned for the selected features.")
    st.stop()

merged_df = df_list[0]
for df_other in df_list[1:]:
    merged_df = pd.merge(merged_df, df_other, on="DATE", how="outer")

# Sort by date
merged_df.sort_values("DATE", inplace=True)
merged_df = merged_df.dropna(how="all")

# 1) Apply derivatives if requested
for feat, do_deriv in derivatives.items():
    if do_deriv and feat in merged_df.columns:
        merged_df[feat] = merged_df[feat].diff()

# drop first row of each derived column that is now NaN
all_derived_feats = [f for f, val in derivatives.items() if val]  # only those that are derived
if all_derived_feats:
    merged_df.dropna(subset=all_derived_feats, how="any", inplace=True)

# 2) Apply the user-defined shifts
for feat, shift_val in shifts.items():
    if feat in merged_df.columns and shift_val > 0:
        merged_df[feat] = merged_df[feat].shift(shift_val)

# After shifting, remove rows at top that are now NaN
merged_df.dropna(how="any", inplace=True)

######################################
# (D) Compute Correlation
######################################
st.subheader(f"{corr_method.capitalize()} Correlation Matrix (Lagged/Derived Indicators)")

df_for_corr = merged_df.drop(columns=["DATE"]).copy()

if len(df_for_corr.columns) < 2:
    st.warning("Not enough columns to compute correlation. Please select at least 2 features.")
    st.stop()

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
ax.set_title(f"{corr_method.capitalize()} Correlation Matrix of On-chain Features", color="white")
plt.xticks(rotation=45, ha="right", color="white")
plt.yticks(rotation=0, color="white")

st.pyplot(fig)

######################################
# (E) Option to Save Plot on White Background
######################################
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
    ax_save.set_title(f"{corr_method.capitalize()} Correlation Matrix (Non-negative Lags)", color="black")
    plt.xticks(rotation=45, ha="right", color="black")
    plt.yticks(rotation=0, color="black")

    buf = io.BytesIO()
    fig_save.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    st.download_button(
        "Download Plot as PNG",
        data=buf,
        file_name=f"correlation_heatmap_{corr_method}.png",
        mime="image/png"
    )
    plt.close(fig_save)

######################################
# (F) FEATURE SELECTION
######################################
st.subheader("Feature Selection for BTC Price Prediction")

target_col = "BTC PRICE:BTC_PRICE_USD"

max_feats = len(df_for_corr.columns) - 1 if target_col in df_for_corr.columns else len(df_for_corr.columns)
if max_feats < 1:
    st.warning("Cannot do feature selection because there's no target or not enough columns.")
    st.stop()

num_features_to_select = st.slider(
    "Number of top features to select",
    min_value=1,
    max_value=max_feats if max_feats >= 1 else 1,
    value=min(5, max_feats)
)

selection_method = st.selectbox(
    "Select Feature-Selection Method:",
    ["Correlation-based", "RandomForest-based"]
)

st.markdown("""
In **Correlation-based** selection, we pick the top features by absolute correlation to BTC Price (or its derivative, if chosen).
In **RandomForest-based** selection, we train a light Random Forest to predict BTC Price from all
other features, and rank features by their importance scores.
""")

if st.button("Run Feature Selection"):
    df_no_date = merged_df.drop(columns=["DATE"]).copy()
    if target_col not in df_no_date.columns:
        st.warning(f"Target column '{target_col}' not found in data. Cannot select features.")
    else:
        if selection_method == "Correlation-based":
            corrs_to_target = df_no_date.corr(method=corr_method)[target_col].drop(labels=[target_col])
            ranked = corrs_to_target.abs().sort_values(ascending=False)
            best_feats = ranked.head(num_features_to_select).index.tolist()

            st.write(f"**Top {num_features_to_select} features by absolute correlation:**")
            for feat in best_feats:
                st.write(f"{feat}: correlation = {corrs_to_target[feat]:.4f}")
        
        else:
            # 2) Model-based (Random Forest)
            X = df_no_date.drop(columns=[target_col])
            y = df_no_date[target_col]
            if len(X) < 10:
                st.warning("Not enough data rows to run Random Forest-based feature selection.")
            else:
                from sklearn.ensemble import RandomForestRegressor
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import mean_squared_error

                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
                rf_model = RandomForestRegressor(
                    n_estimators=2000,
                    max_depth=6,
                    min_samples_leaf=5,
                    random_state=42
                )
                rf_model.fit(X_train, y_train)
                importances = rf_model.feature_importances_
                feature_names = X.columns.tolist()
                feat_imp_pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
                best_feats = [f[0] for f in feat_imp_pairs[:num_features_to_select]]

                st.write(f"**Top {num_features_to_select} features by RandomForest importance:**")
                for (feat, imp) in feat_imp_pairs[:num_features_to_select]:
                    st.write(f"{feat}: importance = {imp:.4f}")

                # Evaluate quickly
                y_pred = rf_model.predict(X_test)
                mse = mean_squared_error(y_test, y_pred)
                rmse = math.sqrt(mse)
                st.write(f"Random Forest test RMSE: {rmse:.2f}")

        st.write("---")
        st.write("**Selected features:**", best_feats)
        st.info("You can feed these features into your DQN or other ML pipeline!")
