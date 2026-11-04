import streamlit as st
import pandas as pd
import urllib.parse
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

def parse_full_ad_text(raw_text):
    """Analyse le texte brut d'une page d'annonce complète pour en extraire les critères clés."""
    extracted = {
        "title": "Véhicule Pro",
        "make": "",
        "model": "",
        "year": "2018",
        "km": "100000"
    }
    
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
    # Recherche de l'année (ex: 2015 à 2026)
    for line in lines:
        year_match = re.search(r'\b(20[0-2]\d)\b', line)
        if year_match and not extracted["year"] or (extracted["year"] == "2018" and year_match):
            extracted["year"] = year_match.group(1)
            
        # Recherche du kilométrage (ex: 125 000 km ou 125000km)
        km_match = re.search(r'(\d+[\s\d]*)\s*km', line, re.IGNORECASE)
        if km_match:
            clean_km = re.sub(r'\D', '', km_match.group(1))
            if len(clean_km) >= 3:  # Pour éviter de chopper un petit chiffre anodin
                extracted["km"] = clean_km
                
    # Le titre est souvent l'une des premières lignes significatives de la page
    for line in lines[:10]:
        if len(line) > 5 and not any(w in line.lower() for w in ["leboncoin", "pro", "€", "favoris", "partager", "déposer"]):
            extracted["title"] = line
            parts = line.split()
            if len(parts) > 0: extracted["make"] = parts[0]
            if len(parts) > 1: extracted["model"] = parts[1]
            break
            
    return extracted

# Initialisation de la session
if "target_car" not in st.session_state:
    st.session_state["target_car"] = {
        "title": "",
        "make": "",
        "model": "",
        "year": "2018",
        "km": "100000"
    }

st.title("🚗 Switch Auto — Hub & Chasse Miroir Particuliers")
st.caption("Sélectionne une agence, ouvre une annonce, fais Ctrl+A / Ctrl+C et colle le contenu ici !")

# --- BARRE LATÉRALE : LES 11 AGENCES DU SECTEUR ---
st.sidebar.header("🏪 Hub des 11 Agences Concurrentes")
selected_agency_name = st.sidebar.selectbox("Choisir une agence :", list(AGENCES_CONCURRENCE.keys()))
agency_url = AGENCES_CONCURRENCE[selected_agency_name]

st.sidebar.link_button(f"🌐 Ouvrir le catalogue de {selected_agency_name}", agency_url, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Paramétrage de la Cible")
delta_km = st.sidebar.slider("Tolérance delta kilométrage (± en km) :", min_value=50, max_value=10000, value=500, step=50)

# --- INTERFACE PRINCIPALE EN DEUX COLONNES ---
col_left, col_right = st.columns([1.2, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : COPIER-COLLER GLOBAL DE LA PAGE ANNONCE
# ==============================================================================
with col_left:
    st.header("📋 Analyseur par Copier-Coller Global")
    st.write("Sur l'annonce du pro : fais **Ctrl+A** puis **Ctrl+C**, et colle tout ici :")
    
    raw_page_paste = st.text_area("Colle le contenu complet de la page de l'annonce pro :", height=180, placeholder="Colle le texte brut de la page ici...")
    
    if st.button("🪄 Extraire et Préparer le Miroir", type="primary"):
        if raw_page_paste:
            parsed_data = parse_full_ad_text(raw_page_paste)
            st.session_state["target_car"] = parsed_data
            st.success("Extraction réussie ! Vérifie et ajuste les champs ci-dessous si besoin.")
        else:
            st.error("Veuillez coller le texte de la page.")

    st.markdown("---")
    st.subheader("Vérification & Ajustement Rapide")
    
    with st.form("adjust_form"):
        input_title = st.text_input("Titre détecté", value=st.session_state["target_car"]["title"])
        input_make = st.text_input("Marque", value=st.session_state["target_car"]["make"])
        input_model = st.text_input("Modèle", value=st.session_state["target_car"]["model"])
        input_year = st.text_input("Année", value=st.session_state["target_car"]["year"])
        input_km = st.text_input("Kilométrage", value=st.session_state["target_car"]["km"])
        
        if st.form_submit_button("💾 Valider les critères finaux"):
            st.session_state["target_car"] = {
                "title": input_title,
                "make": input_make,
                "model": input_model,
                "year": input_year,
                "km": input_km
            }
            st.success("Critères validés !")

# ==============================================================================
# COLONNE DROITE : RÉSULTATS DU MIRRORING PARTICULIER
# ==============================================================================
with col_right:
    st.header("👤 Mirroring Particuliers (Mandat Simple)")
    
    car = st.session_state["target_car"]
    
    if car["make"]:
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
        ### Paramètres de recherche appliqués :
        * **Cible :** `{make} {model}` ({year_str})
        * **Tranche KM :** `{km_min:,} km` à `{km_max:,} km` (Delta ± {delta_km} km)
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
        💡 **Chasse au Mandat Simple :** En collant tout le texte de la page, l'outil pré-remplit les critères. Tu n'as plus qu'à cliquer pour afficher instantanément le particulier en face !
        """)
    else:
        st.warning("👈 Colle le contenu d'une annonce à gauche et clique sur **Extraire** pour générer les liens.")
