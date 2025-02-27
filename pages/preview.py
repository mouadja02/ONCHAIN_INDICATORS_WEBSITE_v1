import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px

# Streamlit UI setup
st.set_page_config(page_title="Bitcoin HODL Waves", layout="wide")
st.title("Bitcoin HODL Waves Visualization")

# Snowflake Connection
conn = snowflake.connector.connect(
    user=st.secrets["SNOWFLAKE_USER"],
    password=st.secrets["SNOWFLAKE_PASSWORD"],
    account=st.secrets["SNOWFLAKE_ACCOUNT"],
    warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
    database=st.secrets["SNOWFLAKE_DATABASE"],
    schema=st.secrets["SNOWFLAKE_SCHEMA"]
)

# Query Data
query = """
    SELECT SNAPSHOT_DATE, AGE_BUCKET, PERCENT_SUPPLY
    FROM HODL_Waves
    ORDER BY SNAPSHOT_DATE, AGE_BUCKET
"""
df = pd.read_sql(query, conn)

# Close connection
conn.close()

# Convert date column to datetime
df["SNAPSHOT_DATE"] = pd.to_datetime(df["SNAPSHOT_DATE"])

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
    x="SNAPSHOT_DATE",
    y="PERCENT_SUPPLY",
    color="AGE_BUCKET",
    title="Bitcoin HODL Waves Over Time",
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
st.subheader("HODL Waves Data")
st.dataframe(df_filtered)
