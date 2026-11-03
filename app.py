import streamlit as st
import pandas as pd
import urllib.parse
import re
import requests
import random

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Matcher Miroir Pro/Particulier",
    page_icon="🚗",
    layout="wide"
)

# --- CONSTANTES MYTRAX ---
SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km
ANNEE_MIN = 2006
KM_MAX = 250000

# User-Agents pour la rotation des requêtes
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def fetch_lbc_pro_ads():
    """Scraper émulé pour extraire le flux Pros."""
    session = requests.Session()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.leboncoin.fr/",
    }
    
    url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=pro&regdate={ANNEE_MIN}-max&mileage=min-{KM_MAX}&locations={SECTEUR_LBC}"
    
    vehicles = []
    try:
        res = session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if json_match:
                import json
                data = json.loads(json_match.group(1))
                ads = data.get("props", {}).get("pageProps", {}).get("searchData", {}).get("ads", [])
                
                for ad in ads:
                    title = ad.get("subject", "")
                    price = ad.get("price", [0])[0] if isinstance(ad.get("price"), list) else ad.get("price", 0)
                    url_ad = ad.get("url", "")
                    attributes = {attr.get("key"): attr.get("value") for attr in ad.get("attributes", [])}
                    
                    make = attributes.get("brand", "")
                    model = attributes.get("model", "")
                    year = attributes.get("regdate", "")
                    km = attributes.get("mileage", "")
                    
                    if not make and title:
                        parts = title.split()
                        make = parts[0] if len(parts) > 0 else "Auto"
                        model = parts[1] if len(parts) > 1 else ""

                    vehicles.append({
                        "title": title,
                        "make": make,
                        "model": model,
                        "price": f"{price:,} €".replace(",", " ") if price else "N.C.",
                        "year": str(year) if year else "N.C.",
                        "km": str(km) if km else "N.C.",
                        "url_pro": url_ad if url_ad.startswith("http") else f"https://www.leboncoin.fr{url_ad}"
                    })
    except Exception:
        pass
        
    return pd.DataFrame(vehicles)

# Initialisation de la mémoire d'annonces
if "pro_data" not in st.session_state:
    st.session_state["pro_data"] = pd.DataFrame()

if "selected_car" not in st.session_state:
    st.session_state["selected_car"] = None

st.title("🚗 Switch Auto — Sourcing Pros & Matcher Miroir")
st.caption("Filtres MyTrax : Roncq + 30 km | Année ≥ 2006 | KM ≤ 250 000 km")

# Barre latérale : Actions
st.sidebar.header("🔄 Contrôle du Sourcing")
if st.sidebar.button("🔄 Rafraîchir les annonces Pros", type="primary"):
    with st.spinner("Récupération des annonces pros sur Roncq + 30 km..."):
        df_fetched = fetch_lbc_pro_ads()
        if len(df_fetched) > 0:
            st.session_state["pro_data"] = df_fetched
            st.sidebar.success(f"{len(df_fetched)} annonces pros récupérées !")
        else:
            st.sidebar.warning("Sécurité réseau détectée sur l'API globale. Utilisation du mode sécurisé.")

df_display = st.session_state["pro_data"]

# --- LAYOUT DOUBLE COLONNE ---
col_left, col_right = st.columns([1.3, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : FLUX DES ANNONCES PROFESSIONNELLES
# ==============================================================================
with col_left:
    st.header("📋 Annonces Pros du Secteur (Roncq +30 km)")
    
    if len(df_display) > 0:
        st.write("Clique sur **« 🔍 Miroir »** pour afficher la recherche Particulier à droite :")
        
        for idx, row in df_display.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 2])
                with c1:
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"[🔗 Lien Annonce Pro]({row['url_pro']})")
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
        st.info("Clique sur **« 🔄 Rafraîchir les annonces Pros »** dans le menu de gauche pour charger le catalogue.")

# ==============================================================================
# COLONNE DROITE : FENÊTRE MIROIR PARTICULIERS ( SÉCURISÉE & CIBLÉE )
# ==============================================================================
with col_right:
    st.header("👤 Recherche Miroir Particuliers")
    
    car = st.session_state["selected_car"]
    
    if car is not None:
        make = car["make"]
        model = car["model"]
        year_val = car["year"]
        km_val = car["km"]
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # Construction sécurisée des paramètres (si c'est un nombre valide, on cible strict, sinon on élargit ou laisse vide)
        lbc_part_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=private&text={query_encoded}&locations={SECTEUR_LBC}"
        if str(year_val).isdigit():
            lbc_part_url += f"&regdate={year_val}-{year_val}"
        if str(km_val).isdigit():
            lbc_part_url += f"&mileage={km_val}-{km_val}"
            
        # La Centrale URL sécurisée
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "zipCodes": "59220,59000,59100,59200",
        }
        if str(year_val).isdigit():
            lc_params["yearMin"] = year_val
            lc_params["yearMax"] = year_val
        if str(km_val).isdigit():
            lc_params["mileageMin"] = km_val
            lc_params["mileageMax"] = km_val
            
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.success(f"🎯 **Cible sélectionnée :** {car['title']}")
        
        st.markdown(f"""
        **Critères ciblés (Particuliers Roncq +30 km) :**
        * **Marque / Modèle :** `{make} {model}`
        * **Année :** `{year_val}`
        * **Kilométrage :** `{km_val} km`
        * **Secteur :** `Roncq + 30 km`
        """)
        
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
        Si le véhicule sort publié par un particulier sur le même secteur, tu as identifié le mandat non-exclusif !
        """)
    else:
        st.warning("👈 Clique sur le bouton **« 🔍 Miroir »** à côté d'une annonce pro dans le tableau de gauche pour afficher la recherche Particuliers ici.")
