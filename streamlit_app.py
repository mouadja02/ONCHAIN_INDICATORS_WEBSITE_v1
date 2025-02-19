import streamlit as st

st.set_page_config(
    page_title="Application Bitcoin On-chain",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Bienvenue sur mon application Bitcoin On-chain")

st.write("""
Utilisez la barre latérale pour explorer :
- OnChainVitals (affiche des indicateurs on-chain).
- BlockchainScope (explorer les blocs et les transactions).
""")
