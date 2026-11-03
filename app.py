import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import urllib3

# Désactivation des avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Global Competitor Matcher",
    page_icon="🚗",
    layout="wide"
)

# Liste des 11 concurrents du secteur lillois et leurs URLs vitrines
COMPETITORS = {
    "Transakauto Roncq": "https://pros.lacentrale.fr/C045809",
    "Transakauto Wambrechies": "https://pros.lacentrale.fr/C045809",
    "Partenaire Auto": "https://pros.lacentrale.fr/C040938",
    "Ewigo Roncq": "https://pros.lacentrale.fr/C037105",
    "Ewigo Villeneuve d'Ascq": "https://pros.lacentrale.fr/C037105",
    "Ewigo Lesquin": "https://pros.lacentrale.fr/C037105",
    "Simplicicar La Madeleine": "https://pros.lacentrale.fr/C040938",
    "Via Automobile Roncq": "https://pros.lacentrale.fr/C038590",
    "Via Automobile Villeneuve d'Ascq": "https://pros.lacentrale.fr/C038590",
    "Vroom Market": "https://pros.lacentrale.fr/C040938",
    "L'Agence Automobilière Wasquehal": "https://pros.lacentrale.fr/C060915",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def generate_lacentrale_search_url(make, model, year, km):
    base_url = "https://www.lacentrale.fr/listing"
    year_min = max(2000, int(year) - 1) if year and str(year).isdigit() else ""
    year_max = int(year) + 1 if year and str(year).isdigit() else ""
    km_min = max(0, int(km) - 5000) if km and str(km).isdigit() else ""
    km_max = int(km) + 5000 if km and str(km).isdigit() else ""
    
    params = {
        "makesModelsCommercialNames": f"{make}:{model}",
        "yearMin": year_min,
        "yearMax": year_max,
        "mileageMin": km_min,
        "mileageMax": km_max,
        "zipCodes": "59000",
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def generate_leboncoin_search_url(make, model, year, km):
    query = f"{make} {model}".strip()
    encoded_query = urllib.parse.quote(query)
    lbc_url = f"https://www.leboncoin.fr/recherche?category=2&text={encoded_query}&locations=r_17"
    if year and str(year).isdigit():
        lbc_url += f"&regdate={int(year)-1}-{int(year)+1}"
    if km and str(km).isdigit():
        lbc_url += f"&mileage={max(0, int(km)-5000)}-{int(km)+5000}"
    return lbc_url

@st.cache_data(ttl=1800)
def fetch_all_competitors_stock():
    """Extrait uniquement les vraies annonces réelles du Web sans aucune donnée factice."""
    all_vehicles = []
    global_id = 1
    
    for agency_name, target_url in COMPETITORS.items():
        try:
            session = requests.Session()
            response = session.get(target_url, headers=HEADERS, timeout=8, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("div[class*='adCard'], div[class*='searchCard'], div[class*='annonce'], article")
                
                for card in cards:
                    text_block = card.get_text(" ", strip=True)
                    title_elem = card.select_one("h2, h3, span[class*='title'], a[class*='title']")
                    if not title_elem:
                        continue
                    
                    full_title = title_elem.get_text(strip=True)
                    parts = full_title.split(" ", 2)
                    make = parts[0] if len(parts) > 0 else ""
                    model = parts[1] if len(parts) > 1 else ""
                    
                    price_match = re.search(r"(\d+[\s.]?\d*)\s*€", text_block)
                    price = f"{price_match.group(1)} €" if price_match else "Prix N.C."
                    
                    year_match = re.search(r"\b(20\d{2})\b", text_block)
                    km_match = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", text_block)
                    
                    year = year_match.group(1) if year_match else ""
                    km_raw = km_match.group(1) if km_match else ""
                    km_str = re.sub(r"\D", "", km_raw)
                    
                    if make and model:
                        all_vehicles.append({
                            "id": global_id,
                            "agency": agency_name,
                            "title": full_title,
                            "make": make,
                            "model": model,
                            "price": price,
                            "year": year,
                            "km": km_str,
                            "lbc_url": generate_leboncoin_search_url(make, model, year, km_str),
                            "lacentrale_url": generate_lacentrale_search_url(make, model, year, km_str),
                        })
                        global_id += 1
        except Exception:
            pass
            
    return pd.DataFrame(all_vehicles)

# --- INTERFACE UTILISATEUR STREAMLIT ---

st.title("🚗 Switch Auto — Global Competitor Matcher")
st.caption("Centralisation réelle des stocks concurrents & détection des mandats non-exclusifs")

# Sidebar: Filtres globaux
st.sidebar.header("1. Filtres du Marché")
if st.sidebar.button("🔄 Lancer l'extraction réelle", type="primary"):
    st.cache_data.clear()

df_global = fetch_all_competitors_stock()

selected_agency_filter = st.sidebar.selectbox(
    "Filtrer par agence :", 
    ["Toutes les agences"] + list(COMPETITORS.keys())
)

if len(df_global) > 0:
    if selected_agency_filter != "Toutes les agences":
        df_filtered = df_global[df_global["agency"] == selected_agency_filter].reset_index(drop=True)
    else:
        df_filtered = df_global
else:
    df_filtered = pd.DataFrame()

st.subheader(f"📊 Marché réel consolidé ({len(df_filtered)} véhicules récupérés)")

# DISPOSITION EN 2 COLONNES
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Sélection Véhicule Concurrent")
    
    if len(df_filtered) > 0:
        selected_title = st.selectbox(
            "Choisissez une annonce parmi les véhicules extraits :", 
            df_filtered["title"].tolist()
        )
        
        car = df_filtered[df_filtered["title"] == selected_title].iloc[0]
        
        km_display = f"{int(car['km']):,} km" if str(car['km']).isdigit() and car['km'] != "" else "N.C."
        year_display = car['year'] if car['year'] != "" else "N.C."
        
        st.info(f"""
        **Agence :** {car['agency']}  
        **Modèle :** {car['title']}  
        **Prix Pro :** {car['price']}  
        **Année :** {year_display}  
        **Kilométrage :** {km_display}  
        """)
        
        st.dataframe(
            df_filtered[["agency", "title", "price", "year", "km"]], 
            use_container_width=True, 
            height=320
        )
    else:
        st.warning("Aucun véhicule extrait pour cette sélection. Cliquez sur 'Lancer l'extraction réelle' pour rafraîchir les données.")

with col_right:
    st.markdown("### 🔍 Recherche Miroirs (Particuliers)")
    
    if len(df_filtered) > 0:
        st.write("Génération des liens de recherche ciblés pour vérifier si le propriétaire vend en parallèle :")
        
        st.markdown(f"""
        **Paramètres cibles :**
        * Véhicule : `{car['make']} {car['model']}`
        * Année : `{int(car['year'])-1 if str(car['year']).isdigit() else ''} - {int(car['year'])+1 if str(car['year']).isdigit() else ''}`
        * Kilométrage : `{max(0, int(car['km'])-5000) if str(car['km']).isdigit() else ''}` à `{int(car['km'])+5000 if str(car['km']).isdigit() else ''}` km
        """)
        
        st.markdown("---")
        
        col_lbc, col_lc = st.columns(2)
        with col_lbc:
            st.link_button("🟠 Rechercher sur LeBonCoin", car["lbc_url"], use_container_width=True)
        with col_lc:
            st.link_button("🔵 Rechercher sur La Centrale", car["lacentrale_url"], use_container_width=True)

        st.success("""
        **💡 Stratégie Switch Auto :**  
        Si l'annonce apparaît moins chère sur LeBonCoin par un particulier, c'est un mandat non-exclusif à prospecter immédiatement !
        """)
