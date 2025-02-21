import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Bitcoin Block Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Bitcoin Block Explorer")

# Snowflake connection
cx = st.connection("snowflake")
session = cx.session()

# Search bar
st.write("**Search by block number, block hash, or TX_ID.**")
search_input = st.text_input("Enter a value to search:")

def show_block_details(block_number):
    """
    Display block info for a given block_number, and list transactions
    by TX_ID (coinbase first). Also allow user to pick a TX_ID to see its details.
    """
    st.subheader(f"Block #'{block_number}' Details")

    # Query block info
    query_block = f"""
        SELECT 
            BLOCK_NUMBER,
            BLOCK_HASH,
            BLOCK_TIMESTAMP,
            SIZE,
            TX_COUNT
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
        WHERE BLOCK_NUMBER = '{block_number}'
        LIMIT 1
    """
    block_df = session.sql(query_block).to_pandas()
    if not block_df.empty:
        st.write("**Block Info**")
        st.dataframe(block_df)

    # Query transactions for this block, focusing on TX_ID, ignoring TX_HASH
    tx_query = f"""
        SELECT 
            TX_ID,
            INPUT_COUNT,
            OUTPUT_COUNT,
            OUTPUT_VALUE_SATS,
            FEE,
            IS_COINBASE
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE BLOCK_NUMBER = '{block_number}'
        ORDER BY IS_COINBASE DESC, TX_ID
        LIMIT 50
    """
    tx_df = session.sql(tx_query).to_pandas()

    st.write("**Transactions in this block (coinbase first, showing up to 50):**")
    st.dataframe(tx_df, use_container_width=True)

    # Allow user to pick a TX_ID from a selectbox
    if not tx_df.empty:
        tx_ids = tx_df["TX_ID"].tolist()
        selected_tx_id = st.selectbox("Select a transaction to view details:", tx_ids)
        if selected_tx_id:
            show_transaction_details(selected_tx_id)

def show_transaction_details(tx_id):
    """
    Display details for a single transaction (identified only by TX_ID).
    Includes transaction-level info plus inputs/outputs.
    """
    st.subheader(f"Transaction details for TX_ID: {tx_id}")

    # Query transaction info
    tx_info_query = f"""
        SELECT
            BLOCK_NUMBER,
            TX_ID,
            INPUT_COUNT,
            OUTPUT_COUNT,
            OUTPUT_VALUE_SATS,
            FEE,
            IS_COINBASE
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE TX_ID = '{tx_id}'
        ORDER BY IS_COINBASE DESC
        LIMIT 10
    """
    tx_info_df = session.sql(tx_info_query).to_pandas()
    if not tx_info_df.empty:
        st.write("**Transaction Info**")
        st.dataframe(tx_info_df)

    # Query inputs
    inputs_query = f"""
        SELECT
            TX_ID,
            SPENT_TX_ID,
            SPENT_OUTPUT_INDEX,
            VALUE_SATS
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_INPUTS
        WHERE TX_ID = '{tx_id}'
        LIMIT 50
    """
    inputs_df = session.sql(inputs_query).to_pandas()
    if not inputs_df.empty:
        st.write("**Transaction Inputs (first 50)**")
        st.dataframe(inputs_df, use_container_width=True)

    # Query outputs
    outputs_query = f"""
        SELECT
            TX_ID,
            INDEX,
            VALUE_SATS
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_OUTPUTS
        WHERE TX_ID = '{tx_id}'
        LIMIT 50
    """
    outputs_df = session.sql(outputs_query).to_pandas()
    if not outputs_df.empty:
        st.write("**Transaction Outputs (first 50)**")
        st.dataframe(outputs_df, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Main logic for this page
# ─────────────────────────────────────────────────────────────────────────────

if not search_input:
    # If no search input, show latest 10 blocks
    st.subheader("Latest Blocks")
    latest_blocks_query = """
        SELECT 
            BLOCK_NUMBER,
            BLOCK_HASH,
            BLOCK_TIMESTAMP,
            SIZE,
            TX_COUNT
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
        ORDER BY BLOCK_NUMBER DESC
        LIMIT 10
    """
    df_blocks = session.sql(latest_blocks_query).to_pandas()
    st.dataframe(df_blocks, use_container_width=True)

    # Let the user pick a block
    if not df_blocks.empty:
        block_nums = df_blocks["BLOCK_NUMBER"].tolist()
        selected_block = st.selectbox("Select a block to view details:", block_nums)
        if selected_block:
            show_block_details(selected_block)

else:
    # If there's search input, attempt to interpret it.
    if search_input.isdigit():
        # Possibly a block_number
        query_block = f"""
            SELECT 
                BLOCK_NUMBER,
                BLOCK_HASH,
                BLOCK_TIMESTAMP,
                SIZE,
                TX_COUNT
            FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
            WHERE BLOCK_NUMBER = {int(search_input)}
            LIMIT 1
        """
        result = session.sql(query_block).to_pandas()
        if not result.empty:
            st.success(f"Found block #{search_input}")
            st.dataframe(result)
            show_block_details(int(search_input))
        else:
            st.error(f"No block found for block_number = {search_input}")
    else:
        # Possibly a block hash or a TX_ID
        block_hash_query = f"""
            SELECT 
                BLOCK_NUMBER,
                BLOCK_HASH,
                BLOCK_TIMESTAMP,
                SIZE,
                TX_COUNT
            FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
            WHERE BLOCK_HASH = '{search_input}'
            LIMIT 1
        """
        df_block = session.sql(block_hash_query).to_pandas()

        tx_id_query = f"""
            SELECT 
                TX_ID,
                BLOCK_NUMBER,
                INPUT_COUNT,
                OUTPUT_COUNT,
                OUTPUT_VALUE_SATS,
                FEE
            FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
            WHERE TX_ID = '{search_input}'
            LIMIT 1
        """
        df_tx = session.sql(tx_id_query).to_pandas()

        if not df_block.empty:
            # Found a block matching that hash
            block_num = df_block["BLOCK_NUMBER"].iloc[0]
            st.success(f"Found block with hash = {search_input}")
            st.dataframe(df_block)
            show_block_details(block_num)
        elif not df_tx.empty:
            # Found a transaction matching that TX_ID
            st.success(f"Found transaction with TX_ID = {search_input}")
            st.dataframe(df_tx)
            show_transaction_details(search_input)
        else:
            st.error(f"No block or transaction found matching {search_input}.")
