import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import urllib3

# Désactivation des avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="Switch Auto — Global Competitor Matcher",
    page_icon="🚗",
    layout="wide"
)

# Cartographie complète : URL directe du site officiel + secours ID API La Centrale
COMPETITORS = {
    "Transakauto Roncq": {
        "direct_url": "https://annonces.transakauto.com/agence/roncq",
        "dealer_id": "C045809"
    },
    "Transakauto Wambrechies": {
        "direct_url": "https://annonces.transakauto.com/agence/wambrechies",
        "dealer_id": "C045809"
    },
    "Partenaire Auto": {
        "direct_url": "https://www.partenaireauto.fr/vehicules",
        "dealer_id": "C040938"
    },
    "Ewigo Roncq": {
        "direct_url": "https://www.ewigo.com/reseau/ewigo-roncq",
        "dealer_id": "C037105"
    },
    "Ewigo Villeneuve d'Ascq": {
        "direct_url": "https://www.ewigo.com/reseau/ewigo-villeneuve-d-ascq",
        "dealer_id": "C037105"
    },
    "Ewigo Lesquin": {
        "direct_url": "https://www.ewigo.com/reseau/ewigo-lesquin",
        "dealer_id": "C037105"
    },
    "Simplicicar La Madeleine": {
        "direct_url": "https://simplicicar.com/agences/simplicicar-lille-la-madeleine/",
        "dealer_id": "C040938"
    },
    "Via Automobile Roncq": {
        "direct_url": "https://www.viaautomobile.com/agence/roncq",
        "dealer_id": "C038590"
    },
    "Via Automobile Villeneuve d'Ascq": {
        "direct_url": "https://www.viaautomobile.com/agence/villeneuve-d-ascq",
        "dealer_id": "C038590"
    },
    "Vroom Market": {
        "direct_url": "https://www.vroommarket.fr/stock",
        "dealer_id": "C040938"
    },
    "L'Agence Automobilière Wasquehal": {
        "direct_url": "https://agenceauto.com/fr/fr/agences/wasquehal/",
        "dealer_id": "C060915"
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
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

def scrape_direct_site(agency_name, url):
    """Tente de scraper le HTML directement depuis le site propre de l'agence."""
    vehicles = []
    try:
        session = requests.Session()
        res = session.get(url, headers=HEADERS, timeout=7, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("article, div[class*='card'], div[class*='annonce'], div[class*='vehicle'], div[class*='car']")
            
            for card in cards:
                text = card.get_text(" ", strip=True)
                title_el = card.select_one("h1, h2, h3, h4, a[class*='title']")
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                parts = title.split(" ", 2)
                make = parts[0] if len(parts) > 0 else ""
                model = parts[1] if len(parts) > 1 else ""
                
                price_m = re.search(r"(\d+[\s.]?\d*)\s*€", text)
                price = f"{price_m.group(1)} €" if price_m else "Prix N.C."
                
                year_m = re.search(r"\b(20\d{2})\b", text)
                km_m = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", text)
                
                year = year_m.group(1) if year_m else ""
                km_raw = km_m.group(1) if km_m else ""
                km_str = re.sub(r"\D", "", km_raw)
                
                if make and model:
                    vehicles.append({
                        "agency": agency_name,
                        "title": title,
                        "make": make,
                        "model": model,
                        "price": price,
                        "year": year,
                        "km": km_str,
                        "source": "Site Direct",
                        "lbc_url": generate_leboncoin_search_url(make, model, year, km_str),
                        "lacentrale_url": generate_lacentrale_search_url(make, model, year, km_str),
                    })
    except Exception:
        pass
    return vehicles

def fetch_api_fallback(agency_name, dealer_id):
    """Secours API direct quand le site propre est bloqué ou en JavaScript."""
    vehicles = []
    api_url = f"https://pros.lacentrale.fr/api/v1/dealers/{dealer_id}/ads?page=1&pageSize=100"
    try:
        res = requests.get(api_url, headers=HEADERS, timeout=7, verify=False)
        if res.status_code == 200:
            data = res.json()
            items = data.get("items", []) or data.get("ads", [])
            for item in items:
                make = item.get("make", "") or item.get("brand", "")
                model = item.get("model", "")
                version = item.get("version", "")
                full_title = f"{make} {model} {version}".strip()
                
                raw_price = item.get("price", 0)
                price_str = f"{raw_price:,} €".replace(",", " ") if isinstance(raw_price, (int, float)) and raw_price > 0 else "Prix N.C."
                
                year = str(item.get("year", ""))
                km_str = str(item.get("mileage", ""))
                
                vehicles.append({
                    "agency": agency_name,
                    "title": full_title if full_title else f"Véhicule {agency_name}",
                    "make": make if make else full_title.split(" ")[0],
                    "model": model if model else "",
                    "price": price_str,
                    "year": year,
                    "km": km_str,
                    "source": "Catalogue Reseau",
                    "lbc_url": generate_leboncoin_search_url(make, model, year, km_str),
                    "lacentrale_url": generate_lacentrale_search_url(make, model, year, km_str),
                })
    except Exception:
        pass
    return vehicles

@st.cache_data(ttl=1800)
def fetch_all_stocks():
    all_vehicles = []
    global_id = 1
    
    for agency_name, info in COMPETITORS.items():
        # 1. Tentative sur le site direct propre
        agency_vehicles = scrape_direct_site(agency_name, info["direct_url"])
        
        # 2. Si 0 véhicule trouve (site bloque/JS), bascule sur l'API reseau
        if not agency_vehicles and info["dealer_id"]:
            agency_vehicles = fetch_api_fallback(agency_name, info["dealer_id"])
            
        for v in agency_vehicles:
            v["id"] = global_id
            all_vehicles.append(v)
            global_id += 1
            
    return pd.DataFrame(all_vehicles)

# --- INTERFACE ---

st.title("🚗 Switch Auto — Global Competitor Matcher")
st.caption("Centralisation multi-sources (Sites directs & Catalogues réels)")

st.sidebar.header("1. Panneau de Contrôle")
if st.sidebar.button("🔄 Lancer l'extraction complète", type="primary"):
    st.cache_data.clear()

with st.spinner("Extraction en cours sur les sites directs des 11 agences..."):
    df_global = fetch_all_stocks()

selected_agency = st.sidebar.selectbox(
    "Filtrer par agence :", 
    ["Toutes les agences"] + list(COMPETITORS.keys())
)

if len(df_global) > 0:
    if selected_agency != "Toutes les agences":
        df_filtered = df_global[df_global["agency"] == selected_agency].reset_index(drop=True)
    else:
        df_filtered = df_global
else:
    df_filtered = pd.DataFrame()

st.subheader(f"📊 Marché consolidé ({len(df_filtered)} véhicules récupérés)")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Véhicules Référencés")
    
    if len(df_filtered) > 0:
        selected_title = st.selectbox(
            "Sélectionner un véhicule :", 
            df_filtered["title"].tolist()
        )
        
        car = df_filtered[df_filtered["title"] == selected_title].iloc[0]
        
        km_disp = f"{int(car['km']):,} km" if str(car['km']).isdigit() and car['km'] != "" else "N.C."
        year_disp = car['year'] if car['year'] != "" else "N.C."
        source_disp = car.get('source', 'Direct')
        
        st.info(f"**Agence :** {car['agency']} ({source_disp})\n\n**Modèle :** {car['title']}\n\n**Prix Pro :** {car['price']}\n\n**Année :** {year_disp}\n\n**Kilométrage :** {km_disp}")
        
        st.dataframe(
            df_filtered[["agency", "title", "price", "year", "km", "source"]], 
            use_container_width=True, 
            height=320
        )
    else:
        st.warning("Aucun véhicule extrait. Cliquez sur '🔄 Lancer l'extraction complète' dans la barre latérale.")

with col_right:
    st.markdown("### 🔍 Recherche Miroirs Particuliers")
    
    if len(df_filtered) > 0:
        st.write("Vérification si le propriétaire vend l'auto en direct sur d'autres plateformes :")
        
        y_min = f"{int(car['year'])-1}" if str(car['year']).isdigit() and car['year'] != "" else ""
        y_max = f"{int(car['year'])+1}" if str(car['year']).isdigit() else ""
        km_min = f"{max(0, int(car['km'])-5000):,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        km_max = f"{int(car['km'])+5000:,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        
        st.markdown(f"""
        **Filtres générés :**
        * Véhicule : `{car['make']} {car['model']}`
        * Fenêtre Année : `{y_min} - {y_max}`
        * Fenêtre KM : `{km_min}` à `{km_max}` km
        """)
        
        st.markdown("---")
        
        col_lbc, col_lc = st.columns(2)
        with col_lbc:
            st.link_button("🟠 Recherche LeBonCoin", car["lbc_url"], use_container_width=True)
        with col_lc:
            st.link_button("🔵 Recherche La Centrale", car["lacentrale_url"], use_container_width=True)

        st.success("""
        **💡 Prospection :**  
        Si le véhicule sort sur LeBonCoin au nom d'un particulier, tu as le mandat non-exclusif !
        """)
