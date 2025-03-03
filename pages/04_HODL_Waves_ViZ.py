import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit UI setup
st.set_page_config(page_title="Bitcoin HODL Waves", layout="wide")
st.title("Bitcoin HODL Waves Visualization")

cx = st.connection("snowflake")
session = cx.session()

# Query Data
query = """
    SELECT DATE, AGE_BUCKET, PERCENT_SUPPLY
    FROM HODL_Waves
    ORDER BY DATE ASC
"""
df = session.sql(query).to_pandas()

# Convert date column to datetime
df["DATE"] = pd.to_datetime(df["DATE"])

# Filter out future dates
today = pd.to_datetime("today").normalize()  # Get today's date without time
df = df[df["DATE"] < today]

# Sidebar Filters
st.sidebar.header("Filter Data")
selected_age_buckets = st.sidebar.multiselect(
    "Select Age Buckets to Display", 
    options=df["AGE_BUCKET"].unique(),
    default=df["AGE_BUCKET"].unique()
)
df_filtered = df[df["AGE_BUCKET"].isin(selected_age_buckets)]

# Plotting with Plotly
fig = px.area(
    df_filtered,
    x="DATE",
    y="PERCENT_SUPPLY",
    color="AGE_BUCKET",
    title="Bitcoin HODL Waves Over Time (Before Today)",
    labels={"SNAPSHOT_DATE": "Date", "PERCENT_SUPPLY": "Supply Percentage (%)"},
    color_discrete_sequence=px.colors.qualitative.Set1
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Percentage of Supply",
    legend_title="Age Bucket",
    template="plotly_dark"
)

# Display plot
st.plotly_chart(fig, use_container_width=True)

# Display Data Table
#st.subheader("HODL Waves Data")
#st.dataframe(df_filtered)
