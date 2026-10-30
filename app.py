import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
# 1. APP CONFIGURATION (Hier ändern wir das Icon im Browsertab)
# ==============================================================================
st.set_page_config(
    page_title="Trader Intelligence Terminal",
    page_icon="⚡",  # Hier kannst du jedes Emoji als App-Icon setzen
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. DATA FEEDS (Saubere Funktionen für den Datenabruf)
# ==============================================================================
def fetch_cnbc_rss_feed() -> list:
    """Holt die neuesten 15 Meldungen von CNBC und bereinigt den Text."""
    url = "https://cnbc.com"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        
        # UTF-8 Dekodierung ignoriert fehlerhafte Sonderzeichen
        raw_xml = response.content.decode('utf-8', errors='ignore')
        root = ET.fromstring(raw_xml)
        
        articles = []
        for item in root.findall('.//item')[:15]: 
            title = item.find('title').text if item.find('title') is not None else "Kein Titel"
            link = item.find('link').text if item.find('link') is not None else "#"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Uhrzeit sauber extrahieren (HH:MM)
            try:
                time_str = " ".join(pub_date.split(' ')[4:5])[:-3] # Schneidet die Sekunden ab
            except:
                time_str = datetime.now().strftime('%H:%M')
                
            articles.append({"time": time_str, "title": title, "link": link})
        return articles
    except Exception as e:
        # Fallback, falls die API offline ist
        return [{"time": "--:--", "title": f"Feed temporär nicht erreichbar... ({str(e)})", "link": "#"}]


def get_economic_calendar() -> list:
    """Liefert die Daten für den Wirtschaftskalender."""
    # Später verknüpfen wir das mit einer echten Kalender-API
    return [
        {"time": "14:30", "event": "US-Core CPI (Inflation) MoM", "forecast": "0.2%", "actual": "0.4%", "type": "CPI"},
        {"time": "16:00", "event": "ISM Manufacturing PMI", "forecast": "48.5", "actual": "47.2", "type": "Growth"}
    ]

# ==============================================================================
# 3. SIDEBAR & FILTER LOGIK
# ==============================================================================
st.sidebar.header("⚙️ Terminal-Filter")

# Eingabe für Keywords. Macht automatisch alles zu Kleinbuchstaben für fehlerfreie Suche
keywords_input = st.sidebar.text_input("🚨 Eilmeldungs-Filter (Komma-getrennt)", "Krieg, Verhandlung, Fed, Inflation, Zinsen")
keywords = [kw.strip().lower() for kw in keywords_input.split(",") if kw.strip()]

st.sidebar.markdown("---")
st.sidebar.caption("Terminal v2.0 • Live über GitHub & Streamlit")

# ==============================================================================
# 4. MAIN INTERFACE (Das Layout der App)
# ==============================================================================

# Platzhalter für ein Header-Bild (Falls du ein eigenes Bild hochlädst)
# Wenn du ein Bild namens logo.png im Ordner hast, entferne das '#' in der nächsten Zeile:
 st.image("logo.png", width=200)

st.title("⚡ Trader Intelligence Terminal")
st.markdown("---")

# Layout aufteilen (2 Spalten mit einem Spaltenverhältnis von 1:1)
left_column, right_column = st.columns(2)

# --- LINKE SPALTE: WIRTSCHAFTSKALENDER ---
with left_column:
    st.subheader("🗓️ Smarter Wirtschaftskalender")
    st.caption("Färbung nach echter Marktauswirkung (Rot = Schlecht für Indizes)")
    
    for ev in get_economic_calendar():
        with st.container(border=True):
            # Logik zur Bestimmung des Marktsignals
            is_bearish = False
            signal_text = "NEUTRAL"
            
            actual_num = float(ev["actual"].replace("%",""))
            forecast_num = float(ev["forecast"].replace("%",""))
            
            if ev["type"] == "CPI" and actual_num > forecast_num:
                is_bearish = True
                signal_text = "🔴 BÄRISCH (Höhere Inflation = Zinsdruck)"
            elif ev["type"] == "Growth" and actual_num < forecast_num:
                is_bearish = True
                signal_text = "🔴 BÄRISCH (Wirtschaft kühlt ab)"
                
            color = "#FF4B4B" if is_bearish else "#00E676"
            
            # Oberfläche zeichnen
            st.markdown(f"### {ev['time']} - {ev['event']}")
            st.markdown(f"**Prognose:** {ev['forecast']} | **Aktuell:** <span style='color:{color}; font-weight:bold; font-size:1.2rem;'>{ev['actual']}</span>", unsafe_allow_html=True)
            st.caption(f"Signal: {signal_text}")

# --- RECHTE SPALTE: LIVE NEWS TIKKER ---
with right_column:
    st.subheader("📰 Live Global News Feed")
    st.caption("Aktuelle Schlagzeilen von CNBC (Wichtige Keywords werden hervorgehoben)")
    
    news_data = fetch_cnbc_rss_feed()
    
    for news in news_data:
        # Prüfen, ob eines der eingegebenen Keywords im Titel vorkommt
        title_lower = news["title"].lower()
        has_keyword = any(kw in title_lower for kw in keywords)
        
        with st.container(border=True):
            if has_keyword:
                # Highlight-Box für kriegs- oder marktrelevante News
                st.markdown(f"🚨 **[{news['time']}] {news['title']}**")
                st.caption(f"[🔥 RELEVANTE MELDUNG ÖFFNEN]({news['link']})")
            else:
                # Normale Anzeige für Standard-News
                st.markdown(f"**[{news['time']}] {news['title']}**")
                st.caption(f"[Artikel öffnen]({news['link']})")
