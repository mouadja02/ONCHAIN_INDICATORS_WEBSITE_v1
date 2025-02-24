# streamlit_app.py
import streamlit as st

# IMPORTANT: set_page_config must be the first Streamlit call
st.set_page_config(
    page_title="Bitcoin On-Chain Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Bootstrap + custom CSS/HTML
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">

<style>
/* Hide the default Streamlit hamburger menu and footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Make body background dark if desired */
body {
  background-color: #000000;
  color: #f0f2f6;
}

/* A custom navbar (fixed top) using Bootstrap classes */
.navbar-custom {
  background-color: #111111 !important;
}

/* Optional: tweak some margins */
.container {
  margin-top: 80px; /* so content isn't hidden behind the navbar */
}
</style>

<!-- NAVBAR -->
<nav class="navbar navbar-expand-lg navbar-dark navbar-custom fixed-top">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">OnChain Explorer</a>
    <button class="navbar-toggler" type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto">
        <!--
          We can't do real multi-route links easily in default Streamlit,
          but we can link to pages if we deploy externally or just keep these as placeholders.
        -->
        <li class="nav-item">
          <a class="nav-link" href="/?page=OnChainVitals">OnChainVitals</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/?page=BlockchainScope">BlockchainScope</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
""", unsafe_allow_html=True)

st.title("Bienvenue sur mon application Bitcoin On-chain Explorer")

st.write("""
<div class="container">
  <h2>Accueil</h2>
  <p>Bienvenue ! Cette application Streamlit propose :</p>
  <ul>
    <li>**OnChainVitals** : indicateurs on-chain (MVRV, CDD, etc.).</li>
    <li>**BlockchainScope** : un block explorer basique pour Bitcoin.</li>
  </ul>
  <p>Utilisez le menu dans la barre latérale (Streamlit) ou dans la navbar ci-dessus 
  pour naviguer.</p>
</div>
""", unsafe_allow_html=True)
