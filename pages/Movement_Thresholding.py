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

# New slider for No-Change threshold
no_change_threshold = st.sidebar.slider(
    "No-Change Threshold (%)",
    min_value=0.0,
    max_value=2.0,
    value=0.5,
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

# Existing classification based on standard deviations
df_movement["Movement_Category"] = df_movement["PRICE_MOVEMENT_PERCENT"].apply(
    lambda x: "Significant Increase" if (x - mean_val) > std_slider * std_val else
              ("Significant Decrease" if (x - mean_val) < -std_slider * std_val else
               ("Slight Increase" if x > 0 else "Slight Decrease"))
)

# New classification for Increase/Decrease/No-Change
df_movement["Price_Status"] = df_movement["PRICE_MOVEMENT_PERCENT"].apply(
    lambda x: "Increase" if x > no_change_threshold else
              ("Decrease" if x < -no_change_threshold else "No-Change")
)

######################################
# 4.4) Display normality test results and category stats
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
st.write(f"No-Change Threshold set at ±{no_change_threshold}%.")

# Display percentage of days in each Price_Status category
category_counts = df_movement["Price_Status"].value_counts(normalize=True) * 100
st.write("### Price Status Distribution")
st.write(f"Percentage of days with Increase: {category_counts.get('Increase', 0):.2f}%")
st.write(f"Percentage of days with Decrease: {category_counts.get('Decrease', 0):.2f}%")
st.write(f"Percentage of days with No-Change: {category_counts.get('No-Change', 0):.2f}%")

######################################
# 4.5) Plot histogram (full data) with thresholds
######################################
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=movement_data, nbinsx=nbins_slider))
fig_hist.add_vline(x=-no_change_threshold, line_dash="dash", line_color="red", annotation_text="Decrease Threshold")
fig_hist.add_vline(x=no_change_threshold, line_dash="dash", line_color="red", annotation_text="Increase Threshold")
fig_hist.update_layout(
    title="Distribution of BTC Movement (%) - Full Data",
    xaxis_title="BTC Movement (%)",
    yaxis_title="Count",
    template="plotly_dark"
)
st.plotly_chart(fig_hist, use_container_width=True)
