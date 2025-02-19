import streamlit as st

st.set_page_config(
    page_title="Bitcoin On-chain App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Welcome to My Bitcoin On-chain App")

st.write("""
Use the sidebar to explore:
- OnChainVitals (displays on-chain indicators).
- BlockchainScope (browse blocks and transactions).
""")
