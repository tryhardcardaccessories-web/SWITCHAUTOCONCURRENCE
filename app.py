import streamlit as st
import pandas as pd
import urllib.parse
import requests
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Hub & Chasse Miroir",
    page_icon="🚗",
    layout="wide"
)

# --- CONSTANTES & LISTE DES 11 AGENCES DU SECTEUR ---
SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km

AGENCES_CONCURRENCE = {
    "1. Transakauto Roncq": "https://www.leboncoin.fr/boutique/7447928",
    "2. Transakauto Wambrechies": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&locations=Wambrechies_59118__30000",
    "3. Partenaire Auto": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Partenaire%20Auto&locations=Roncq_59223__30000",
    "4. Ewigo Roncq": "https://www.leboncoin.fr/boutique/7145725/ewigo_roncq.htm",
    "5. Ewigo Villeneuve d'Ascq": "https://www.leboncoin.fr/boutique/7032084/ewigo_lille_villeneuve_dascq.htm",
    "6. Ewigo Lesquin": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Ewigo%20Lesquin&locations=Lesquin_59810__30000",
    "7. Simplicicar La Madeleine": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Simplicicar&locations=La%20Madeleine_59110__30000",
    "8. Via Automobile Roncq": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Via%20Automobile&locations=Roncq_59223__30000",
    "9. Via Automobile Villeneuve d'Ascq": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Via%20Automobile&locations=Villeneuve-d'Ascq_59650__30000",
    "10. Vroom Market": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Vroom%20Market&locations=Roncq_59223__30000",
    "11. L'Agence Automobilière Wasquehal": "https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text=Agence%20Automobiliere&locations=Wasquehal_59290__30000"
}

def extract_ad_info_from_url(url):
    """Extrait sommairement les infos si c'est une URL LBC, sinon prépare un squelette vide modifiable."""
    # Valeurs par défaut modifiables par l'utilisateur
    info = {
        "title": "Véhicule Pro Concurrence",
        "make": "",
        "model": "",
        "year": "2018",
        "km": "100000",
        "url": url
    }
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            html = res.text
            # Tentative de récupération du titre via la balise OpenGraph ou title
            title_match = re.search(r'<meta property="og:title" content="(.*?)">', html)
            if title_match:
                full_title = title_match.group(1)
                info["title"] = full_title
                parts = full_title.split()
                if len(parts) > 0: info["make"] = parts[0]
                if len(parts) > 1: info["model"] = parts[1]
            
            # Recherche d'année et km dans le texte de la page si possible
            year_match = re.search(r'\b(20[0-2]\d)\b', html)
            if year_match: info["year"] = year_match.group(1)
            
            km_match = re.search(r'(\d{2,3}[\s]?\d{3})\s*km', html, re.IGNORECASE)
            if km_match:
                info["km"] = re.sub(r'\D', '', km_match.group(1))
    except Exception:
        pass
    return info

# Initialisation de la session
if "target_car" not in st.session_state:
    st.session_state["target_car"] = None

st.title("🚗 Switch Auto — Hub & Chasse Miroir Particuliers")
st.caption("Sélectionne une agence, consulte son catalogue, et colle l'URL de l'annonce pro pour lancer le miroir.")

# --- BARRE LATÉRALE : LES 11 AGENCES DU SECTEUR ---
st.sidebar.header("🏪 Hub des 11 Agences Concurrentes")
st.sidebar.markdown("Clique sur une agence pour ouvrir son catalogue dans un onglet :")

selected_agency_name = st.sidebar.selectbox("Choisir une agence :", list(AGENCES_CONCURRENCE.keys()))
agency_url = AGENCES_CONCURRENCE[selected_agency_name]

