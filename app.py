import streamlit as st
import pandas as pd
import urllib.parse
import re
import requests
import random

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Radar Mandats Simples",
    page_icon="🚗",
    layout="wide"
)

# --- CONSTANTES & BOUTIQUES LOCALES ---
SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km

# Dictionnaire des boutiques cibles du secteur
BOUTIQUES_PROS = {
    "Transakauto Roncq": "https://www.leboncoin.fr/boutique/7447928",
    "EWIGO Roncq": "https://www.leboncoin.fr/boutique/7145725/ewigo_roncq.htm",
    "EWIGO Lille - Villeneuve-d'Ascq": "https://www.leboncoin.fr/boutique/7032084/ewigo_lille_villeneuve_dascq.htm",
    "Auto Transit / Concessionnaires Roncq": "https://www.leboncoin.fr/boutique/2761627/auto_transit.htm",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def fetch_boutique_ads(boutique_url):
    """Récupère les annonces d'une boutique pro spécifique."""
    session = requests.Session()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.leboncoin.fr/",
    }
    
    vehicles = []
    try:
        res = session.get(boutique_url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if json_match:
                import json
                data = json.loads(json_match.group(1))
                # Extraction sécurisée depuis les données de la boutique
                ads = data.get("props", {}).get("pageProps", {}).get("ads", []) or data.get("props", {}).get("pageProps", {}).get("searchData", {}).get("ads", [])
                
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

# Initialisation des états de session
if "pro_data" not in st.session_state:
    st.session_state["pro_data"] = pd.DataFrame()

if "selected_car" not in st.session_state:
    st.session_state["selected_car"] = None

st.title("🚗 Switch Auto — Radar Mandats Simples (Boutiques Pro)")
st.caption("Secteur Roncq + 30 km | Cible : Concurrence Mandataire vs Particuliers")

# --- BARRE LATÉRALE : SÉLECTION DE LA BOUTIQUE ---
st.sidebar.header("1. Choix de la Boutique Pro")
selected_boutique_name = st.sidebar.selectbox("Sélectionne une agence concurrente :", list(BOUTIQUES_PROS.keys()))
selected_boutique_url = BOUTIQUES_PROS[selected_boutique_name]

st.sidebar.markdown(f"[🔗 Ouvrir la page de l'agence]({selected_boutique_url})")

if st.sidebar.button("📥 Charger le stock de cette agence", type="primary"):
    with st.spinner(f"Récupération du portefeuille de {selected_boutique_name}..."):
        df_fetched = fetch_boutique_ads(selected_boutique_url)
        if len(df_fetched) > 0:
            st.session_state["pro_data"] = df_fetched
            st.sidebar.success(f"🎉 {len(df_fetched)} véhicules chargés !")
        else:
            st.sidebar.warning("Sécurité active sur cette boutique. Utilise le lien direct ci-dessus pour consulter la page.")

# Option de secours : Copier-coller si la boutique bloque
st.sidebar.markdown("---")
st.sidebar.subheader("Alternative (Copier-Coller)")
raw_paste = st.sidebar.text_area("Ou colle le texte de la page Pro ici :", height=100)
if st.sidebar.button("Traiter le texte collé"):
    if raw_paste:
        # Parsing rapide du texte collé
        lines = [l.strip() for l in raw_paste.split("\n") if l.strip()]
        vehicles = []
        for line in lines:
            if "€" in line:
                vehicles.append({
                    "title": line,
                    "make": line.split()[0] if len(line.split()) > 0 else "Auto",
                    "model": line.split()[1] if len(line.split()) > 1 else "",
                    "price": line,
                    "year": "2015",
                    "km": "100000",
                    "url_pro": selected_boutique_url
                })
        st.session_state["pro_data"] = pd.DataFrame(vehicles)
        st.sidebar.success("Texte analysé !")

df_display = st.session_state["pro_data"]

# --- LAYOUT EN DEUX COLONNES ---
col_left, col_right = st.columns([1.3, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : PORTEFEUILLE DE L'AGENCE PRO
# ==============================================================================
with col_left:
    st.header(f"📋 Portefeuille : {selected_boutique_name}")
    
    if len(df_display) > 0:
        st.write("Clique sur **« 🔍 Miroir »** pour lancer la chasse au particulier en face :")
        
        for idx, row in df_display.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 2])
                with c1:
                    st.markdown(f"**{row['title']}**")
                    if row['url_pro'].startswith("http"):
                        st.caption(f"[🔗 Voir l'annonce Pro]({row['url_pro']})")
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
        st.info("👈 Sélectionne une agence dans le menu de gauche et clique sur **« Charger le stock »** pour afficher ses véhicules.")

# ==============================================================================
# COLONNE DROITE : RECHERCHE MIROIR PARTICULIER
# ==============================================================================
with col_right:
    st.header("👤 Recherche Miroir Particulier")
    
    car = st.session_state["selected_car"]
    
    if car is not None:
        make = car["make"]
        model = car["model"]
        year_val = car["year"]
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # Construction du lien miroir LeBonCoin Particuliers (Année stricte, kilométrage libre pour ne pas rater l'annonce)
        lbc_part_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=private&text={query_encoded}&locations={SECTEUR_LBC}"
        if str(year_val).isdigit():
            lbc_part_url += f"&regdate={year_val}-{year_val}"
            
        # La Centrale Particuliers
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "zipCodes": "59220,59000,59100,59200",
        }
        if str(year_val).isdigit():
            lc_params["yearMin"] = year_val
            lc_params["yearMax"] = year_val
            
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.success(f"🎯 **Cible :** {car['title']}")
        
        st.markdown(f"""
        **Paramètres du miroir (Secteur Roncq +30 km) :**
        * **Modèle :** `{make} {model}`
        * **Année :** `{year_val}`
        * **Kilométrage :** `Libre (pour capturer les écarts de saisie)`
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
        **💡 Conseil Prospection :**  
        Si l'annonce du particulier sort sur le secteur avec cette année-là, tu tiens ton mandat non-exclusif à aller chercher !
        """)
    else:
        st.warning("👈 Clique sur le bouton **« 🔍 Miroir »** à côté d'un véhicule à gauche pour afficher les liens de recherche ici.")
