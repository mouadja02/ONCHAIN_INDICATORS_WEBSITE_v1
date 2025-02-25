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


#########################
# TRANSACTION DETAILS
#########################
def show_transaction_details(tx_id):
    """
    Display a "detailed" layout for the transaction from FACT_TRANSACTIONS,
    plus inputs/outputs from FACT_INPUTS and FACT_OUTPUTS. 
    Allows toggling between an Overview layout or raw JSON for each section.
    """
    st.subheader(f"Transaction details for TX_ID: {tx_id}")

    # 1) Basic transaction info from FACT_TRANSACTIONS
    tx_info_query = f"""
        SELECT
            BLOCK_NUMBER,
            BLOCK_TIMESTAMP,
            BLOCK_HASH,
            TX_ID,
            TX_HASH,
            FEE,
            IS_COINBASE,
            INPUT_COUNT,
            OUTPUT_COUNT,
            INPUT_VALUE,
            OUTPUT_VALUE,
            SIZE,
            WEIGHT,
            VERSION,
            LOCK_TIME
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_TRANSACTIONS
        WHERE TX_ID = '{tx_id}'
        LIMIT 1
    """
    tx_info_df = session.sql(tx_info_query).to_pandas()

    if tx_info_df.empty:
        st.warning("Transaction not found in FACT_TRANSACTIONS.")
        return

    # Show top summary in 2 columns
    row = tx_info_df.iloc[0]
    st.markdown(f"""
    ### Bitcoin Transaction
    Broadcasted on {row['BLOCK_TIMESTAMP']}
    """)

    # A quick row of some top-level fields
    colA, colB = st.columns(2)
    with colA:
        st.write("**Hash (TX_HASH)**:", row["TX_HASH"] if row["TX_HASH"] else "N/A")
        st.write("**TX_ID**:", row["TX_ID"])
        st.write("**Block Number**:", row["BLOCK_NUMBER"])
        st.write("**Coinbase**:", "Yes" if row["IS_COINBASE"] else "No")
    with colB:
        st.write("**Fee**:", row["FEE"])
        st.write("**Input Count**:", row["INPUT_COUNT"])
        st.write("**Output Count**:", row["OUTPUT_COUNT"])
        st.write("**Size (bytes)**:", row["SIZE"])

    # 2) Inputs
    inputs_query = f"""
        SELECT
            BLOCK_TIMESTAMP,
            BLOCK_NUMBER,
            BLOCK_HASH,
            TX_ID,
            INDEX,
            IS_COINBASE,
            SPENT_TX_ID,
            SPENT_OUTPUT_INDEX,
            VALUE,
            VALUE_SATS,
            INPUT_ID
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_INPUTS
        WHERE TX_ID = '{tx_id}'
        LIMIT 50
    """
    inputs_df = session.sql(inputs_query).to_pandas()

    st.write("### Transaction Inputs")
    if inputs_df.empty:
        st.info("No inputs found.")
    else:
        # Let user pick "Overview" or "Raw JSON" style
        view_mode_inputs = st.selectbox("View mode for Inputs", ["Overview", "Raw JSON"], key="inputs_view_mode")
        if view_mode_inputs == "Overview":
            # Show a simplified table or custom layout
            st.dataframe(inputs_df[["TX_ID","SPENT_TX_ID","SPENT_OUTPUT_INDEX","VALUE","VALUE_SATS"]], use_container_width=True)
        else:
            # Show raw JSON for all columns
            st.json(inputs_df.to_dict(orient="records"))

    # 3) Outputs
    outputs_query = f"""
        SELECT
            BLOCK_TIMESTAMP,
            BLOCK_NUMBER,
            BLOCK_HASH,
            TX_ID,
            INDEX,
            VALUE,
            VALUE_SATS,
            OUTPUT_ID
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_OUTPUTS
        WHERE TX_ID = '{tx_id}'
        LIMIT 50
    """
    outputs_df = session.sql(outputs_query).to_pandas()

    st.write("### Transaction Outputs")
    if outputs_df.empty:
        st.info("No outputs found.")
    else:
        view_mode_outputs = st.selectbox("View mode for Outputs", ["Overview", "Raw JSON"], key="outputs_view_mode")
        if view_mode_outputs == "Overview":
            st.dataframe(outputs_df[["TX_ID","INDEX","VALUE","VALUE_SATS"]], use_container_width=True)
        else:
            st.json(outputs_df.to_dict(orient="records"))


