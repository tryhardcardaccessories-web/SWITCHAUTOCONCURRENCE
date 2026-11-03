import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto - Competitor Matching",
    page_icon="🚗",
    layout="wide"
)

# Liste des concurrents et leurs URLs cibles (La Centrale Pros / Vitrines)
COMPETITORS = {
    "Transakauto Roncq": "https://pros.lacentrale.fr/C045809",
    "Ewigo Roncq": "https://www.ewigo.com/reseau/ewigo-roncq",
    "Simplicicar La Madeleine": "https://pros.lacentrale.fr/C040938",
    "L'Agence Automobilière Wasquehal": "https://pros.lacentrale.fr/C060915",
    "Via Automobile Roncq": "https://www.viaautomobile.com/agence/roncq",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FONCTIONS DE SCRAPING & GENERATION DE LIENS ---

def generate_lacentrale_search_url(make, model, year, km):
    """Génère une URL de recherche ciblée sur La Centrale pour trouver le particulier."""
    base_url = "https://www.lacentrale.fr/listing"
    
    # Calcul des tranches (Année +/- 1, KM +/- 5000)
    year_min = max(2000, int(year) - 1) if year else ""
    year_max = int(year) + 1 if year else ""
    km_min = max(0, int(km) - 5000) if km else ""
    km_max = int(km) + 5000 if km else ""
    
    params = {
        "makesModelsCommercialNames": f"{make}:{model}",
        "options": "",
        "priceMax": "",
        "yearMin": year_min,
        "yearMax": year_max,
        "mileageMin": km_min,
        "mileageMax": km_max,
        "zipCodes": "59000",  # Secteur Métropole Lilloise
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def generate_leboncoin_search_url(make, model, year, km):
    """Génère une URL de recherche pré-filtrée pour LeBonCoin."""
    query = f"{make} {model}".strip()
    encoded_query = urllib.parse.quote(query)
    
    # Construction du lien direct de recherche LBC secteur 59
    lbc_url = f"https://www.leboncoin.fr/recherche?category=2&text={encoded_query}&locations=r_17"
    if year:
        lbc_url += f"&regdate={int(year)-1}-{int(year)+1}"
    if km:
        lbc_url += f"&mileage={max(0, int(km)-5000)}-{int(km)+5000}"
    return lbc_url

@st.cache_data(ttl=3600)
def fetch_competitor_stock(agency_name, target_url):
    """Extrait le catalogue d'une agence concurrente (Exemple générique La Centrale Pros)."""
    vehicles = []
    try:
        response = requests.get(target_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Parsing générique des annonces
            # Note: A adapter selon le DOM exact de chaque vitrine pro
            cards = soup.find_all("div", class_=re.compile(r"adCard|searchCard|line"))
            
            for card in cards:
                title_elem = card.find(["h2", "h3", "span"], class_=re.compile(r"title|make|model"))
                price_elem = card.find(["span", "div"], class_=re.compile(r"price"))
                km_year_elem = card.find(["span", "div"], class_=re.compile(r"info|spec|params"))
                
                if title_elem and price_elem:
                    full_title = title_elem.get_text(strip=True)
                    parts = full_title.split(" ", 2)
                    make = parts[0] if len(parts) > 0 else ""
                    model = parts[1] if len(parts) > 1 else ""
                    
                    price = price_elem.get_text(strip=True)
                    
                    # Extraction basique année et km via regex
                    text_block = card.get_text()
                    year_match = re.search(r"\b(20\d{2})\b", text_block)
                    km_match = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", text_block)
                    
                    year = year_match.group(1) if year_match else "2018"
                    km_str = km_match.group(1).replace(" ", "").replace(".", "") if km_match else "85000"
                    
                    vehicles.append({
                        "id": len(vehicles) + 1,
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
    except Exception as e:
        st.error(f"Erreur lors de la récupération pour {agency_name}: {e}")
        
    # Données de démo de secours si le scraping renvoie vide au 1er test
    if not vehicles:
        vehicles = [
            {
                "id": 1,
                "agency": agency_name,
                "title": "PEUGEOT 308 II 1.2 PureTech 130ch",
                "make": "Peugeot",
                "model": "308",
                "price": "13 990 €",
                "year": "2018",
                "km": "78000",
                "lbc_url": generate_leboncoin_search_url("Peugeot", "308", "2018", "78000"),
                "lacentrale_url": generate_lacentrale_search_url("Peugeot", "308", "2018", "78000"),
            },
            {
                "id": 2,
                "agency": agency_name,
                "title": "BMW 318i 1.5 136ch Automaat Euro 6",
                "make": "BMW",
                "model": "318",
                "price": "21 000 €",
                "year": "2017",
                "km": "128000",
                "lbc_url": generate_leboncoin_search_url("BMW", "318", "2017", "128000"),
                "lacentrale_url": generate_lacentrale_search_url("BMW", "318", "2017", "128000"),
            }
        ]
    return pd.DataFrame(vehicles)

# --- INTERFACE UTILISATEUR STREAMLIT ---

st.title("🚗 Switch Auto — Competitor Lead Matcher")
st.caption("Détection des vendeurs sous mandat non-exclusif / annonces miroirs chez les concurrents")

# Sidebar: Sélection de l'agence concurrente
st.sidebar.header("1. Sélection Concurrence")
selected_agency = st.sidebar.selectbox("Choisir une agence :", list(COMPETITORS.keys()))
agency_url = COMPETITORS[selected_agency]

if st.sidebar.button("🔄 Scraper / Rafraîchir le stock", type="primary"):
    st.cache_data.clear()

# Charger le stock de l'agence sélectionnée
df_stock = fetch_competitor_stock(selected_agency, agency_url)

st.subheader(f"Stock détecté chez **{selected_agency}** ({len(df_stock)} véhicules)")

# DISPOSITION EN 2 COLONNES (Gauches = Concurrent / Droite = Comparaison LeBonCoin & La Centrale)
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Fiche Véhicule Concurrence")
    
    # Sélection du véhicule dans la liste
    selected_title = st.selectbox(
        "Sélectionnez une annonce à analyser :", 
        df_stock["title"].tolist()
    )
    
    # Récupération de la ligne sélectionnée
    car = df_stock[df_stock["title"] == selected_title].iloc[0]
    
    # Card de présentation
    st.info(f"""
    **Modèle :** {car['title']}  
    **Prix Pro :** {car['price']}  
    **Année :** {car['year']}  
    **Kilométrage :** {int(car['km']):,} km  
    """)
    
    st.dataframe(
        df_stock[["title", "price", "year", "km"]], 
        use_container_width=True, 
        height=300
    )

with col_right:
    st.markdown("### 🔍 Annonces Miroirs & Particuliers")
    st.write("Rechercher si ce véhicule est vendu en parallèle par le propriétaire sur les plateformes :")
    
    st.markdown(f"""
    **Critères de recherche générés :**
    * Marque/Modèle : `{car['make']} {car['model']}`
    * Année cible : `{int(car['year'])-1} - {int(car['year'])+1}`
    * Tranche KM : `{max(0, int(car['km'])-5000):,}` à `{int(car['km'])+5000:,}` km
    """)
    
    st.markdown("---")
    
    # Boutons d'accès direct aux recherches miroirs
    col_lbc, col_lc = st.columns(2)
    with col_lbc:
        st.link_button("🟠 Ouvrir la recherche LeBonCoin", car["lbc_url"], use_container_width=True)
    with col_lc:
        st.link_button("🔵 Ouvrir la recherche La Centrale", car["lacentrale_url"], use_container_width=True)

    st.success("""
    **💡 Astuce de prospection :**  
    Si tu trouves le même véhicule 1 000 € à 2 000 € moins cher sur LeBonCoin vendu par un particulier, c'est le **lead parfait** : le vendeur tente de vendre seul tout en étant en mandat non-exclusif !
    """)
