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
    # Include the price column plus the selected indicators
    cols_for_corr = [price_col] + selected_indicators
    corr_data = df[cols_for_corr].corr()  # Pearson correlation matrix

    st.write("### Matrice de corrélation")
    st.dataframe(corr_data)

    # Determine figure size based on number of features
    num_features = len(cols_for_corr)
    fig_width = max(8, num_features * 0.8)
    fig_height = max(6, num_features * 0.8)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Set dark background (like in the seaborn version)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    
    # Display the correlation matrix using imshow with similar parameters as sns.heatmap
    im = ax.imshow(corr_data, cmap="RdBu_r", vmin=-1, vmax=1, aspect="equal")
    
    # Set ticks with white labels
    ax.set_xticks(np.arange(len(cols_for_corr)))
    ax.set_yticks(np.arange(len(cols_for_corr)))
    ax.set_xticklabels(cols_for_corr, rotation=45, ha="right", color="white")
    ax.set_yticklabels(cols_for_corr, color="white")
    
    # Annotate each cell with the correlation value (formatted to 2 decimals)
    for i in range(len(cols_for_corr)):
        for j in range(len(cols_for_corr)):
            ax.text(j, i, f"{corr_data.iloc[i, j]:.2f}",
                    ha="center", va="center", color="white")
    
    # Add colorbar with a white label
    cbar = plt.colorbar(im, ax=ax, shrink=0.75)
    cbar.set_label("Correlation", color="white")
    
    # Set title in white
    ax.set_title("Correlation Matrix of On-chain Features", color="white")
    
    fig.tight_layout()
    st.pyplot(fig)


import io

######################################
# Option to Save Plot on White Background
######################################
if st.button("Save Correlation Plot (White Background)"):
    fig_width = max(8, num_features * 0.8)
    fig_height = max(6, num_features * 0.8)
    fig_save, ax_save = plt.subplots(figsize=(fig_width, fig_height))
    fig_save.patch.set_facecolor("white")
    ax_save.set_facecolor("white")
    
    sns.heatmap(
        corr_matrix,
        annot=True,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        square=True,
        ax=ax_save,
        fmt=".2f",
        cbar_kws={'shrink': 0.75, 'label': 'Correlation'}
    )
    ax_save.set_title("Correlation Matrix of On-chain Features", color="black")
    plt.xticks(rotation=45, ha="right", color="black")
    plt.yticks(rotation=0, color="black")
    
    # Enregistrer la figure dans un buffer
    buf = io.BytesIO()
    fig_save.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    st.download_button("Download Plot as PNG", data=buf, file_name="correlation_heatmap.png", mime="image/png")
    
    plt.close(fig_save)
