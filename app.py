import streamlit as st
import pandas as pd
import urllib.parse
import requests
import random
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Radar & Scraper en Ligne",
    page_icon="🚗",
    layout="wide"
)

# --- CONSTANTES ---
SECTEUR_LBC = "Roncq_59223__30000"  # Roncq + 30 km

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def online_scraper_lbc():
    """Scraper distant configuré pour tenter de contourner les filtres en ligne."""
    session = requests.Session()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.leboncoin.fr/",
        "Sec-Ch-Ua": '"Chromium";v="123", "Not:A-Brand";v="8"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    
    # URL de recherche pro ciblée (Catégorie Voitures, Pros, Secteur Roncq +30km)
    url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=pro&locations={SECTEUR_LBC}"
    
    vehicles = []
    try:
        # Requête distante
        res = session.get(url, headers=headers, timeout=15)
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
                        "km": f"{km:,} km".replace(",", " ") if str(km).isdigit() else "N.C.",
                        "raw_km": int(km) if str(km).isdigit() else 0,
                        "url_pro": url_ad if url_ad.startswith("http") else f"https://www.leboncoin.fr{url_ad}"
                    })
    except Exception as e:
        st.error(f"Erreur technique lors du scraping en ligne : {e}")
        
    return pd.DataFrame(vehicles)

# Initialisation des états de session
if "scraped_data" not in st.session_state:
    st.session_state["scraped_data"] = pd.DataFrame()

if "selected_car" not in st.session_state:
    st.session_state["selected_car"] = None

st.title("🚗 Switch Auto — Radar & Mirroring en Ligne")
st.caption("Extraction automatisée en ligne des annonces pros & Matching Particuliers strict")

# --- BARRE LATÉRALE : CONTRÔLE DU SCRAPER ---
st.sidebar.header("🌐 Contrôle du Scraper Distant")
st.sidebar.info("Clique sur le bouton ci-dessous pour lancer l'extraction des annonces professionnelles directement depuis le serveur en ligne.")

if st.sidebar.button("🚀 Lancer l'extraction des annonces Pros", type="primary"):
    with st.spinner("Connexion aux serveurs et extraction des annonces en cours..."):
        df_result = online_scraper_lbc()
        if len(df_result) > 0:
            st.session_state["scraped_data"] = df_result
            st.sidebar.success(f"🎉 {len(df_result)} annonces pros extraites avec succès !")
        else:
            st.sidebar.warning("Protection anti-bot détectée par le serveur distant. (Utilise le mode de secours par Google Sheets si le blocage persiste).")

df_pros = st.session_state["scraped_data"]

# --- LAYOUT EN DEUX COLONNES ---
col_left, col_right = st.columns([1.3, 1], gap="large")

# ==============================================================================
# COLONNE GAUCHE : FLUX DES ANNONCES PROS EXTRAITES EN LIGNE
# ==============================================================================
with col_left:
    st.header("📋 Catalogue Pros (Extraction en Ligne)")
    
    if len(df_pros) > 0:
        st.write("Sélectionne un véhicule pour lancer son **mirroring strict** à droite :")
        
        for idx, row in df_pros.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2.5, 1.2, 1, 1.2, 1.5])
                with c1:
                    st.markdown(f"**{row['title']}**")
                    if row['url_pro'].startswith("http"):
                        st.caption(f"[🔗 Lien Pro]({row['url_pro']})")
                with c2:
                    st.write(f"💰 {row['price']}")
                with c3:
                    st.write(f"📅 {row['year']}")
                with c4:
                    st.write(f"🛣️ {row['km']}")
                with c5:
                    if st.button("🔍 Miroir", key=f"btn_{idx}", type="secondary"):
                        st.session_state["selected_car"] = row
                        st.rerun()
                st.markdown("---")
    else:
        st.info("👈 Clique sur **« Lancer l'extraction des annonces Pros »** dans le menu de gauche pour charger le catalogue en direct.")

# ==============================================================================
# COLONNE DROITE : MIRRORING PARTICULIER (MÊME MODÈLE, ANNÉE, KM)
# ==============================================================================
with col_right:
    st.header("👤 Mirroring Particuliers Stricte")
    
    car = st.session_state["selected_car"]
    
    if car is not None:
        make = str(car.get("make", "")).strip()
        model = str(car.get("model", "")).strip()
        year_val = str(car.get("year", "")).strip()
        raw_km = car.get("raw_km", 0)
        
        st.success(f"🎯 **Cible :** {car['title']}")
        
        st.markdown(f"""
        **Critères stricts appliqués au mirroring :**
        * **Marque / Modèle :** `{make} {model}`
        * **Année exacte :** `{year_val}`
        * **Kilométrage ciblé :** `{raw_km:,} km` (avec delta de tolérance de +/- 10 000 km)
        * **Secteur :** `Roncq + 30 km`
        """)
        
        query_encoded = urllib.parse.quote(f"{make} {model}".strip())
        
        # Construction URL LBC Particulier (Critères stricts année + tranche kilométrage proche)
        lbc_part_url = f"https://www.leboncoin.fr/recherche?category=2&owner_type=private&text={query_encoded}&locations={SECTEUR_LBC}"
        if year_val.isdigit():
            lbc_part_url += f"&regdate={year_val}-{year_val}"
        if raw_km > 0:
            lbc_part_url += f"&mileage={max(0, raw_km-10000)}-{raw_km+10000}"
            
        # Construction URL La Centrale Particulier équivalente
        lc_params = {
            "makesModelsCommercialNames": f"{make}:{model}",
            "zipCodes": "59220,59000,59100,59200",
        }
        if year_val.isdigit():
            lc_params["yearMin"] = year_val
            lc_params["yearMax"] = year_val
        if raw_km > 0:
            lc_params["mileageMin"] = max(0, raw_km-10000)
            lc_params["mileageMax"] = raw_km+10000
            
        lc_part_url = f"https://www.lacentrale.fr/listing?{urllib.parse.urlencode(lc_params)}"
        
        st.markdown("---")
        
        st.link_button(
            f"🟠 🔍 Lancer LeBonCoin Particuliers (Miroir Stricte)", 
            lbc_part_url, 
            use_container_width=True, 
            type="primary"
        )
        
        st.write("")
        
        st.link_button(
            f"🔵 🔍 Lancer La Centrale Particuliers (Miroir)", 
            lc_part_url, 
            use_container_width=True
        )
        
        st.info("""
        💡 **Mission Mandat Simple :** Ce lien miroir intègre exactement les paramètres extraits par le scraper en ligne pour te sortir instantanément l'annonce du particulier en face !
        """)
    else:
        st.warning("👈 Clique sur le bouton **« 🔍 Miroir »** d'une annonce pro à gauche pour activer les liens de recherche particuliers ici.")
