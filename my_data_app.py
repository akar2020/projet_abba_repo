import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import os

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Dakar Auto Scraper Pro", layout="wide",)

# --- FONCTION DE DÉTECTION DYNAMIQUE ---
def get_total_pages(url_categorie):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url_categorie, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        nav_paginator = soup.find('nav', class_='paginator')
        if nav_paginator:
            ul = nav_paginator.find('ul')
            if ul:
                li_items = ul.find_all('li')
                if li_items:
                    dernier_a = li_items[-1].find('a')
                    if dernier_a and dernier_a.has_attr('href'):
                        href = dernier_a['href']
                        match = re.search(r'page=(\d+)', href)
                        if match: return int(match.group(1))
                        match_alt = re.search(r'-(\d+)$', href)
                        if match_alt: return int(match_alt.group(1))
        return 1
    except: return 1

# --- FONCTIONS DE NETTOYAGE ---
def clean_numeric(value):
    if value == "N/A" or not value: return None
    cleaned = re.sub(r'\D', '', str(value))
    return int(cleaned) if cleaned else None

def clean_text(value):
    if value == "N/A" or not value: return "INCONNU"
    return str(value).strip().upper()

# --- MOTEUR DE SCRAPING COMPLET ---
def scraper_dakar_auto(max_pages, type_vehicule):
    all_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    urls = {
        "voitures": "https://dakar-auto.com/senegal/voitures-4?&page=",
        "motos": "https://dakar-auto.com/senegal/motos-and-scooters-3?&page=",
        "location": "https://dakar-auto.com/senegal/location-de-voitures-19?&page="
    }
    
    for p in range(1, max_pages + 1):
        url = f"{urls[type_vehicule]}{p}"
        status_text.write(f"Scan {type_vehicule} - Page {p}/{max_pages}...")
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            annonces = soup.find_all('div', class_='listings-cards__list-item')
            
            for ann in annonces:
                # 1. Infos de base (Titre, Prix, Adresse)
                titre_el = ann.find('h2', class_='listing-card__header__title')
                titre = titre_el.text.strip() if titre_el else "N/A"
                prix_el = ann.find('h3', class_='listing-card__header__price')
                
                data = {
                    "Marque": clean_text(titre[:-4]),
                    "Année": clean_numeric(titre[-4:]),
                    "Prix": clean_numeric(prix_el.text if prix_el else "0"),
                    "Adresse": clean_text(ann.find('span', class_='province').text if ann.find('span', class_='province') else "N/A")
                }
                
                # 2. Propriétés spécifiques (Kilométrage, Boite, Carburant)
                props = ann.find('div', class_='listing-card__properties')
                if props:
                    lis = props.find_all('li')
                    if type_vehicule in ["voitures", "motos"]:
                        data["Kilométrage"] = clean_numeric(lis[1].text) if len(lis) > 1 else None
                    if type_vehicule == "voitures":
                        data["Boite vitesse"] = clean_text(lis[2].text) if len(lis) > 2 else "N/A"
                        data["Carburant"] = clean_text(lis[3].text) if len(lis) > 3 else "N/A"
                
                # 3. Propriétaire
                auth = ann.find('div', class_='author-meta')
                if auth and auth.find('p', class_='time-author') and auth.find('p', class_='time-author').a:
                    data["Propriétaire"] = clean_text(auth.find('p', class_='time-author').a.text[4:].strip())
                else:
                    data["Propriétaire"] = "N/A"

                all_data.append(data)
        except: pass
        progress_bar.progress(p / max_pages)
        time.sleep(0.1)
    
    status_text.empty()
    return pd.DataFrame(all_data)

# --- SIDEBAR ---
with st.sidebar:
    st.title("Paramètres")
    cat_keys = {"Voitures": "voitures", "Motos et Scooters": "motos", "Location de voitures": "location"}
    cat_urls = {
        "voitures": "https://dakar-auto.com/senegal/voitures-4",
        "motos": "https://dakar-auto.com/senegal/motos-and-scooters-3",
        "location": "https://dakar-auto.com/senegal/location-de-voitures-19"
    }
    choix_label = st.selectbox("Choisir la catégorie :", list(cat_keys.keys()))
    cat_tech = cat_keys[choix_label]
    
    max_p = get_total_pages(cat_urls[cat_tech])
    nb_pages = st.number_input(f"Pages à scraper (Max: {max_p})", 1, max_p, 1)
    
    options_app = ["Scraper avec BeautifulSoup", "Scraper avec Web Scraper", "Tableau de Bord", "Évaluation"]
    action_choisie = st.selectbox("Options", options_app)

# --- LOGIQUE PRINCIPALE ---
if action_choisie == "Évaluation":
    st.header("Évaluation")
    st.write("Contribuez à l'amélioration de cette application :")
    col1, col2 = st.columns(2)
    with col1: st.link_button("Google Forms", "https://forms.gle/6vniYzs14vgPNXwo8")
    with col2: st.link_button("KoboToolbox", "https://ee.kobotoolbox.org/rjeUfcG2")

else:
    if action_choisie == "Scraper avec BeautifulSoup":
        if cat_tech == "voitures":
            text_cat_tech="voitures"
        elif cat_tech =="motos":
            text_cat_tech="motos et scooters"
        else:
            text_cat_tech= "location de voitures"
        
        st.header(f"Scraper les données sur les {text_cat_tech} avec BeautifulSoup")
        if st.button(f"Lancer l'extraction"):
            st.session_state[f"data_{cat_tech}"] = scraper_dakar_auto(nb_pages, cat_tech)
        
        if f"data_{cat_tech}" in st.session_state:
            st.dataframe(st.session_state[f"data_{cat_tech}"], use_container_width=True)

    elif action_choisie == "Scraper avec Web Scraper":
        st.header(f"Importation obtenues via Web Scraper ({cat_tech})")
        try:
            # On cherche dans le dossier 'datas' comme dans votre code
            df_ws = pd.read_csv(f"datas/{cat_tech}.csv")
            st.session_state[f"data_{cat_tech}"] = df_ws
            st.success("Données chargées avec succès !")
            st.dataframe(df_ws, use_container_width=True)
        except:
            st.warning(f"Aucun fichier trouvé : `datas/{cat_tech}.csv` n'existe pas.")

    elif action_choisie == "Tableau de Bord":
        st.header(f"Analyse : {choix_label}")
        if f"data_{cat_tech}" in st.session_state:
            df = st.session_state[f"data_{cat_tech}"]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Annonces", len(df))
            if 'Prix' in df.columns:
                c2.metric("Prix Moyen", f"{int(df['Prix'].mean()):,} FCFA".replace(',', ' '))
                c3.metric("Prix Max", f"{int(df['Prix'].max()):,} FCFA".replace(',', ' '))
            
            st.divider()
            cl, cr = st.columns(2)
            with cl:
                st.subheader("Top Marques")
                st.bar_chart(df['Marque'].value_counts().head(10))
            with cr:
                st.subheader("Volume par Année")
                if 'Année' in df.columns:
                    st.line_chart(df['Année'].value_counts().sort_index())
        else:
            st.info("Scrapez des données pour afficher les graphiques.")