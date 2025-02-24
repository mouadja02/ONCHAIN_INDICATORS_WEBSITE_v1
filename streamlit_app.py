import streamlit as st

st.set_page_config(
    page_title="Bitcoin On-Chain App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Bienvenue sur mon application Bitcoin On-chain Explorer")

st.write("""
Utilisez la barre latérale pour explorer :
- OnChainVitals (affiche des indicateurs on-chain).
- BlockchainScope (explorer les blocs et les transactions).
""")
