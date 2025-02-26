# Bitcoin On-chain Analytics Dashboard

This project is a collection of interactive Streamlit applications designed for on-chain analysis of Bitcoin data. It connects to a Snowflake data warehouse (populated via Azure Data Factory, for example) and provides detailed visualizations of on-chain metrics and address balance bands. The project helps analysts and investors understand blockchain trends, network activity, and market behavior.

## Overview

The project consists of several standalone Streamlit apps:

### 1. On-chain Indicators Dashboard
This app allows users to:
- Select an on-chain metric set (one table) and visualize its indicators using an interactive Plotly chart.
- Overlay BTC price (queried from a separate table).
- Apply exponential moving averages (EMA) to smooth trends.
- Enable change point detection (CPD) using the `ruptures` package to highlight significant BTC price shifts.

### 2. Address Size Metric
This app focuses on visualizing the distribution of Bitcoin address balances over time:
- Displays daily address counts per balance band.
- Optionally applies EMA overlay for trend analysis.

### 3. Block Explorer
- Allows users to search for transactions or blocks.
- Displays transaction details and parses JSON columns for inputs and outputs.

## Features

### Interactive Visualization
- Uses Plotly to create zoomable, customizable charts (line or bar charts).
- Intuitive sidebar controls for chart customization.

### On-chain Metrics
- Queries and displays key on-chain metrics from Snowflake (e.g., Active Addresses, NUPL, Puell Multiple).

### BTC Price Overlay & Change Point Detection
- Optionally overlays BTC price with a secondary Y-axis.
- Detects major price shifts using the `ruptures` library.

### Address Balance Bands
- Visualizes the daily distribution of Bitcoin addresses based on balance bands.
- Includes optional EMA smoothing for trend analysis.

### Customizable Controls
- Users can adjust date ranges, axis scales (linear/log), chart types, EMA settings, and CPD penalty values.

## Technologies Used
- **Streamlit** – For building interactive web apps.
- **Pandas** – For data manipulation and analysis.
- **Plotly** – For interactive visualizations.
- **Snowflake** – As a data warehouse for blockchain data.
- **Ruptures** – For time series change point detection.
- **Python Standard Libraries** – Including `datetime` and `random`.


### UI/UX Enhancements
- Styled with a dark theme (similar to Glassnode or BitcoinMagazinePro).
- Future improvements could include more advanced sidebar filtering and grouping.

### Additional Metrics & Views
- Expand with more on-chain metrics and detailed block/transaction views.

### Data Refresh & Caching
- Implement caching strategies for faster data retrieval and real-time updates.

