import streamlit as st
import urllib.parse

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Prospection Miroir MyTrax",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Switch Auto — Sourcing Pros & Matcher Miroir Particuliers")
st.caption("Mécanique MyTrax : Filtre Pro à gauche ➔ Recherche Miroir Particulier à droite")

# --- PARAMÈTRES FIXES MYTRAX ---
SECTEUR_LBC = "Roncq_59223__30000" # Roncq + 30 km
ANNEE_MIN_MYTRAX = 2006
KM_MAX_MYTRAX = 250000

# DISPOSITION EN 2 COLONNES PRINCIPALES
col_pros, col_miroir = st.columns([1, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : RECHERCHE PROS & CRITÈRES MYTRAX
# ==============================================================================
with col_pros:
    st.header("1. 🏬 Feed Annonces PROS (MyTrax)")
    st.info("""
    **🎯 Filtres d'éligibilité MyTrax appliqués :**
    * **Vendeurs :** Professionnels uniquement
    * **Zone :** Roncq + 30 km aux alentours
    * **Critères :** Année ≥ 2006 | Kilométrage ≤ 250 000 km | Origine France
    """)
    
    # URL globale de prospection LeBonCoin Pros (Filtrée MyTrax)
    lbc_global_pro_url = (
        f"https://www.leboncoin.fr/recherche?"
        f"category=2"
        f"&owner_type=pro"
        f"&regdate={ANNEE_MIN_MYTRAX}-max"
        f"&mileage=min-{KM_MAX_MYTRAX}"
        f"&locations={SECTEUR_LBC}"
    )

    st.markdown("### 🔍 Accès direct au catalogue Pro local")
    st.link_button(
        "🔍 Ouvrir LeBonCoin — Toutes les annonces PROS (Roncq +30km)", 
        lbc_global_pro_url, 
        use_container_width=True,
        type="primary"
    )
    
    st.markdown("---")
    st.markdown("### 📋 Saisie rapide du véhicule Pro repéré")
    st.caption("Renseigne ici les 4 éléments de l'annonce pro pour lancer le miroir :")
    
    c_make, c_model = st.columns(2)
    with c_make:
        make = st.text_input("Marque :", placeholder="ex: Peugeot, Dacia, Audi...")
    with c_model:
        model = st.text_input("Modèle :", placeholder="ex: 308, Duster, A4...")
        
    c_year, c_km = st.columns(2)
    with c_year:
        year = st.number_input("Année :", min_value=2006, max_value=2026, value=2016, step=1)
    with c_km:
        km = st.number_input("Kilométrage :", min_value=0, max_value=250000, value=110000, step=5000)

# ==============================================================================
# COLONNE DROITE : RECHERCHE MIROIR PARTICULIERS (SANS PRIX)
# ==============================================================================
with col_miroir:
    st.header("2. 👤 Recherche Miroir PARTICULIERS")
    
    if make and model:
        # Plages de tolérance (+/- 1 an et +/- 5 000 km)
        year_min = max(2006, int(year) - 1)
        year_max = int(year) + 1
        km_min = max(0, int(km) - 5000)
        km_max = min(250000, int(km) + 5000)
        
        query = f"{make} {model}".strip()
        encoded_query = urllib.parse.quote(query)
        
        # URL LeBonCoin PARTICULIERS (Mêmes critères hors prix)
        lbc_part_url = (
            f"https://www.leboncoin.fr/recherche?"
            f"category=2"
            f"&owner_type=private"
            f"&text={encoded_query}"
            f"&regdate={year_min}-{year_max}"
            f"&mileage={km_min}-{km_max}"
            f"&locations={SECTEUR_LBC}"
        )
        
        # URL La Centrale PARTICULIERS (Backup)
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "yearMin": year_min,
            "yearMax": year_max,
            "mileageMin": km_min,
            "mileageMax": km_max,
            "zipCodes": "59220,59000,59100,59200",
        }
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"

        st.success(f"✅ **Cible activée :** {make} {model} ({year} | {km:,} km)".replace(",", " "))
        
        st.markdown(f"""
        **Paramètres miroirs appliqués (Prix ignoré) :**
        * **Modèle :** `{make} {model}`
        * **Fenêtre Année :** `{year_min} - {year_max}`
        * **Fenêtre Kilométrage :** `{km_min:,}` à `{km_max:,}` km
        * **Secteur :** `Roncq + 30 km`
        """.replace(",", " "))
        
        st.markdown("---")
        
        st.subheader("🔗 Liens de comparaison Particuliers")
        
        st.link_button(
            f"🟠 🔍 LeBonCoin — PARTICULIERS pour {make} {model}", 
            lbc_part_url, 
            use_container_width=True,
            type="primary"
        )
        
        st.write("")
        
        st.link_button(
            f"🔵 🔍 La Centrale — PARTICULIERS pour {make} {model}", 
            lc_part_url, 
            use_container_width=True
        )

        st.info("""
        **💡 Prospection Switch Auto :**  
        Si le même véhicule ressort publié par un particulier, tu as identifié le mandat non-exclusif. Tu peux l'appeler directement !
        """)
        
    else:
        st.warning("👈 Indique la marque et le modèle du véhicule pro sélectionné à gauche pour générer les liens miroirs particuliers.")
