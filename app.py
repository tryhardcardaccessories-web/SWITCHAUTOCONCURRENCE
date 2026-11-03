import streamlit as st
import pandas as pd
import urllib.parse
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Matcher Miroir Souple",
    page_icon="🚗",
    layout="wide"
)

# --- CONSTANTES MYTRAX ---
SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km

def parse_lbc_paste(raw_text):
    """Parseur intelligent et stable pour traiter le copier-coller de la page pro."""
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
                year = "2015"
                km_str = "100000"
                
                for check_idx in range(max(0, i-4), min(len(lines), i+4)):
                    year_m = re.search(r"\b(20[0-2]\d)\b", lines[check_idx])
                    km_m = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", lines[check_idx], re.IGNORECASE)
                    if year_m:
                        year = year_m.group(1)
                    if km_m:
                        km_str = re.sub(r"\D", "", km_m.group(1))

                query_pro = urllib.parse.quote(f"{title}".strip())
                pro_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=pro&text={query_pro}&locations={SECTEUR_LBC}"

                vehicles.append({
                    "title": title,
                    "make": make,
                    "model": model,
                    "price": price_str,
                    "year": year,
                    "km": km_str,
                    "url_pro": pro_url
                })
        i += 1
        
    return pd.DataFrame(vehicles)

# Initialisation du stockage de session
if "pro_inventory" not in st.session_state:
    st.session_state["pro_inventory"] = pd.DataFrame()

if "selected_car" not in st.session_state:
    st.session_state["selected_car"] = None

st.title("🚗 Switch Auto — Matcher Miroir Souple (Anti-Bug)")
st.caption("Filtres MyTrax : Roncq + 30 km | Tolérance delta année & kilométrage")

# --- BARRE LATÉRALE : IMPORT DU STOCK PRO ---
st.sidebar.header("1. Importer les annonces Pros")
st.sidebar.markdown("[🔍 Ouvrir le flux Pros LeBonCoin (Roncq +30km)](https://www.leboncoin.fr/recherche?category=2&owner_type=pro&regdate=2006-max&mileage=min-250000&locations=Roncq_59223__30000)")

raw_paste = st.sidebar.text_area(
    "Copie-colle le texte de la page LeBonCoin Pros ici (Ctrl+A puis Ctrl+C) :",
    height=200,
    placeholder="Fais Ctrl+A puis Ctrl+C sur la page de recherche LeBonCoin Pros et colle ici..."
)

if st.sidebar.button("📥 Charger le tableau", type="primary"):
    if raw_paste:
        df_extracted = parse_lbc_paste(raw_paste)
        if len(df_extracted) > 0:
            st.session_state["pro_inventory"] = df_extracted
            st.sidebar.success(f"🎉 {len(df_extracted)} annonces chargées !")
        else:
            st.sidebar.error("Aucune annonce détectée. Vérifie ton copier-coller.")
    else:
        st.sidebar.error("Colle d'abord le texte de la page.")

if st.sidebar.button("🗑️ Vider la liste"):
    st.session_state["pro_inventory"] = pd.DataFrame()
    st.session_state["selected_car"] = None
    st.rerun()

df_pros = st.session_state["pro_inventory"]

# --- INTERFACE EN 2 COLONNES ---
col_list, col_match = st.columns([1.3, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : TABLEAU DES ANNONCES PROS
# ==============================================================================
with col_list:
    st.header("📋 Annonces Pros du Secteur (Roncq +30 km)")
    
    if len(df_pros) > 0:
        st.write("Clique sur **« 🔍 Miroir »** sur la ligne du véhicule à analyser :")
        
        for idx, row in df_pros.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 2])
                with c1:
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"[🔗 Voir Pro]({row['url_pro']})")
                with c2:
                    st.write(f"💰 {row['price']}")
                with c3:
                    st.write(f"📅 {row['year']}")
                with c4:
                    st.write(f"🛣️ {row['km']} km")
                with c5:
                    if st.button("🔍 Miroir", key=f"btn_{idx}", type="secondary"):
                        st.session_state["selected_car"] = row
                        st.rerun()
                st.markdown("---")
    else:
        st.info("👈 **Mode d'emploi :**\n1. Ouvre le lien pro dans la barre latérale.\n2. Fais `Ctrl+A` puis `Ctrl+C` sur la page.\n3. Colle le tout à gauche et clique sur **Charger le tableau**.")

# ==============================================================================
# COLONNE DROITE : FENÊTRE MIROIR PARTICULIERS ( AVEC DELTA )
# ==============================================================================
with col_match:
    st.header("👤 Recherche Miroir Particuliers")
    
    car = st.session_state["selected_car"]
    
    if car is not None:
        make = car["make"]
        model = car["model"]
        
        # Sécurisation des valeurs numériques pour appliquer le delta
        year_val = int(car["year"]) if str(car["year"]).isdigit() else 2015
        km_val = int(car["km"]) if str(car["km"]).isdigit() else 100000
        
        # Application du delta (Tolérance +/- 1 an et +/- 5000 km pour ne rien rater)
        year_min = max(2006, year_val - 1)
        year_max = year_val + 1
        km_min = max(0, km_val - 5000)
        km_max = km_val + 5000
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # URL LeBonCoin Particuliers avec delta
        lbc_part_url = (
            f"https://www.leboncoin.fr/recherche?"
            f"category=2"
            f"&owner_type=private"
            f"&text={query_encoded}"
            f"&regdate={year_min}-{year_max}"
            f"&mileage={km_min}-{km_max}"
            f"&locations={SECTEUR_LBC}"
        )
        
        # URL La Centrale Particuliers avec delta
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "yearMin": year_min,
            "yearMax": year_max,
            "mileageMin": km_min,
            "mileageMax": km_max,
            "zipCodes": "59220,59000,59100,59200",
        }
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.success(f"🎯 **Cible sélectionnée :** {car['title']}")
        
        st.markdown(f"""
        **Critères avec delta appliqués (Particuliers Roncq +30 km) :**
        * **Modèle :** `{make} {model}`
        * **Tranche d'Année :** `{year_min} - {year_max}`
        * **Tranche KM :** `{km_min:,}` à `{km_max:,}` km
        """.replace(",", " "))
        
        st.markdown("---")
        
        st.link_button(
            f"🟠 🔍 Lancer Miroir LeBonCoin (Particuliers)", 
            lbc_part_url, 
            use_container_width=True, 
            type="primary"
        )
        
        st.write("")
        
        st.link_button(
            f"🔵 🔍 Lancer Miroir La Centrale (Particuliers)", 
            lc_part_url, 
            use_container_width=True
        )
        
        st.info("""
        **💡 Action Prospection :**  
        Ce delta souple te permet de tomber immédiatement sur l'annonce du particulier même si son kilométrage affiché varie de quelques milliers de kilomètres !
        """)
    else:
        st.warning("👈 Clique sur le bouton **« 🔍 Miroir »** à côté d'une annonce pro dans le tableau de gauche pour activer les liens miroirs ici.")