st.sidebar.link_button(f"🌐 Ouvrir le catalogue de {selected_agency_name}", agency_url, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Analyseur d'Annonce Pro")
pro_url_input = st.sidebar.text_input("Colle l'URL de l'annonce pro ici :", placeholder="https://www.leboncoin.fr/voitures/...")

delta_km = st.sidebar.slider("Tolérance delta kilométrage (± en km) :", min_value=50, max_value=10000, value=500, step=50)

if st.sidebar.button("🔍 Analyser et Préparer le Miroir", type="primary"):
    if pro_url_input:
        with st.spinner("Analyse des caractéristiques du véhicule..."):
            car_data = extract_ad_info_from_url(pro_url_input)
            st.session_state["target_car"] = car_data
            st.sidebar.success("Véhicule analysé avec succès !")
    else:
        st.sidebar.error("Veuillez coller une URL valide.")

# --- INTERFACE PRINCIPALE EN DEUX COLONNES ---
col_left, col_right = st.columns([1.2, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : FICHE DU VÉHICULE ANALYSÉ & AJUSTEMENT
# ==============================================================================
with col_left:
    st.header("📋 Fiche Technique du Véhicule Pro")
    
    car = st.session_state["target_car"]
    
    if car is not None:
        st.success(f"🎯 **Annonce source :** [{car['title']}]({car['url']})")
        
        # Formulaire d'ajustement rapide pour s'assurer que les critères sont parfaits
        with st.form("edit_car_form"):
            st.write("Vérifie et affine les critères extraits si besoin :")
            edit_make = st.text_input("Marque", value=car["make"])
            edit_model = st.text_input("Modèle", value=car["model"])
            edit_year = st.text_input("Année", value=car["year"])
            edit_km = st.text_input("Kilométrage exact", value=car["km"])
            
            update_btn = st.form_submit_button("💾 Valider les critères")
            if update_btn:
                car["make"] = edit_make
                car["model"] = edit_model
                car["year"] = edit_year
                car["km"] = edit_km
                st.success("Critères mis à jour !")
        
        st.info(f"""
        **Paramètres retenus :**
        * **Modèle :** `{car['make']} {car['model']}`
        * **Année :** `{car['year']}`
        * **Kilométrage :** `{car['km']} km` (Delta : ± {delta_km} km)
        * **Secteur :** `Roncq + 30 km`
        """)
    else:
        st.info("""
        👈 **Mode d'emploi :**
        1. Sélectionne une agence dans la barre latérale et ouvre son catalogue.
        2. Copie l'URL d'une annonce qui t'intéresse.
        3. Colle-la dans le champ de la barre latérale et clique sur **Analyser et Préparer le Miroir**.
        """)

# ==============================================================================
# COLONNE DROITE : RÉSULTATS DU MIRRORING PARTICULIER
# ==============================================================================
with col_right:
    st.header("👤 Mirroring Particuliers (Mandat Simple)")
    
    car = st.session_state["target_car"]
    
    if car is not None:
        make = car["make"].strip()
        model = car["model"].strip()
        year_str = car["year"].strip()
        km_str = car["km"].strip()
        
        # Calcul de la tranche de kilométrage avec le delta choisi
        base_km = int(re.sub(r'\D', '', km_str)) if km_str.isdigit() else 100000
        km_min = max(0, base_km - delta_km)
        km_max = base_km + delta_km
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # URL LeBonCoin Particuliers avec Année stricte et Tranche kilométrage (Delta)
        lbc_part_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=private&text={query_encoded}&locations={SECTEUR_LBC}"
        if year_str.isdigit():
            lbc_part_url += f"&regdate={year_str}-{year_str}"
        lbc_part_url += f"&mileage={km_min}-{km_max}"
        
        # URL La Centrale Particuliers équivalente
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "zipCodes": "59220,59000,59100,59200",
            "mileageMin": km_min,
            "mileageMax": km_max,
        }
        if year_str.isdigit():
            lc_params["yearMin"] = year_str
            lc_params["yearMax"] = year_str
            
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.markdown(f"""
        ### Liens de recherche ciblés :
        * **Tranche KM recherchée :** `{km_min:,} km` à `{km_max:,} km` (Delta ± {delta_km} km)
        """)
        
        st.markdown("---")
        
        st.link_button(
            f"🟠 🔍 Lancer le Miroir LeBonCoin Particuliers", 
            lbc_part_url, 
            use_container_width=True, 
            type="primary"
        )
        
        st.write("")
        
        st.link_button(
            f"🔵 🔍 Lancer le Miroir La Centrale Particuliers", 
            lc_part_url, 
            use_container_width=True
        )
        
        st.warning("""
        💡 **Chasse au Mandat Simple :** En cliquant, les liens s'ouvrent directement avec les filtres taillés sur mesure (marque, modèle, année et kilométrage proche). Si le particulier a posté la même caisse, tu la vois en haut de liste !
        """)
    else:
        st.warning("👈 Configure d'abord un véhicule à gauche pour générer les liens de mirroring ici.")
