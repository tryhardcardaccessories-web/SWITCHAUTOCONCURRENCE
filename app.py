import streamlit as st
import pandas as pd
import urllib.parse
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — CRM Prospection Miroir",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Switch Auto — Sourcing Pros & Matcher Miroir Automatique")
st.caption("Filtres MyTrax : Roncq + 30 km | Année ≥ 2006 | KM ≤ 250 000")

# --- CONSTANTES MYTRAX ---
SECTEUR_LBC = "Roncq_59223__30000"

def generate_lbc_pro_feed_url():
    """Lien direct vers la recherche globale LeBonCoin Pros filtrée MyTrax."""
    return (
        f"https://www.leboncoin.fr/recherche?"
        f"category=2"
        f"&owner_type=pro"
        f"&regdate=2006-max"
        f"&mileage=min-250000"
        f"&locations={SECTEUR_LBC}"
    )

def parse_lbc_pro_page(raw_text):
    """Parse le copier-coller de la recherche Pro pour extraire les annonces dans le tableau."""
    vehicles = []
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        price_match = re.search(r"(\d+[\s.]?\d*)\s*€", line)
        
        if price_match:
            price_str = f"{price_match.group(1)} €"
            
            # Recherche du titre du véhicule
            title = ""
            for offset in range(1, 6):
                if i - offset >= 0:
                    candidate = lines[i - offset]
                    if not re.search(r"€|Voitures|aujourd'hui|hier|Filtres|annonces|Tri :|\d+\s*€|Baisse de prix", candidate, re.IGNORECASE) and len(candidate) > 3:
                        title = candidate
                        break
            
            if title and title != "Véhicule inconnu":
                parts = title.split()
                make = parts[0] if len(parts) > 0 else "Auto"
                model = parts[1] if len(parts) > 1 else ""
                
                # Extraction Année et KM dans les lignes adjacentes
                year = "2015"  # Valeur par défaut si non affiché sur la carte
                km_str = "100000"
                
                for check_idx in range(max(0, i-4), min(len(lines), i+4)):
                    year_m = re.search(r"\b(20[0-2]\d)\b", lines[check_idx])
                    km_m = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", lines[check_idx], re.IGNORECASE)
                    if year_m:
                        year = year_m.group(1)
                    if km_m:
                        km_str = re.sub(r"\D", "", km_m.group(1))

                # URL de recherche ciblée Pro (Loupe Pro)
                query_pro = urllib.parse.quote(f"{title}".strip())
                pro_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text={query_pro}&locations={SECTEUR_LBC}"

                vehicles.append({
                    "title": title,
                    "make": make,
                    "model": model,
                    "price": price_str,
                    "year": year,
                    "km": km_str,
                    "pro_url": pro_url
                })
        i += 1
        
    return pd.DataFrame(vehicles)

# Initialisation du stockage de la session
if "pro_inventory" not in st.session_state:
    st.session_state["pro_inventory"] = pd.DataFrame()

# --- BARRE LATÉRALE : IMPORT DU FEED PRO ---
st.sidebar.header("1. Sourcing Recherche Pros")
st.sidebar.markdown(f"[🔍 Ouvrir le Feed Pros LeBonCoin (Roncq +30km)]({generate_lbc_pro_feed_url()})")

raw_paste = st.sidebar.text_area(
    "Copie-colle le texte de la page LeBonCoin Pros ici (Ctrl+A puis Ctrl+C) :",
    height=180,
    placeholder="Fais Ctrl+A puis Ctrl+C sur la page de recherche LeBonCoin Pros et colle ici..."
)

if st.sidebar.button("📥 Extraire et charger la liste", type="primary"):
    if raw_paste:
        df_extracted = parse_lbc_pro_page(raw_paste)
        if len(df_extracted) > 0:
            st.session_state["pro_inventory"] = df_extracted
            st.sidebar.success(f"🎉 {len(df_extracted)} annonces pros chargées dans la liste !")
        else:
            st.sidebar.error("Aucune annonce détectée. Veille à bien sélectionner tout le texte de la page.")
    else:
        st.sidebar.error("Colle d'abord le texte de la page.")

if st.sidebar.button("🗑️ Vider la liste"):
    st.session_state["pro_inventory"] = pd.DataFrame()
    st.rerun()

df_pros = st.session_state["pro_inventory"]

