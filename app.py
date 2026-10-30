
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Page Configuration für Trading-Look
st.set_page_config(page_title="Trader Intelligence Terminal", layout="wide")

st.title("⚡ Trader Intelligence Terminal (Real-Time)")
st.caption("Echtzeit-Nachrichten & Smarter Wirtschaftskalender")

# Sidebar für Einstellungen
st.sidebar.header("⚙️ Einstellungen & Filter")
news_keywords = st.sidebar.text_input("News Keywords (Filter)", "Krieg, Verhandlung, Inflation, Fed, Zinsen")

# Reparierte, stabile News-Quelle via Weltnachrichten-RSS Feed
def get_live_news():
    try:
        # Wir nutzen einen stabilen globalen Wirtschafts- und Politikfeed
        url = "https://cnbc.com"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(response.content)
        
        news_list = []
        for item in root.findall('.//item')[:15]: # Die neuesten 15 Meldungen
            titel = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # Formatiere das Datum auf eine kurze Uhrzeit
            try:
                zeit = pub_date.split(' ')[4][:5]
            except:
                zeit = "--:--"
                
            news_list.append({
                "zeit": zeit,
                "titel": titel,
                "quelle": "CNBC Live",
                "link": link
            })
        return news_list
    except Exception as e:
        return [{"zeit": "--:--", "titel": f"Warte auf News-Update... ({str(e)})", "quelle": "System", "link": "#"}]

# Spalten-Layout für das Dashboard
col1, col2 = st.columns(2)

with col1:
    st.subheader("🗓️ Wirtschaftskalender (Smarte Logik)")
    st.write("Färbung nach echter Marktauswirkung (bärisch = rot, bullisch = grün)")
    
    mock_data = [
        {"Zeit": "14:30", "Event": "US-Core CPI (Inflation) MoM", "Prognose": "0.2%", "Aktuell": "0.4%", "Impact": "High", "Type": "CPI"},
        {"Zeit": "16:00", "Event": "ISM Manufacturing PMI", "Prognose": "48.5", "Aktuell": "47.2", "Impact": "High", "Type": "Growth"}
    ]
    
    for ev in mock_data:
        with st.container(border=True):
            color = "white"
            direction = "NEUTRAL"
            
            if ev["Type"] == "CPI" and float(ev["Aktuell"].replace("%","")) > float(ev["Prognose"].replace("%","")):
                color = "#FF4B4B"
                direction = "BÄRISCH (Höhere Inflation = Zinsdruck)"
            elif ev["Type"] == "Growth" and float(ev["Aktuell"]) < float(ev["Prognose"]):
                color = "#FF4B4B"
                direction = "BÄRISCH (Wirtschaft kühlt ab)"
                
            st.markdown(f"### {ev['Zeit']} - {ev['Event']}")
            st.markdown(f"**Prognose:** {ev['Prognose']} | **Aktuell:** <span style='color:{color}; font-weight:bold;'>{ev['Aktuell']}</span>", unsafe_allow_html=True)
            st.caption(f"Auswirkung: {ev['Impact']} | Signal: {direction}")

with col2:
    st.subheader("📰 Live Global News Feed")
    st.write("Echtzeit-Meldungen aus dem globalen Markt:")
    
    live_news = get_live_news()
    for news in live_news:
        with st.container(border=True):
            st.markdown(f"**[{news['zeit']}] {news['titel']}**")
            st.caption(f"Quelle: {news['quelle']} | [Artikel lesen]({news['link']})")
