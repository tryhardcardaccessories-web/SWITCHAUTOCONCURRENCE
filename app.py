import streamlit as st
import pandas as pd
import requests
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

# Registre des identifiants pros des agences cibles
COMPETITORS = {
    "Transakauto Roncq": "C045809",
    "Transakauto Wambrechies": "C045809",
    "Partenaire Auto": "C040938",
    "Ewigo Roncq": "C037105",
    "Ewigo Villeneuve d'Ascq": "C037105",
    "Ewigo Lesquin": "C037105",
    "Simplicicar La Madeleine": "C040938",
    "Via Automobile Roncq": "C038590",
    "Via Automobile Villeneuve d'Ascq": "C038590",
    "Vroom Market": "C040938",
    "L'Agence Automobilière Wasquehal": "C060915",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

def generate_lacentrale_search_url(make, model, year, km):
    base_url = "https://www.lacentrale.fr/listing"
    year_min = max(2000, int(year) - 1) if str(year).isdigit() and year else ""
    year_max = int(year) + 1 if str(year).isdigit() and year else ""
    km_min = max(0, int(km) - 5000) if str(km).isdigit() and km else ""
    km_max = int(km) + 5000 if str(km).isdigit() and km else ""
    
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
    if str(year).isdigit() and year:
        lbc_url += f"&regdate={int(year)-1}-{int(year)+1}"
    if str(km).isdigit() and km:
        lbc_url += f"&mileage={max(0, int(km)-5000)}-{int(km)+5000}"
    return lbc_url

@st.cache_data(ttl=1800)
def fetch_all_competitors_stock():
    all_vehicles = []
    global_id = 1
    session = requests.Session()
    
    for agency_name, dealer_id in COMPETITORS.items():
        # Appel sur les endpoints JSON publics des stocks
        api_url = f"https://pros.lacentrale.fr/api/v1/dealers/{dealer_id}/ads?page=1&pageSize=100"
        try:
            res = session.get(api_url, headers=HEADERS, timeout=8, verify=False)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", []) or data.get("ads", []) or data.get("vehicles", [])
                
                for item in items:
                    make = str(item.get("make", "") or item.get("brand", "") or "").strip()
                    model = str(item.get("model", "") or "").strip()
                    version = str(item.get("version", "") or item.get("commercialName", "") or "").strip()
                    
                    full_title = f"{make} {model} {version}".strip()
                    if not full_title:
                        full_title = f"Véhicule {agency_name}"
                    
                    raw_price = item.get("price", 0)
                    price_str = f"{raw_price:,} €".replace(",", " ") if isinstance(raw_price, (int, float)) and raw_price > 0 else "Prix N.C."
                    
                    year = str(item.get("year", "") or item.get("regDate", ""))[:4]
                    km_val = item.get("mileage", "") or item.get("km", "")
                    km_str = str(km_val)
                    
                    all_vehicles.append({
                        "id": global_id,
                        "agency": agency_name,
                        "title": full_title,
                        "make": make if make else (full_title.split()[0] if full_title.split() else ""),
                        "model": model if model else (full_title.split()[1] if len(full_title.split()) > 1 else ""),
                        "price": price_str,
                        "year": year,
                        "km": km_str,
                        "lbc_url": generate_leboncoin_search_url(make, model, year, km_str),
                        "lacentrale_url": generate_lacentrale_search_url(make, model, year, km_str),
                    })
                    global_id += 1
        except Exception:
            pass
            
    return pd.DataFrame(all_vehicles)

# --- INTERFACE STREAMLIT ---

st.title("🚗 Switch Auto — Global Competitor Matcher")
st.caption("Centralisation exhaustive des stocks concurrents & recherche de mandats non-exclusifs")

st.sidebar.header("1. Actions")
if st.sidebar.button("🔄 Lancer l'extraction réelle", type="primary"):
    st.cache_data.clear()

with st.spinner("Récupération directe des stocks en cours..."):
    df_global = fetch_all_competitors_stock()

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

st.subheader(f"📊 Marché consolidé ({len(df_filtered)} véhicules en stock)")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Catalogue Concurrence")
    
    if len(df_filtered) > 0:
        selected_title = st.selectbox(
            "Sélectionner une annonce :", 
            df_filtered["title"].tolist()
        )
        
        car = df_filtered[df_filtered["title"] == selected_title].iloc[0]
        
        km_disp = f"{int(car['km']):,} km" if str(car['km']).isdigit() and car['km'] != "" else "N.C."
        year_disp = car['year'] if car['year'] != "" else "N.C."
        
        st.info(f"**Agence :** {car['agency']}\n\n**Modèle :** {car['title']}\n\n**Prix Pro :** {car['price']}\n\n**Année :** {year_disp}\n\n**Kilométrage :** {km_disp}")
        
        st.dataframe(
            df_filtered[["agency", "title", "price", "year", "km"]], 
            use_container_width=True, 
            height=320
        )
    else:
        st.warning("Aucune annonce chargée. Cliquez sur le bouton '🔄 Lancer l'extraction réelle' dans le menu de gauche.")

with col_right:
    st.markdown("### 🔍 Annonces Miroirs (Particuliers)")
    
    if len(df_filtered) > 0:
        st.write("Génération automatique des recherches pour repérer le particulier vendeur :")
        
        y_min = f"{int(car['year'])-1}" if str(car['year']).isdigit() and car['year'] != "" else ""
        y_max = f"{int(car['year'])+1}" if str(car['year']).isdigit() else ""
        km_min = f"{max(0, int(car['km'])-5000):,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        km_max = f"{int(car['km'])+5000:,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        
        st.markdown(f"""
        **Critères ciblés :**
        * Véhicule : `{car['make']} {car['model']}`
        * Années : `{y_min} - {y_max}`
        * Kilométrage : `{km_min}` à `{km_max}` km
        """)
        
        st.markdown("---")
        
        col_lbc, col_lc = st.columns(2)
        with col_lbc:
            st.link_button("🟠 Recherche LeBonCoin", car["lbc_url"], use_container_width=True)
        with col_lc:
            st.link_button("🔵 Recherche La Centrale", car["lacentrale_url"], use_container_width=True)

        st.success("""
        **💡 Prospection :**  
        Si le véhicule sort sur LeBonCoin au nom d'un particulier à un prix inférieur, c'est le mandat non-exclusif idéal à rentrer !
        """)
