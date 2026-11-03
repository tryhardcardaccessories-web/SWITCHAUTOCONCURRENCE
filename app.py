import streamlit as st
import pandas as pd
import urllib.parse

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Radar Concurrence Google Sheets",
    page_icon="🚗",
    layout="wide"
)

# --- CONFIGURATION GOOGLE SHEETS ---
# ID extrait de ton lien de partage
SHEET_ID = "1l4CPiJ11n-zhB5RYsAHqOjp5Y7Mm2NOoTlihNAvrTCg"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km

@st.cache_data(ttl=60) # Cache de 60 secondes pour rafraîchir en direct si tu modifies ton Sheets
def load_sheet_data():
    """Charge les données directement depuis ton Google Sheets 'Concurrence Switch Auto'."""
    try:
        df = pd.read_csv(SHEET_URL)
        # Nettoyage des noms de colonnes (minuscules et sans espaces)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erreur de lecture du Google Sheets : {e}")
        return pd.DataFrame()

# Initialisation de la sélection
if "selected_car" not in st.session_state:
    st.session_state["selected_car"] = None

st.title("🚗 Switch Auto — Radar Mandats Simples (Google Sheets)")
st.caption("Base de données centralisée : Concurrence Roncq + 30 km")

# Barre latérale : Infos et lien direct vers le Sheet
st.sidebar.header("📁 Source des données")
st.sidebar.markdown(f"[🔗 Ouvrir ton Google Sheets 'Concurrence'](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)")

if st.sidebar.button("🔄 Rafraîchir les données du Sheets", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Chargement du DataFrame depuis le Sheets
df_pros = load_sheet_data()

# --- LAYOUT EN DEUX COLONNES ---
col_left, col_right = st.columns([1.3, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : TABLEAU DES PROS (ISSU DU SHEETS)
# ==============================================================================
with col_left:
    st.header("📋 Véhicules Concurrence (Secteur Roncq)")
    
    if len(df_pros) > 0:
        st.write("Sélectionne un véhicule pour lancer sa recherche miroir :")
        
        for idx, row in df_pros.iterrows():
            with st.container():
                # Récupération sécurisée des colonnes
                title = row.get("title", "Véhicule sans titre")
                make = row.get("make", "")
                model = row.get("model", "")
                year = row.get("year", "")
                
                c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1.5])
                with c1:
                    st.markdown(f"**{title}**")
                    st.caption(f"{make} {model}")
                with c2:
                    st.write(f"📅 {year}")
                with c3:
                    st.write("Secteur Roncq")
                with c4:
                    if st.button("🔍 Miroir", key=f"btn_{idx}", type="secondary"):
                        st.session_state["selected_car"] = row
                        st.rerun()
                st.markdown("---")
    else:
        st.warning("⚠️ Ton Google Sheets semble vide ou inaccessible. Vérifie qu'il contient bien les colonnes `title`, `make`, `model`, `year` et qu'il est partagé en mode public.")

# ==============================================================================
# COLONNE DROITE : FENÊTRE MIROIR PARTICULIER
# ==============================================================================
with col_right:
    st.header("👤 Recherche Miroir Particulier")
    
    car = st.session_state["selected_car"]
    
    if car is not None:
        title = car.get("title", "")
        make = str(car.get("make", "")).strip()
        model = str(car.get("model", "")).strip()
        year_val = str(car.get("year", "")).strip()
        
        st.success(f"🎯 **Cible sélectionnée :** {title}")
        
        st.markdown(f"""
        **Critères de recherche miroir appliqués :**
        * **Marque / Modèle :** `{make} {model}`
        * **Année stricte :** `{year_val}`
        * **Secteur :** `Roncq + 30 km`
        """)
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # URL LeBonCoin Particuliers (Année exacte)
        lbc_part_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=private&text={query_encoded}&locations={SECTEUR_LBC}"
        if year_val.isdigit():
            lbc_part_url += f"&regdate={year_val}-{year_val}"
            
        # URL La Centrale Particuliers (Année exacte)
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "zipCodes": "59220,59000,59100,59200",
        }
        if year_val.isdigit():
            lc_params["yearMin"] = year_val
            lc_params["yearMax"] = year_val
            
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.markdown("---")
        
        st.link_button(
            f"🟠 🔍 Ouvrir Miroir LeBonCoin (Particuliers)", 
            lbc_part_url, 
            use_container_width=True, 
            type="primary"
        )
        
        st.write("")
        
        st.link_button(
            f"🔵 🔍 Ouvrir Miroir La Centrale (Particuliers)", 
            lc_part_url, 
            use_container_width=True
        )
        
        st.info("""
        💡 **Rappel Mission :** Si l'annonce du particulier apparaît sur LeBonCoin avec cette année-là sur le secteur, tu as ton mandat simple à prospecter en direct !
        """)
    else:
        st.warning("👈 Clique sur le bouton **« 🔍 Miroir »** à gauche pour afficher les liens de recherche correspondants ici.")