# --- INTERFACE EN 2 COLONNES ---
col_list, col_match = st.columns([1.2, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : LISTE DES ANNONCES PROS (STYLE CRM / AUTO SCOUT)
# ==============================================================================
with col_list:
    st.header("📋 Annonces Pros en cours (Secteur Roncq)")
    
    if len(df_pros) > 0:
        st.write("Sélectionne une annonce pro dans la liste pour générer ses miroirs :")
        
        # Menu déroulant de sélection rapide
        selected_idx = st.selectbox(
            "👉 Choisir un véhicule à analyser :",
            range(len(df_pros)),
            format_func=lambda x: f"{df_pros.iloc[x]['title']} | {df_pros.iloc[x]['price']} | {df_pros.iloc[x]['year']} | {df_pros.iloc[x]['km']} km"
        )
        
        selected_car = df_pros.iloc[selected_idx]
        
        # Fiche du véhicule Pro sélectionné avec la loupe vers l'annonce pro
        st.info(f"""
        **🚗 Véhicule Pro Sélectionné :** {selected_car['title']}  
        **Prix affiché :** {selected_car['price']}  
        **Année :** {selected_car['year']} | **Kilométrage :** {selected_car['km']} km  
        """)
        
        st.link_button(f"🔍 Ouvrir la recherche Pro pour {selected_car['make']} {selected_car['model']}", selected_car['pro_url'], use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📊 Liste Globale")
        st.dataframe(df_pros[["title", "price", "year", "km"]], use_container_width=True, height=250)
        
    else:
        st.info("👈 **Comment procéder :**\n1. Clique sur le lien dans le menu de gauche pour ouvrir la recherche LeBonCoin Pros.\n2. Fais `Ctrl+A` puis `Ctrl+C` sur la page.\n3. Colle le texte dans la zone de gauche et clique sur **📥 Extraire et charger la liste**.")

# ==============================================================================
# COLONNE DROITE : RECHERCHE MIROIR PARTICULIER (AUTOMATIQUE)
# ==============================================================================
with col_match:
    st.header("👤 Recherche Miroir Particulier")
    
    if len(df_pros) > 0:
        make = selected_car["make"]
        model = selected_car["model"]
        year_val = int(selected_car["year"]) if str(selected_car["year"]).isdigit() else 2015
        km_val = int(selected_car["km"]) if str(selected_car["km"]).isdigit() else 100000
        
        # Plages de tolérance (+/- 1 an et +/- 5 000 km)
        year_min = max(2006, year_val - 1)
        year_max = year_val + 1
        km_min = max(0, km_val - 5000)
        km_max = min(250000, km_val + 5000)
        
        query_part = urllib.parse.quote(f"{make} {model}".strip())
        
        # URL LeBonCoin Particuliers ciblée
        lbc_part_url = (
            f"https://www.leboncoin.fr/recherche?"
            f"category=2"
            f"&owner_type=private"
            f"&text={query_part}"
            f"&regdate={year_min}-{year_max}"
            f"&mileage={km_min}-{km_max}"
            f"&locations={SECTEUR_LBC}"
        )
        
        # URL La Centrale Particuliers
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "yearMin": year_min,
            "yearMax": year_max,
            "mileageMin": km_min,
            "mileageMax": km_max,
            "zipCodes": "59220,59000,59100,59200",
        }
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.success(f"🎯 **Miroir prêt pour :** {make} {model}")
        
        st.markdown(f"""
        **Critères ciblés (Particuliers Roncq +30 km) :**
        * **Modèle :** `{make} {model}`
        * **Fenêtre Année :** `{year_min} - {year_max}`
        * **Fenêtre KM :** `{km_min:,}` à `{km_max:,}` km
        """.replace(",", " "))
        
        st.markdown("---")
        
        st.link_button(f"🟠 🔍 Lancer Miroir LeBonCoin (Particuliers)", lbc_part_url, use_container_width=True, type="primary")
        st.write("")
        st.link_button(f"🔵 🔍 Lancer Miroir La Centrale (Particuliers)", lc_part_url, use_container_width=True)
        
        st.info("""
        **💡 Astuce Prospection :**  
        Si le véhicule sort sur LeBonCoin au nom d'un particulier à un prix inférieur à l'annonce pro, tu as ton mandat non-exclusif !
        """)
    else:
        st.warning("Charge d'abord la liste d'annonces pros à gauche pour activer le matcher miroir automatique.")
