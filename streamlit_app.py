import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

###############################################################################
#                           SNOWFLAKE CONNECTION
###############################################################################
# Adjust to your environment as needed
cx = st.connection("snowflake")
session = cx.session()

###############################################################################
#                        PAGE 1: DASHBOARD FUNCTION
###############################################################################
def show_dashboard_page():
    """
    This function contains your entire existing On-chain Indicators Dashboard code.
    Everything that was in your script originally goes here,
    minus the multi-page logic (we'll call this function from main()).
    """

    # 1) Page Config
    # ------------------------------------------------
    st.set_page_config(
        page_title="Bitcoin On-chain Indicators Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 2) Dark Theme Styling (full black background)
    # ------------------------------------------------
    st.markdown(
        """
        <style>
        body {
            background-color: #000000;
            color: #f0f2f6;
        }
        .css-18e3th9, .css-1dp5vir, .css-12oz5g7, .st-bq {
            background-color: #000000 !important;
        }
        .css-15zrgzn, .css-1hynb2t, .css-1xh633b, .css-17eq0hr {
            color: #f0f2f6;
        }
        .css-1xh633b a {
            color: #1FA2FF;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 3) Table Configurations
    # ------------------------------------------------
    TABLE_DICT = {
        "ACTIVE_ADDRESSES": {
            "table_name": "BTC_DATA.DATA.ACTIVE_ADDRESSES",
            "date_col": "DATE",
            "numeric_cols": ["ACTIVE_ADDRESSES"]
        },
        "BTC_REALIZED_CAP_AND_PRICE": {
            "table_name": "BTC_DATA.DATA.BTC_REALIZED_CAP_AND_PRICE",
            "date_col": "DATE",
            "numeric_cols": [
                "REALIZED_CAP_USD",
                "REALIZED_PRICE_USD"
            ]
        },
        "CDD": {
            "table_name": "BTC_DATA.DATA.CDD",
            "date_col": "DATE",
            "numeric_cols": ["CDD_RAW", "CDD_30_DMA", "CDD_90_DMA"]
        },
        "MVRV": {
            "table_name": "BTC_DATA.DATA.MVRV",
            "date_col": "DATE",
            "numeric_cols": [
                "MVRV"
            ]
        },
        "NUPL": {
            "table_name": "BTC_DATA.DATA.NUPL",
            "date_col": "DATE",
            "numeric_cols": [
                "NUPL",
                "NUPL_PERCENT"
            ]
        },
        "REALIZED_CAP_VS_MARKET_CAP": {
            "table_name": "BTC_DATA.DATA.REALIZED_CAP_VS_MARKET_CAP",
            "date_col": "DATE",
            "numeric_cols": [
                "MARKET_CAP_USD",
                "REALIZED_CAP_USD"
            ]
        },
        "TX_COUNT": {
            "table_name": "BTC_DATA.DATA.TX_COUNT",
            "date_col": "BLOCK_TIMESTAMP",
            "numeric_cols": ["TX_COUNT"]
        },
        "TX_VOLUME": {
            "table_name": "BTC_DATA.DATA.TX_VOLUME",
            "date_col": "DATE",
            "numeric_cols": ["DAILY_TX_VOLUME_BTC"]
        },
        "UTXO_LIFECYCLE": {
            "table_name": "BTC_DATA.DATA.UTXO_LIFECYCLE",
            "date_col": "CREATED_TIMESTAMP",
            "numeric_cols": ["BTC_VALUE"]
        },
        "PUELL_MULTIPLE": {
            "table_name": "BTC_DATA.DATA.PUELL_MULTIPLE",
            "date_col": "DATE",
            "numeric_cols": [
                "MINTED_BTC",
                "DAILY_ISSUANCE_USD",
                "MA_365_ISSUANCE_USD",
                "PUELL_MULTIPLE"
            ]
        },
    }

    BTC_PRICE_TABLE = "BTC_DATA.DATA.BTC_PRICE_USD"
    BTC_PRICE_DATE_COL = "DATE"
    BTC_PRICE_VALUE_COL = "BTC_PRICE_USD"

    # 4) Page Title
    # ------------------------------------------------
    st.title("Bitcoin On-chain Indicators Dashboard")

    #########################
    # 5) CONTROLS (TOP)
    #########################
    control_container = st.container()
    with control_container:
        st.subheader("Chart Controls")

        # Table & Indicators
        selected_table = st.selectbox(
            "Select a Table (Metric Set)",
            list(TABLE_DICT.keys()),
            help="Pick which table (indicator set) to visualize."
        )

        table_info = TABLE_DICT[selected_table]
        all_numeric_cols = table_info["numeric_cols"]
        selected_columns = st.multiselect(
            "Select Indicator(s):",
            all_numeric_cols,
            default=all_numeric_cols,
            help="Pick one or more numeric columns to plot on the left axis."
        )

        # Axis Scales & Chart Types
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            scale_option_indicator = st.radio("Indicator Axis", ["Linear", "Log"], index=0)
        with col2:
            scale_option_price = st.radio("BTC Price Axis", ["Linear", "Log"], index=0)
        with col3:
            chart_type_indicators = st.radio("Indicators", ["Line", "Bars"], index=0)
        with col4:
            chart_type_price = st.radio("BTC Price", ["Line", "Bars"], index=0)

        # EMA Option
        show_ema = st.checkbox("Add EMA for Indicators", value=False)
        if show_ema:
            ema_period = st.number_input("EMA Period (days)", min_value=2, max_value=200, value=20)

        # Date & BTC Price toggle
        col5, col6 = st.columns(2)
        with col5:
            default_start_date = datetime.date(2015, 1, 1)
            selected_start_date = st.date_input(
                "Start Date",
                value=default_start_date,
                help="Filter data from this date onward."
            )
        with col6:
            show_btc_price = st.checkbox("Show BTC Price?", value=True)

        # NEW CHECKBOX: Plot BTC Price on same axis or secondary axis
        same_axis_checkbox = st.checkbox("Plot BTC Price on the same Y-axis as Indicators?", value=False)

        # Color Pickers
        st.markdown("---")
        st.markdown("**Colors**")
        if "colors" not in st.session_state:
            st.session_state["colors"] = {}

        # BTC Price color (if enabled)
        if show_btc_price:
            btc_price_color = st.color_picker(
                "BTC Price Color",
                value=st.session_state["colors"].get("BTC_PRICE", "#FFA500")
            )
            st.session_state["colors"]["BTC_PRICE"] = btc_price_color

        for col in selected_columns:
            default_col_color = st.session_state["colors"].get(col, "#0000FF")
            picked_color = st.color_picker(f"Color for {col}", value=default_col_color)
            st.session_state["colors"][col] = picked_color

    #########################
    # 6) CHART (BOTTOM)
    #########################
    plot_container = st.container()
    with plot_container:
        if not selected_columns:
            st.warning("Please select at least one indicator column.")
            st.stop()

        # Query BTC Price if requested
        btc_price_df = pd.DataFrame()
        if show_btc_price:
            btc_price_query = f"""
                SELECT
                    CAST({BTC_PRICE_DATE_COL} AS DATE) AS PRICE_DATE,
                    {BTC_PRICE_VALUE_COL}
                FROM {BTC_PRICE_TABLE}
                WHERE {BTC_PRICE_VALUE_COL} IS NOT NULL
                  AND CAST({BTC_PRICE_DATE_COL} AS DATE) >= '{selected_start_date}'
                ORDER BY PRICE_DATE
            """
            btc_price_df = session.sql(btc_price_query).to_pandas()
            btc_price_df.rename(columns={"PRICE_DATE": "DATE"}, inplace=True)

        # Query Selected Indicator(s)
        date_col = table_info["date_col"]
        columns_for_query = ", ".join(selected_columns)
        indicator_query = f"""
            SELECT
                CAST({date_col} AS DATE) AS IND_DATE,
                {columns_for_query}
            FROM {table_info['table_name']}
            WHERE CAST({date_col} AS DATE) >= '{selected_start_date}'
            ORDER BY IND_DATE
        """
        indicator_df = session.sql(indicator_query).to_pandas()
        indicator_df.rename(columns={"IND_DATE": "DATE"}, inplace=True)

        if indicator_df.empty and btc_price_df.empty:
            st.warning("No data returned. Check your date range or table.")
            st.stop()

        # Merge if BTC Price is shown
        if show_btc_price and not btc_price_df.empty:
            merged_df = pd.merge(
                btc_price_df,
                indicator_df,
                on="DATE",
                how="inner"
            )
        else:
            merged_df = indicator_df

        if merged_df.empty:
            st.warning("No overlapping data in the selected date range.")
            st.stop()

        # EMA Calculation
        if show_ema:
            for col in selected_columns:
                merged_df[f"EMA_{col}"] = merged_df[col].ewm(span=ema_period).mean()

        # Build Plotly Figure
        # Always create the figure with a secondary axis, but we'll decide
        # whether to plot BTC price on the secondary or the primary axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Plot each indicator on the left axis
        for col in selected_columns:
            if chart_type_indicators == "Line":
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[col],
                        mode="lines",
                        name=col,
                        line=dict(color=st.session_state["colors"][col]),
                    ),
                    secondary_y=False
                )
            else:  # Bars
                fig.add_trace(
                    go.Bar(
                        x=merged_df["DATE"],
                        y=merged_df[col],
                        name=col,
                        marker_color=st.session_state["colors"][col]
                    ),
                    secondary_y=False
                )
            if show_ema:
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[f"EMA_{col}"],
                        mode="lines",
                        name=f"EMA({ema_period}) - {col}",
                        line=dict(color=st.session_state["colors"][col], dash="dash"),
                        opacity=0.8
                    ),
                    secondary_y=False
                )

        # BTC Price
        if show_btc_price and not btc_price_df.empty:
            # Decide which axis to use based on checkbox
            price_secondary_y = (not same_axis_checkbox)

            if chart_type_price == "Line":
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["DATE"],
                        y=merged_df[BTC_PRICE_VALUE_COL],
                        mode="lines",
                        name="BTC Price (USD)",
                        line=dict(color=st.session_state["colors"]["BTC_PRICE"]),
                    ),
                    secondary_y=price_secondary_y
                )
            else:  # Bars
                fig.add_trace(
                    go.Bar(
                        x=merged_df["DATE"],
                        y=merged_df[BTC_PRICE_VALUE_COL],
                        name="BTC Price (USD)",
                        marker_color=st.session_state["colors"]["BTC_PRICE"]
                    ),
                    secondary_y=price_secondary_y
                )

        # Dynamic title
        if show_btc_price:
            fig_title = f"{selected_table} vs BTC Price"
        else:
            fig_title = f"{selected_table}"

        fig.update_layout(
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            title=fig_title,
            hovermode="x unified",
            font=dict(color="#f0f2f6"),
            legend=dict(
                x=0,
                y=1.05,
                bgcolor="rgba(0,0,0,0)",
                orientation="h"
            )
        )
        fig.update_xaxes(title_text="Date", gridcolor="#4f5b66")

        # Left Y-axis
        fig.update_yaxes(
            title_text="Indicator Value",
            type="log" if scale_option_indicator == "Log" else "linear",
            secondary_y=False,
            gridcolor="#4f5b66"
        )

        # Right Y-axis (only used if same_axis_checkbox is False)
        fig.update_yaxes(
            title_text="BTC Price (USD)" if not same_axis_checkbox else "",
            type="log" if scale_option_price == "Log" else "linear",
            secondary_y=True,
            gridcolor="#4f5b66"
        )

        st.plotly_chart(fig, use_container_width=True)

###############################################################################
#                    PAGE 2: SIMPLE BLOCK EXPLORER FUNCTION
###############################################################################
def show_block_explorer_page():
    """
    A simple demonstration of how you can create an interface similar
    to a block explorer, using the FACT_BLOCKS and FACT_TRANSACTIONS views
    from BITCOIN_ONCHAIN_CORE_DATA.CORE in Snowflake.

    This is just an example; you can customize as you wish.
    """
    st.title("Bitcoin Block Explorer")

    # --- Search bar ---
    st.write("Search by **block number**, **block hash**, **transaction ID**, or **transaction hash**.")
    search_input = st.text_input("Enter a value to search:")

    # If no search input -> Show the latest 10 blocks
    if not search_input:
        st.subheader("Latest Blocks")

        query_latest_blocks = """
            SELECT 
                BLOCK_NUMBER,
                BLOCK_HASH,
                BLOCK_TIMESTAMP,
                BLOCK_SIZE,
                TX_COUNT
            FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
            ORDER BY BLOCK_NUMBER DESC
            LIMIT 10
        """
        df_blocks = session.sql(query_latest_blocks).to_pandas()
        st.dataframe(df_blocks, use_container_width=True)

        # Let the user pick a block number to see details
        # (Pick from the table or from a selectbox)
        block_nums = df_blocks["BLOCK_NUMBER"].tolist()
        selected_block = st.selectbox("Select a block to view details:", block_nums)
        if selected_block:
            show_block_details(selected_block)

    else:
        # We have a search input -> attempt to detect what it is
        # 1. Check if it's numeric => possibly a block number
        # 2. Otherwise, try to see if it matches a block hash or a tx hash
        #    (both can be 64-hex length, but we can just do a direct query).
        # 3. Or a transaction ID (some columns might differ; adapt as needed).
        if search_input.isdigit():
            # Try searching by BLOCK_NUMBER
            block_number = int(search_input)
            query_block = f"""
                SELECT 
                    BLOCK_NUMBER,
                    BLOCK_HASH,
                    BLOCK_TIMESTAMP,
                    BLOCK_SIZE,
                    TX_COUNT
                FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
                WHERE BLOCK_NUMBER = {block_number}
                LIMIT 1
            """
            result = session.sql(query_block).to_pandas()
            if not result.empty:
                st.success(f"Found block #{block_number}")
                st.dataframe(result)
                show_block_details(block_number)
            else:
                st.error(f"No block found with block_number = {block_number}")
        else:
            # Attempt a block hash or TX hash
            # We'll do two queries: one for block hash, one for transaction hash
            # If you have TX_ID vs TX_HASH differences, adapt accordingly.
            # 1) Query block
            query_block_by_hash = f"""
                SELECT 
                    BLOCK_NUMBER,
                    BLOCK_HASH,
                    BLOCK_TIMESTAMP,
                    BLOCK_SIZE,
                    TX_COUNT
                FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
                WHERE BLOCK_HASH = '{search_input}'
                LIMIT 1
            """
            df_block = session.sql(query_block_by_hash).to_pandas()

            # 2) Query transaction
            query_tx_by_hash = f"""
                SELECT 
                    TX_ID,
                    TX_HASH,
                    BLOCK_NUMBER,
                    INPUT_COUNT,
                    OUTPUT_COUNT,
                    TOTAL_OUTPUT_SATS,
                    FEE_SATS
                FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
                WHERE TX_HASH = '{search_input}'
                LIMIT 1
            """
            df_tx = session.sql(query_tx_by_hash).to_pandas()

            if not df_block.empty:
                # Found a matching block
                block_number = df_block["BLOCK_NUMBER"].iloc[0]
                st.success(f"Found block with hash = {search_input}")
                st.dataframe(df_block)
                show_block_details(block_number)
            elif not df_tx.empty:
                # Found a matching transaction
                st.success(f"Found transaction with hash = {search_input}")
                st.dataframe(df_tx)
                tx_id = df_tx["TX_ID"].iloc[0]
                show_transaction_details(search_input, tx_id)
            else:
                st.error(f"No block or transaction found matching: {search_input}")


def show_block_details(block_number: int):
    """
    Display the detailed information for a given block_number,
    plus the transactions in that block, with an option to view TX details.
    """
    st.subheader(f"Block #{block_number} Details")

    # Query the block info
    block_query = f"""
        SELECT 
            BLOCK_NUMBER,
            BLOCK_HASH,
            BLOCK_TIMESTAMP,
            BLOCK_SIZE,
            TX_COUNT
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
        WHERE BLOCK_NUMBER = {block_number}
        LIMIT 1
    """
    df_block = session.sql(block_query).to_pandas()
    if not df_block.empty:
        st.write("**Block Info**")
        st.dataframe(df_block)

    # Query all transactions in that block
    tx_query = f"""
        SELECT 
            TX_ID,
            TX_HASH,
            INPUT_COUNT,
            OUTPUT_COUNT,
            TOTAL_OUTPUT_SATS,
            FEE_SATS
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE BLOCK_NUMBER = {block_number}
        ORDER BY TX_ID
        LIMIT 50
    """
    df_txs = session.sql(tx_query).to_pandas()

    st.write("**Transactions in this block (showing first 50):**")
    st.dataframe(df_txs, use_container_width=True)

    # Let user select a transaction from the table
    if not df_txs.empty:
        tx_hashes = df_txs["TX_HASH"].tolist()
        selected_tx_hash = st.selectbox("Select a transaction to view details:", tx_hashes)
        if selected_tx_hash:
            # get the TX_ID from that hash
            selected_tx_id = df_txs.loc[df_txs["TX_HASH"] == selected_tx_hash, "TX_ID"].iloc[0]
            show_transaction_details(selected_tx_hash, selected_tx_id)


def show_transaction_details(tx_hash: str, tx_id: int):
    """
    Display info about a single transaction (inputs, outputs, etc.)
    from FACT_TRANSACTIONS, FACT_INPUTS, FACT_OUTPUTS, etc.
    """
    st.subheader(f"Transaction Details for TX_HASH = {tx_hash}")

    # Basic transaction info
    tx_info_query = f"""
        SELECT
            BLOCK_NUMBER,
            TX_ID,
            TX_HASH,
            INPUT_COUNT,
            OUTPUT_COUNT,
            TOTAL_OUTPUT_SATS,
            FEE_SATS
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE TX_HASH = '{tx_hash}'
        LIMIT 1
    """
    df_tx_info = session.sql(tx_info_query).to_pandas()
    if not df_tx_info.empty:
        st.write("**Transaction Info**")
        st.dataframe(df_tx_info)

    # We can also show inputs and outputs if desired.
    # 1) Inputs
    inputs_query = f"""
        SELECT
            TX_ID,
            SRC_TX_HASH,
            SRC_OUTPUT_INDEX,
            INPUT_SATS
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_INPUTS
        WHERE TX_ID = {tx_id}
        LIMIT 50
    """
    df_inputs = session.sql(inputs_query).to_pandas()
    if not df_inputs.empty:
        st.write("**Transaction Inputs (first 50)**")
        st.dataframe(df_inputs, use_container_width=True)

    # 2) Outputs
    outputs_query = f"""
        SELECT
            TX_ID,
            OUTPUT_INDEX,
            OUTPUT_SATS,
            OUTPUT_TYPE
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_OUTPUTS
        WHERE TX_ID = {tx_id}
        LIMIT 50
    """
    df_outputs = session.sql(outputs_query).to_pandas()
    if not df_outputs.empty:
        st.write("**Transaction Outputs (first 50)**")
        st.dataframe(df_outputs, use_container_width=True)

###############################################################################
#                             MAIN APP LAYOUT
###############################################################################
def main():
    """
    Combine both pages in a single script with a sidebar to select
    between the Dashboard and the Block Explorer.
    """
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to page:", ["Dashboard", "Block Explorer"])

    if choice == "Dashboard":
        show_dashboard_page()
    else:
        # The block explorer page
        show_block_explorer_page()

if __name__ == "__main__":
    main()
