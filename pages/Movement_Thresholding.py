import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import random
import ruptures as rpt
from scipy.stats import norm, shapiro

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

######################################
# 4) Query and Statistical Analysis
######################################

# -- Sidebar for parameters
st.sidebar.subheader("Statistical Analysis Parameters")
std_slider = st.sidebar.slider(
    "Std Dev Threshold for Significant Movement", 
    min_value=0.5, 
    max_value=3.0, 
    value=1.0, 
    step=0.1
)

# Date picker for the histogram start date
hist_start_date = st.sidebar.date_input(
    "Histogram Start Date", 
    value=datetime.date(2010, 7, 30)
)
hist_start_date_str = hist_start_date.strftime("%Y-%m-%d")

# Slider for the number of bins in the histogram
nbins_slider = st.sidebar.slider(
    "Number of Bins for Histogram", 
    min_value=10, 
    max_value=200, 
    value=100, 
    step=10
)

# 4.1) Load the BTC price movement percentage from Snowflake
query_movement = f"""
SELECT
    DATE,
    AVG_PRICE,
    PREV_AVG,
    (AVG_PRICE - PREV_AVG)/NULLIF(PREV_AVG, 0) * 100 AS PRICE_MOVEMENT_PERCENT
FROM BTC_PRICE_MOVEMENT_PERCENTAGE
WHERE PREV_AVG IS NOT NULL AND DATE > '{hist_start_date_str}'
"""
df_movement = session.sql(query_movement).to_pandas()

movement_data = df_movement["PRICE_MOVEMENT_PERCENT"].dropna()

# 4.2) Check normality (Shapiro-Wilk Test) on the ENTIRE dataset
stat, p_value = shapiro(movement_data)

# 4.3) Mean and std on the entire dataset
mean_val = movement_data.mean()
std_val = movement_data.std()

# Classify moves as 'slight' or 'significant' based on how many std dev from mean
df_movement["Movement_Category"] = df_movement["PRICE_MOVEMENT_PERCENT"].apply(
    lambda x: "Significant Increase" if (x - mean_val) > std_slider * std_val else
              ("Significant Decrease" if (x - mean_val) < -std_slider * std_val else
               ("Slight Increase" if x > 0 else "Slight Decrease"))
)

######################################
# 4.4) Display normality test results
######################################
st.subheader("BTC Price Movement Percentage - Normality Check (Full Data)")
st.write(f"Shapiro-Wilk Test Statistic = {stat:.4f}, p-value = {p_value:.4f}")

if p_value < 0.05:
    st.write("**Conclusion**: The distribution is likely *not* normal (p < 0.05).")
else:
    st.write("**Conclusion**: The distribution *is* likely normal (p >= 0.05).")

st.write(f"Mean Movement (full data): {mean_val:.2f}%")
st.write(f"Std Dev of Movement (full data): {std_val:.2f}%")
st.write(f"Threshold for 'Significant' set at ±{std_slider} standard deviations.")

######################################
# 4.5) Plot histogram (full data)
######################################
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=movement_data, nbinsx=nbins_slider))
fig_hist.update_layout(
    title="Distribution of BTC Movement (%) - Full Data",
    xaxis_title="BTC Movement (%)",
    yaxis_title="Count",
    template="plotly_dark"
)
st.plotly_chart(fig_hist, use_container_width=True)

######################################
# 4.6) Subset Range + Normality Check
######################################
st.subheader("Subset Range Analysis")

st.write("Select a movement percentage range (in %). We'll slice the data to that range, run a normality test, and if it's normal, define a threshold for up/down/unchanged.")

range_min, range_max = st.slider(
    "Select Movement Range (%)",
    min_value=float(movement_data.min()),
    max_value=float(movement_data.max()),
    value=(float(movement_data.min()), float(movement_data.max())),
    step=0.5
)

# Subset
subset_data = movement_data[(movement_data >= range_min) & (movement_data <= range_max)]
st.write(f"Data points in selected range: {len(subset_data)}")

if len(subset_data) > 1:
    # Normality test on subset
    stat_sub, p_sub = shapiro(subset_data)
    mean_sub = subset_data.mean()
    std_sub = subset_data.std()

    st.write(f"**Subset Shapiro-Wilk**: statistic={stat_sub:.4f}, p={p_sub:.4f}")
    st.write(f"Subset mean={mean_sub:.2f}% , std={std_sub:.2f}%")

    if p_sub < 0.05:
        st.write("**Subset Conclusion**: likely *not* normal (p < 0.05).")
    else:
        st.write("**Subset Conclusion**: likely normal (p >= 0.05).")

        # If normal, let's define a threshold
        st.write("**Defining Up/Down/Unchanged** around mean ± 1×std (example).")
        up_threshold = mean_sub + std_sub
        down_threshold = mean_sub - std_sub
        st.write(f"Up if movement >= {up_threshold:.2f}%")
        st.write(f"Down if movement <= {down_threshold:.2f}%")
        st.write("Unchanged otherwise")

        # Show a mini table with these boundaries
        st.write("**Boundaries**:")
        st.table({
            "Type": ["Down", "Unchanged", "Up"],
            "Condition": [
                f"movement ≤ {down_threshold:.2f}%",
                f"{down_threshold:.2f}% < movement < {up_threshold:.2f}%",
                f"movement ≥ {up_threshold:.2f}%"
            ]
        })
else:
    st.write("Not enough data points in this range to do a normality test.")

######################################
# 4.7) Display table of movements with categories (FULL data)
######################################
st.subheader("BTC Price Movements With Classification (Full Data)")
st.dataframe(df_movement[["DATE", "AVG_PRICE", "PREV_AVG", "PRICE_MOVEMENT_PERCENT", "Movement_Category"]])

######################################
# 5) (Optional) Load and Display Absolute BTC Price
######################################
st.subheader("Optional: BTC Price (USD) Over Time")
query_price = """
SELECT
    TIMESTAMP,
    BTC_PRICE_USD
FROM BTC_PRICE_USD
ORDER BY TIMESTAMP
"""
df_price = session.sql(query_price).to_pandas()

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=df_price["TIMESTAMP"], 
    y=df_price["BTC_PRICE_USD"], 
    mode='lines',
    name="BTC Price (USD)"
))

fig_price.update_layout(
    title="Historical BTC Price in USD",
    xaxis_title="Timestamp",
    yaxis_title="Price (USD)",
    template="plotly_dark"
)
st.plotly_chart(fig_price, use_container_width=True)
