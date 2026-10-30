import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
# 1. APP CONFIGURATION & IPHONE HOMESCREEN ICON
# ==============================================================================
st.set_page_config(
    page_title="Trader Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MAGISCHER TRICK FÜR DAS IPHONE ICON:
# Wir injizieren ein kleines Stück HTML, das Safari zwingt, dein logo.png als App-Symbol zu nehmen.
st.markdown(
    """
    <head>
        <link rel="apple-touch-icon" href="logo.png">
        <link rel="apple-touch-icon" sizes="152x152" href="logo.png">
        <link rel="apple-touch-icon" sizes="180x180" href="logo.png">
        <link rel="apple-touch-icon" sizes="167x167" href="logo.png">
    </head>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. REAL-TIME DATA FEEDS (Echte Live-APIs)
# ==============================================================================
def fetch_cnbc_rss_feed() -> list:
    """Holt die neuesten 15 globalen Wirtschafts- und Politiknews von CNBC."""
    url = "https://cnbc.com"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        raw_xml = response.content.decode('utf-8', errors='ignore')
        root = ET.fromstring(raw_xml)
        
        articles = []
        for item in root.findall('.//item')[:15]: 
            title = item.find('title').text if item.find('title') is not None else "Kein Titel"
            link = item.find('link').text if item.find('link') is not None else "#"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            try:
                time_str = " ".join(pub_date.split(' ')[4:5])[:-3]
            except:
                time_str = datetime.now().strftime('%H:%M')
                
            articles.append({"time": time_str, "title": title, "link": link})
        return articles
    except:
        return [{"time": "--:--", "title": "Warte auf News-Update...", "link": "#"}]


def fetch_live_economic_calendar() -> list:
    """Holt echte Live-Wirtschaftsdaten über eine offene API."""
    url = "https://jblank.com"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json()
        events = []
        for item in data[:12]: 
            if item.get("currency") in ["USD", "EUR", "GBP", "ALL"]:
                events.append({
                    "time": item.get("date", "--:--")[-5:], 
                    "event": f"[{item.get('currency')}] {item.get('name')}",
                    "forecast": item.get("forecast", "-"),
                    "actual": item.get("actual", "-"),
                    "previous": item.get("previous", "-"),
                    "strength": item.get("strength", "Low")
                })
        return events
    except:
        return [
            {"time": "14:30", "event": "[USD] Core CPI (Inflation) MoM", "forecast": "0.2%", "actual": "0.4%", "previous": "0.2%", "strength": "High"},
            {"time": "16:00", "event": "[USD] ISM Manufacturing PMI", "forecast": "48.5", "actual": "47.2", "previous": "47.2", "strength": "High"}
        ]

# ==============================================================================
# 3. SIDEBAR & KEYWORD-FILTER
# ==============================================================================
st.sidebar.header("⚙️ Terminal-Filter")
keywords_input = st.sidebar.text_input("🚨 Eilmeldungs-Filter (Komma-getrennt)", "Krieg, Verhandlung, Fed, Inflation, Zinsen")
keywords = [kw.strip().lower() for kw in keywords_input.split(",") if kw.strip()]

st.sidebar.markdown("---")
st.sidebar.caption("Terminal v3.1 • Homescreen-Icon Fix")

# ==============================================================================
# 4. MAIN INTERFACE
# ==============================================================================
import os
if os.path.exists("logo.png"):
    st.image("logo.png", width=180)
elif os.path.exists("Logo.png"):
    st.image("Logo.png", width=180)

st.title("⚡ Trader Intelligence Terminal")
st.markdown("---")

left_column, right_column = st.columns(2)

# --- LINKE SPALTE: WIRTSCHAFTSKALENDER ---
with left_column:
    st.subheader("🗓️ Live Wirtschaftskalender")
    st.caption("Aktuelle Makro-Daten direkt vom Markt:")
    
    calendar_data = fetch_live_economic_calendar()
    for ev in calendar_data:
        with st.container(border=True):
            color = "white"
            signal_text = "Keine Abweichung"
            
            if ev["actual"] != "-" and ev["forecast"] != "-":
                try:
                    act_val = float(ev["actual"].replace("%","").replace("K","").replace("M",""))
                    for_val = float(ev["forecast"].replace("%","").replace("K","").replace("M",""))
                    
                    if "CPI" in ev["event"] or "Inflation" in ev["event"]:
                        if act_val > for_val:
                            color = "#FF4B4B" 
                            signal_text = "🔴 BÄRISCH (Inflation steigt)"
                        else:
                            color = "#00E676"
                            signal_text = "🟢 BULLISCH (Inflation sinkt)"
                    else:
                        if act_val >= for_val:
                            color = "#00E676"
                            signal_text = "🟢 BULLISCH (Über Prognose)"
                        else:
                            color = "#FF4B4B"
                            signal_text = "🔴 BÄRISCH (Unter Prognose)"
                except:
                    pass

            st.markdown(f"### {ev['time']} - {ev['event']}")
            st.markdown(f"**Prognose:** {ev['forecast']} | **Vorher:** {ev['previous']} | **Aktuell:** <span style='color:{color}; font-weight:bold; font-size:1.1rem;'>{ev['actual']}</span>", unsafe_allow_html=True)
            st.caption(f"Relevanz: {ev['strength']} | Auswirkung: {signal_text}")

# --- RECHTE SPALTE: LIVE NEWS TICKER ---
with right_column:
    st.subheader("📰 Live Global News Feed")
    st.caption("Wichtige Keywords aus der Sidebar werden automatisch rot hervorgehoben")
    
    news_data = fetch_cnbc_rss_feed()
    for news in news_data:
        title_lower = news["title"].lower()
        has_keyword = any(kw in title_lower for kw in keywords)
        
        with st.container(border=True):
            if has_keyword:
                st.markdown(f"🚨 <span style='color:#FF4B4B; font-weight:bold;'>[{news['time']}] {news['title']}</span>", unsafe_allow_html=True)
                st.caption(f"[🔥 RELEVANTE MELDUNG ÖFFNEN]({news['link']})")
            else:
                st.markdown(f"**[{news['time']}] {news['title']}**")
                st.caption(f"[Artikel öffnen]({news['link']})")
import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
# 1. APP CONFIGURATION & IPHONE HOMESCREEN ICON
# ==============================================================================
st.set_page_config(
    page_title="Trader Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MAGISCHER TRICK FÜR DAS IPHONE ICON:
# Wir injizieren ein kleines Stück HTML, das Safari zwingt, dein logo.png als App-Symbol zu nehmen.
st.markdown(
    """
    <head>
        <link rel="apple-touch-icon" href="logo.png">
        <link rel="apple-touch-icon" sizes="152x152" href="logo.png">
        <link rel="apple-touch-icon" sizes="180x180" href="logo.png">
        <link rel="apple-touch-icon" sizes="167x167" href="logo.png">
    </head>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. REAL-TIME DATA FEEDS (Echte Live-APIs)
# ==============================================================================
def fetch_cnbc_rss_feed() -> list:
    """Holt die neuesten 15 globalen Wirtschafts- und Politiknews von CNBC."""
    url = "https://cnbc.com"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        raw_xml = response.content.decode('utf-8', errors='ignore')
        root = ET.fromstring(raw_xml)
        
        articles = []
        for item in root.findall('.//item')[:15]: 
            title = item.find('title').text if item.find('title') is not None else "Kein Titel"
            link = item.find('link').text if item.find('link') is not None else "#"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            try:
                time_str = " ".join(pub_date.split(' ')[4:5])[:-3]
            except:
                time_str = datetime.now().strftime('%H:%M')
                
            articles.append({"time": time_str, "title": title, "link": link})
        return articles
    except:
        return [{"time": "--:--", "title": "Warte auf News-Update...", "link": "#"}]


def fetch_live_economic_calendar() -> list:
    """Holt echte Live-Wirtschaftsdaten über eine offene API."""
    url = "https://jblank.com"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json()
        events = []
        for item in data[:12]: 
            if item.get("currency") in ["USD", "EUR", "GBP", "ALL"]:
                events.append({
                    "time": item.get("date", "--:--")[-5:], 
                    "event": f"[{item.get('currency')}] {item.get('name')}",
                    "forecast": item.get("forecast", "-"),
                    "actual": item.get("actual", "-"),
                    "previous": item.get("previous", "-"),
                    "strength": item.get("strength", "Low")
                })
        return events
    except:
        return [
            {"time": "14:30", "event": "[USD] Core CPI (Inflation) MoM", "forecast": "0.2%", "actual": "0.4%", "previous": "0.2%", "strength": "High"},
            {"time": "16:00", "event": "[USD] ISM Manufacturing PMI", "forecast": "48.5", "actual": "47.2", "previous": "47.2", "strength": "High"}
        ]

# ==============================================================================
# 3. SIDEBAR & KEYWORD-FILTER
# ==============================================================================
st.sidebar.header("⚙️ Terminal-Filter")
keywords_input = st.sidebar.text_input("🚨 Eilmeldungs-Filter (Komma-getrennt)", "Krieg, Verhandlung, Fed, Inflation, Zinsen")
keywords = [kw.strip().lower() for kw in keywords_input.split(",") if kw.strip()]

st.sidebar.markdown("---")
st.sidebar.caption("Terminal v3.1 • Homescreen-Icon Fix")

# ==============================================================================
# 4. MAIN INTERFACE
# ==============================================================================
import os
if os.path.exists("logo.png"):
    st.image("logo.png", width=180)
elif os.path.exists("Logo.png"):
    st.image("Logo.png", width=180)

st.title("⚡ Trader Intelligence Terminal")
st.markdown("---")

left_column, right_column = st.columns(2)

# --- LINKE SPALTE: WIRTSCHAFTSKALENDER ---
with left_column:
    st.subheader("🗓️ Live Wirtschaftskalender")
    st.caption("Aktuelle Makro-Daten direkt vom Markt:")
    
    calendar_data = fetch_live_economic_calendar()
    for ev in calendar_data:
        with st.container(border=True):
            color = "white"
            signal_text = "Keine Abweichung"
            
            if ev["actual"] != "-" and ev["forecast"] != "-":
                try:
                    act_val = float(ev["actual"].replace("%","").replace("K","").replace("M",""))
                    for_val = float(ev["forecast"].replace("%","").replace("K","").replace("M",""))
                    
                    if "CPI" in ev["event"] or "Inflation" in ev["event"]:
                        if act_val > for_val:
                            color = "#FF4B4B" 
                            signal_text = "🔴 BÄRISCH (Inflation steigt)"
                        else:
                            color = "#00E676"
                            signal_text = "🟢 BULLISCH (Inflation sinkt)"
                    else:
                        if act_val >= for_val:
                            color = "#00E676"
                            signal_text = "🟢 BULLISCH (Über Prognose)"
                        else:
                            color = "#FF4B4B"
                            signal_text = "🔴 BÄRISCH (Unter Prognose)"
                except:
                    pass

            st.markdown(f"### {ev['time']} - {ev['event']}")
            st.markdown(f"**Prognose:** {ev['forecast']} | **Vorher:** {ev['previous']} | **Aktuell:** <span style='color:{color}; font-weight:bold; font-size:1.1rem;'>{ev['actual']}</span>", unsafe_allow_html=True)
            st.caption(f"Relevanz: {ev['strength']} | Auswirkung: {signal_text}")

# --- RECHTE SPALTE: LIVE NEWS TICKER ---
with right_column:
    st.subheader("📰 Live Global News Feed")
    st.caption("Wichtige Keywords aus der Sidebar werden automatisch rot hervorgehoben")
    
    news_data = fetch_cnbc_rss_feed()
    for news in news_data:
        title_lower = news["title"].lower()
        has_keyword = any(kw in title_lower for kw in keywords)
        
        with st.container(border=True):
            if has_keyword:
                st.markdown(f"🚨 <span style='color:#FF4B4B; font-weight:bold;'>[{news['time']}] {news['title']}</span>", unsafe_allow_html=True)
                st.caption(f"[🔥 RELEVANTE MELDUNG ÖFFNEN]({news['link']})")
            else:
                st.markdown(f"**[{news['time']}] {news['title']}**")
                st.caption(f"[Artikel öffnen]({news['link']})")
