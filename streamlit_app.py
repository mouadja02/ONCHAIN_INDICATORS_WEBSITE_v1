import streamlit as st

# For multi-page apps with the Streamlit pages/ folder approach,
# this main page can be minimal. You can set a page config if you like:
st.set_page_config(
    page_title="Bitcoin On-chain App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Welcome to My Bitcoin On-chain App")

st.write("""
Use the sidebar to explore:
- The Dashboard (displays on-chain indicators).
- The Block Explorer (browse blocks and transactions).
""")
