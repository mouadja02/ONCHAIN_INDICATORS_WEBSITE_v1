import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import snowflake.connector

# -----------------------------------------------------------------------------
# 1. Connexion à Snowflake (exemple minimal - adaptez selon vos identifiants)
# -----------------------------------------------------------------------------
def load_data_from_snowflake():
    # Remplacez par vos propres identifiants
    cx = st.connection("snowflake")
    session = cx.session()
    query = """
        SELECT * 
        FROM BTC_DATA.DATA.BTC_ALL_INDICATORS_STATES
        ORDER BY date_week
    """
    df = session.sql(query).to_pandas()
    return df

# -----------------------------------------------------------------------------
# 2. Chargement et préparation des données
# -----------------------------------------------------------------------------
st.title("Correlation Dashboard - BTC Price Movement & Indicators")

@st.cache_data  # Cache Streamlit pour éviter de recharger à chaque rafraîchissement
def load_data():
    return load_data_from_snowflake()

df = load_data()

st.write("Aperçu des données (BTC_ALL_INDICATORS_STATES) :")
st.dataframe(df.head(10))

# La colonne du mouvement de prix (par défaut)
price_col = "PRICE_MOVEMENT_STATE"

# -----------------------------------------------------------------------------
# 3. Barre latérale : sélection des indicateurs
# -----------------------------------------------------------------------------
all_state_cols = [col for col in df.columns 
                  if col.endswith("_STATE") and col != price_col]

st.sidebar.write("## Choisissez les indicateurs à inclure dans la corrélation :")
selected_indicators = st.sidebar.multiselect(
    "Indicateurs on-chain (états discrets)",
    options=all_state_cols,
    default=all_state_cols[:5]  # Exemple : on en sélectionne 5 par défaut
)

# -----------------------------------------------------------------------------
# 4. Construction de la matrice de corrélation
# -----------------------------------------------------------------------------
if not selected_indicators:
    st.warning("Veuillez sélectionner au moins un indicateur.")
else:
    # On inclut la colonne du prix + les indicateurs choisis
    cols_for_corr = [price_col] + selected_indicators
    corr_data = df[cols_for_corr].corr()  # matrice de corrélation (Pearson par défaut)

    st.write("### Matrice de corrélation")
    st.dataframe(corr_data)

    # -----------------------------------------------------------------------------
    # 5. Visualisation - heatmap matplotlib
    # -----------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(corr_data, cmap="RdBu_r", aspect="auto")

    ax.set_xticks(np.arange(len(cols_for_corr)))
    ax.set_yticks(np.arange(len(cols_for_corr)))
    ax.set_xticklabels(cols_for_corr, rotation=45, ha="right")
    ax.set_yticklabels(cols_for_corr)

    for i in range(len(cols_for_corr)):
        for j in range(len(cols_for_corr)):
            text = ax.text(
                j, i,
                f"{corr_data.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if abs(corr_data.iloc[i, j]) > 0.5 else "black"
            )

    fig.tight_layout()

    st.pyplot(fig)
