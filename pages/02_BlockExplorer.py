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
st.write("**Search by block number, block hash, TX_ID, or TX_HASH.**")
search_input = st.text_input("Enter a value to search:")

def show_block_details(block_number):
    st.subheader(f"Block #{block_number} Details")

    query_block = f"""
        SELECT 
            BLOCK_NUMBER,
            BLOCK_HASH,
            BLOCK_TIMESTAMP,
            SIZE,
            TX_COUNT
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
        WHERE BLOCK_NUMBER = {block_number}
        LIMIT 1
    """
    block_df = session.sql(query_block).to_pandas()
    if not block_df.empty:
        st.write("**Block Info**")
        st.dataframe(block_df)

    # Show transactions in this block
    tx_query = f"""
        SELECT 
            TX_ID,
            TX_HASH,
            INPUT_COUNT,
            OUTPUT_COUNT,
            OUTPUT_VALUE_SATS,
            FEE
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE BLOCK_NUMBER = {block_number}
        ORDER BY TX_ID
        LIMIT 50
    """
    tx_df = session.sql(tx_query).to_pandas()
    st.write("**Transactions in this block (first 50):**")
    st.dataframe(tx_df, use_container_width=True)

    if not tx_df.empty:
        tx_hashes = tx_df["TX_HASH"].tolist()
        selected_tx_hash = st.selectbox("Select a transaction to view details:", tx_hashes)
        if selected_tx_hash:
            selected_tx_id = tx_df.loc[tx_df["TX_HASH"] == selected_tx_hash, "TX_ID"].iloc[0]
            show_transaction_details(selected_tx_hash, selected_tx_id)

def show_transaction_details(tx_hash, tx_id):
    st.subheader(f"Transaction details for {tx_hash}")

    # Basic tx info
    tx_info_query = f"""
        SELECT
            BLOCK_NUMBER,
            TX_ID,
            TX_HASH,
            INPUT_COUNT,
            OUTPUT_COUNT,
            OUTPUT_VALUE_SATS,
            FEE
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE TX_HASH = '{tx_hash}'
        LIMIT 1
    """
    tx_info_df = session.sql(tx_info_query).to_pandas()
    if not tx_info_df.empty:
        st.write("**Transaction Info**")
        st.dataframe(tx_info_df)

    # Inputs
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
    inputs_df = session.sql(inputs_query).to_pandas()
    if not inputs_df.empty:
        st.write("**Transaction Inputs (first 50)**")
        st.dataframe(inputs_df, use_container_width=True)

    # Outputs
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
    outputs_df = session.sql(outputs_query).to_pandas()
    if not outputs_df.empty:
        st.write("**Transaction Outputs (first 50)**")
        st.dataframe(outputs_df, use_container_width=True)

# Main logic for this page
if not search_input:
    # Show latest 10 blocks
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
    # Try to detect if it's a block number or a hash
    if search_input.isdigit():
        # Try block_number
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
        # Try block hash or tx hash
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

        tx_hash_query = f"""
            SELECT 
                TX_ID,
                TX_HASH,
                BLOCK_NUMBER,
                INPUT_COUNT,
                OUTPUT_COUNT,
                OUTPUT_VALUE_SATS,
                FEE
            FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
            WHERE TX_HASH = '{search_input}'
            LIMIT 1
        """
        df_tx = session.sql(tx_hash_query).to_pandas()

        if not df_block.empty:
            block_num = df_block["BLOCK_NUMBER"].iloc[0]
            st.success(f"Found block with hash = {search_input}")
            st.dataframe(df_block)
            show_block_details(block_num)
        elif not df_tx.empty:
            st.success(f"Found transaction with hash = {search_input}")
            st.dataframe(df_tx)
            tx_id = df_tx["TX_ID"].iloc[0]
            show_transaction_details(search_input, tx_id)
        else:
            st.error(f"No block or transaction found matching {search_input}.")