#########################
# BLOCK DETAILS
#########################
def show_block_details(block_number):
    """
    Display a "detailed" layout for a given block_number from FACT_BLOCKS,
    with transaction listing from FACT_TRANSACTIONS. Allows toggling 
    between overview or raw JSON for each major section.
    """
    st.subheader(f"Block #{block_number} Details")

    # Query block info from FACT_BLOCKS
    query_block = f"""
        SELECT 
            BLOCK_NUMBER,
            BLOCK_HASH,
            BLOCK_TIMESTAMP,
            SIZE,
            TX_COUNT,
            -- Possibly other columns if available, e.g. BITS, VERSION, NONCE, WEIGHT, etc.
            VERSION,
            INSERTED_TIMESTAMP,
            MODIFIED_TIMESTAMP
        FROM BITCOIN_ONCHAIN_CORE_DATA.CORE.FACT_BLOCKS
        WHERE BLOCK_NUMBER = '{block_number}'
        LIMIT 1
    """
    block_df = session.sql(query_block).to_pandas()
    if block_df.empty:
        st.warning("Block not found in FACT_BLOCKS.")
        return

    # Show top summary
    block_row = block_df.iloc[0]
    st.markdown(f"""
    ### Bitcoin Bloc {block_row['BLOCK_NUMBER']}
    **Mined on** {block_row['BLOCK_TIMESTAMP']}
    """)

    # Two-column detail layout
    colA, colB = st.columns(2)
    with colA:
        st.write("**Block Hash**:", block_row["BLOCK_HASH"])
        st.write("**Block Size**:", block_row["SIZE"])
        st.write("**TX Count**:", block_row["TX_COUNT"])
        st.write("**Version**:", block_row["VERSION"])
        # Add other columns if they exist in your DB
    with colB:
        # Just placeholders: only show if these columns exist
        st.write("**Inserted Timestamp**:", block_row["INSERTED_TIMESTAMP"])
        st.write("**Modified Timestamp**:", block_row["MODIFIED_TIMESTAMP"])
        # If you had more columns (e.g. difficulty, nonce), show them here

    # Optional "Overview" or "Raw JSON" for the block info
    view_mode_block = st.selectbox("View mode for Block Info", ["Overview", "Raw JSON"], key="block_view_mode")
    if view_mode_block == "Raw JSON":
        st.json(block_df.to_dict(orient="records"))

    # Query transactions in this block
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
        LIMIT 100
    """
    tx_df = session.sql(tx_query).to_pandas()

    st.write("### Transactions in this block (coinbase first, up to 100):")
    if tx_df.empty:
        st.info("No transactions found in this block.")
    else:
        # Let user pick "Overview" or "Raw JSON" for the TX listing
        view_mode_txs = st.selectbox("View mode for TX listing", ["Overview", "Raw JSON"], key="block_txs_view_mode")
        if view_mode_txs == "Overview":
            st.dataframe(tx_df, use_container_width=True)
        else:
            st.json(tx_df.to_dict(orient="records"))

        # Let the user select a TX_ID from the listing to see full details
        tx_ids = tx_df["TX_ID"].tolist()
        selected_tx_id = st.selectbox("Select a transaction to view details:", tx_ids)
        if selected_tx_id:
            show_transaction_details(selected_tx_id)


#########################
# MAIN LOGIC
#########################
if not search_input:
    # Show latest 10 blocks if no search
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

    if not df_blocks.empty:
        block_nums = df_blocks["BLOCK_NUMBER"].tolist()
        selected_block = st.selectbox("Select a block to view details:", block_nums)
        if selected_block:
            show_block_details(selected_block)

else:
    # We have some search input -> attempt to interpret
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
            block_num = df_block["BLOCK_NUMBER"].iloc[0]
            st.success(f"Found block with hash = {search_input}")
            st.dataframe(df_block)
            show_block_details(block_num)
        elif not df_tx.empty:
            st.success(f"Found transaction with TX_ID = {search_input}")
            st.dataframe(df_tx)
            show_transaction_details(search_input)
        else:
            st.error(f"No block or transaction found matching {search_input}.")
