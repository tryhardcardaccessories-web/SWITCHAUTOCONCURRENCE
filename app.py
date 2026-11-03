import streamlit as st
import pandas as pd
import urllib.parse
import re

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Switch Auto — Matcher Boutique Directe",
    page_icon="🚗",
    layout="wide"
)

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

def parse_raw_text_input(raw_text, agency_name):
    """Analyse du texte copié depuis la page boutique pour extraire les annonces."""
    vehicles = []
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    
    # Analyse par blocs de texte ou lignes d'annonces
    for i, line in enumerate(lines):
        # Recherche de motifs typiques d'annonces (Marque + Prix + KM)
        price_m = re.search(r"(\d+[\s.]?\d*)\s*€", line)
        year_m = re.search(r"\b(20\d{2})\b", line)
        km_m = re.search(r"(\d+[\s.]?\d*)\s*(km|KM)", line)
        
        if price_m or year_m or km_m:
            words = line.split()
            make = words[0] if len(words) > 0 else "Auto"
            model = words[1] if len(words) > 1 else ""
            
            price = f"{price_m.group(1)} €" if price_m else "N.C."
            year = year_m.group(1) if year_m else ""
            km_raw = km_m.group(1) if km_m else ""
            km_str = re.sub(r"\D", "", km_raw)
            
            vehicles.append({
                "agency": agency_name,
                "title": line,
                "make": make,
                "model": model,
                "price": price,
                "year": year,
                "km": km_str,
                "lbc_url": generate_leboncoin_search_url(make, model, year, km_str),
                "lacentrale_url": generate_lacentrale_search_url(make, model, year, km_str),
            })
            
    return pd.DataFrame(vehicles)

# --- INTERFACE UTILISATEUR ---

st.title("🚗 Switch Auto — Analyseur de Boutique Concurrente")
st.caption("Génération immédiate de liens miroirs à partir des boutiques LeBonCoin / La Centrale")

# Stockage de la session
if "master_stock" not in st.sidebar:
    st.session_state["master_stock"] = pd.DataFrame()

st.sidebar.header("1. Importer une Boutique")

agency_choice = st.sidebar.selectbox(
    "Agence ciblée :",
    ["Transakauto Lille / Roncq", "Ewigo", "Simplicicar", "Via Automobile", "Autre"]
)

st.sidebar.markdown(f"**Lien Boutique :**  \n`https://www.leboncoin.fr/boutique/1385539/transakauto_lille.htm`")

raw_input = st.sidebar.text_area(
    "Copie-colle le texte de la page boutique ici (Ctrl+A puis Ctrl+C sur la page) :",
    height=150,
    placeholder="Exemple : Peugeot 308 1.2 PureTech 130ch - 14 500 € - 2019 - 65 000 km..."
)

if st.sidebar.button("➕ Ajouter au marché", type="primary"):
    if raw_input:
        df_new = parse_raw_text_input(raw_input, agency_choice)
        st.session_state["master_stock"] = pd.concat([st.session_state["master_stock"], df_new], ignore_index=True)
        st.sidebar.success(f"{len(df_new)} véhicule(s) ajouté(s) !")
    else:
        st.sidebar.error("Veuillez coller du texte d'annonce.")

if st.sidebar.button("🗑️ Réinitialiser le marché"):
    st.session_state["master_stock"] = pd.DataFrame()
    st.rerun()

df_display = st.session_state["master_stock"]

st.subheader(f"📊 Annonces sous surveillance ({len(df_display)} véhicules)")

if len(df_display) > 0:
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.markdown("### 📋 Sélection de l'annonce")
        selected_index = st.selectbox(
            "Choisissez un véhicule :",
            range(len(df_display)),
            format_func=lambda x: f"[{df_display.iloc[x]['agency']}] {df_display.iloc[x]['title']}"
        )
        
        car = df_display.iloc[selected_index]
        
        st.info(f"""
        **Agence :** {car['agency']}  
        **Titre :** {car['title']}  
        **Prix :** {car['price']}  
        **Année :** {car['year'] if car['year'] else 'N.C.'}  
        **Kilométrage :** {car['km'] if car['km'] else 'N.C.'} km  
        """)
        
        st.dataframe(df_display[["agency", "title", "price", "year", "km"]], use_container_width=True)
        
    with col_right:
        st.markdown("### 🔍 Recherche Miroirs Directe")
        st.write("Vérifiez immédiatement si le particulier vend en direct :")
        
        col_lbc, col_lc = st.columns(2)
        with col_lbc:
            st.link_button("🟠 Recherche LeBonCoin", car["lbc_url"], use_container_width=True)
        with col_lc:
            st.link_button("🔵 Recherche La Centrale", car["lacentrale_url"], use_container_width=True)

        st.success("""
        **💡 Astuce Prospection :**  
        Si l'auto sort sur LeBonCoin au nom d'un particulier à un prix inférieur, c'est un mandat non-exclusif !
        """)
else:
    st.info("Sélectionnez une agence dans le panneau de gauche et collez le contenu de sa boutique LeBonCoin pour générer les liens miroirs instantanément.")
