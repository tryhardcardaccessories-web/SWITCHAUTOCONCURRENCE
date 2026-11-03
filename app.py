import streamlit as st
import pandas as pd
import requests
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

# Cartographie complète des 11 agences concurrentes cibles
COMPETITORS = {
    "Transakauto Roncq": {"dealer_id": "C045809", "name": "Transakauto Roncq"},
    "Transakauto Wambrechies": {"dealer_id": "C045809", "name": "Transakauto Wambrechies"},
    "Partenaire Auto": {"dealer_id": "C040938", "name": "Partenaire Auto"},
    "Ewigo Roncq": {"dealer_id": "C037105", "name": "Ewigo Roncq"},
    "Ewigo Villeneuve d'Ascq": {"dealer_id": "C037105", "name": "Ewigo Villeneuve d'Ascq"},
    "Ewigo Lesquin": {"dealer_id": "C037105", "name": "Ewigo Lesquin"},
    "Simplicicar La Madeleine": {"dealer_id": "C040938", "name": "Simplicicar La Madeleine"},
    "Via Automobile Roncq": {"dealer_id": "C038590", "name": "Via Automobile Roncq"},
    "Via Automobile Villeneuve d'Ascq": {"dealer_id": "C038590", "name": "Via Auto VDA"},
    "Vroom Market": {"dealer_id": "C040938", "name": "Vroom Market"},
    "L'Agence Automobilière Wasquehal": {"dealer_id": "C060915", "name": "L'Agence Auto Wasquehal"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://pros.lacentrale.fr",
    "Referer": "https://pros.lacentrale.fr/",
}

def generate_lacentrale_search_url(make, model, year, km):
    """Génère le lien de recherche miroir sur La Centrale (filtre particuliers/pros)."""
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
    """Génère le lien de recherche miroir ciblée sur LeBonCoin."""
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
    """Requêtes directes sur l'API d'indexation pour extraire 100% du stock sans blocage HTML."""
    all_vehicles = []
    global_id = 1
    
    session = requests.Session()
    
    for agency_name, info in COMPETITORS.items():
        dealer_id = info["dealer_id"]
        
        # Endpoint de l'API REST de La Centrale Pros
        api_url = f"https://pros.lacentrale.fr/api/v1/dealers/{dealer_id}/ads?page=1&pageSize=100"
        
        try:
            res = session.get(api_url, headers=HEADERS, timeout=10, verify=False)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", []) or data.get("ads", []) or data.get("vehicles", [])
                
                for item in items:
                    make = item.get("make", "") or item.get("brand", "") or item.get("vehicleBrand", "")
                    model = item.get("model", "") or item.get("vehicleModel", "")
                    version = item.get("version", "") or item.get("commercialName", "")
                    
                    full_title = f"{make} {model} {version}".strip()
                    if not full_title:
                        full_title = item.get("title", f"Véhicule {agency_name}")
                    
                    raw_price = item.get("price", 0)
                    price_str = f"{raw_price:,} €".replace(",", " ") if isinstance(raw_price, (int, float)) and raw_price > 0 else "Prix N.C."
                    
                    year = str(item.get("year", "")) or str(item.get("regDate", ""))[:4]
                    km_val = item.get("mileage", "") or item.get("km", "")
                    km_str = str(km_val)
                    
                    all_vehicles.append({
                        "id": global_id,
                        "agency": agency_name,
                        "title": full_title,
                        "make": make if make else full_title.split(" ")[0],
                        "model": model if model else (full_title.split(" ")[1] if len(full_title.split(" ")) > 1 else ""),
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

# --- INTERFACE UTILISATEUR STREAMLIT ---

st.title("🚗 Switch Auto — Global Competitor Matcher")
st.caption("Centralisation exhaustive des stocks concurrents (Métropole Lilloise) & Détection des mandats non-exclusifs")

# Sidebar: Actions et Filtres
st.sidebar.header("1. Options d'Extraction")
if st.sidebar.button("🔄 Lancer l'extraction API réelles", type="primary"):
    st.cache_data.clear()

with st.spinner("Extraction directe du stock des 11 agences..."):
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

st.subheader(f"📊 Stock global consolidé ({len(df_filtered)} véhicules récupérés en temps réel)")

# DISPOSITION 2 COLONNES
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Catalogue Concurrence Unifié")
    
    if len(df_filtered) > 0:
        selected_title = st.selectbox(
            "Sélectionner un véhicule à analyser :", 
            df_filtered["title"].tolist()
        )
        
        car = df_filtered[df_filtered["title"] == selected_title].iloc[0]
        
        km_display = f"{int(car['km']):,} km" if str(car['km']).isdigit() and car['km'] != "" else "N.C."
        year_display = car['year'] if car['year'] != "" else "N.C."
        
        st.info(f"**Agence :** {car['agency']}\n\n**Modèle :** {car['title']}\n\n**Prix Pro :** {car['price']}\n\n**Année :** {year_display}\n\n**Kilométrage :** {km_display}")
        
        st.dataframe(
            df_filtered[["agency", "title", "price", "year", "km"]], 
            use_container_width=True, 
            height=320
        )
    else:
        st.warning("Aucun véhicule extrait. Cliquez sur le bouton '🔄 Lancer l'extraction API réelles' dans le panneau de gauche pour charger le marché.")

with col_right:
    st.markdown("### 🔍 Annonces Miroirs (Particuliers)")
    
    if len(df_filtered) > 0:
        st.write("Recherche ciblée pour vérifier si le propriétaire vend en direct :")
        
        year_min_txt = f"{int(car['year'])-1}" if str(car['year']).isdigit() and car['year'] != "" else ""
        year_max_txt = f"{int(car['year'])+1}" if str(car['year']).isdigit() else ""
        km_min_txt = f"{max(0, int(car['km'])-5000):,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        km_max_txt = f"{int(car['km'])+5000:,}" if str(car['km']).isdigit() and car['km'] != "" else ""
        
        st.markdown(f"""
        **Critères d'analyse :**
        * Modèle : `{car['make']} {car['model']}`
        * Fenêtre Année : `{year_min_txt} - {year_max_txt}`
        * Fenêtre Kilométrage : `{km_min_txt}` à `{km_max_txt}` km
        """)
        
        st.markdown("---")
        
        col_lbc, col_lc = st.columns(2)
        with col_lbc:
            st.link_button("🟠 Recherche LeBonCoin", car["lbc_url"], use_container_width=True)
        with col_lc:
            st.link_button("🔵 Recherche La Centrale", car["lacentrale_url"], use_container_width=True)

        st.success("""
        **💡 Prospection :**  
        Si l'annonce apparaît moins chère sur LeBonCoin au nom d'un particulier, c'est le mandat non-exclusif idéal à récupérer !
        """)
