import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================================================================
# 1. APP CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Trader Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vollständiger Raw-Link zum Logo im Repo
LOGO_URL = "https://raw.githubusercontent.com/madsacksven-ai/trader-app/main/logo.png"

# Echter CNBC-RSS-Feed (Top News)
CNBC_RSS_URL = "https://www.cnbc.com/id/100003114/device/rss/rss.html"

# ==============================================================================
# 2. DATA FEEDS (mit Cache: werden nur alle paar Minuten neu geladen)
# ==============================================================================
@st.cache_data(ttl=120, show_spinner=False)
def fetch_cnbc_rss_feed() -> list:
    """Holt die neuesten 15 Wirtschaftsnews von CNBC. Ergebnis wird 2 Minuten gecacht."""
    try:
        response = requests.get(CNBC_RSS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        root = ET.fromstring(response.content)

        articles = []
        for item in root.findall(".//item")[:15]:
            title = item.findtext("title", default="Kein Titel")
            link = item.findtext("link", default="#")
            pub_date = item.findtext("pubDate", default="")

            try:
                # RSS-Format: "Sat, 31 Oct 2026 14:05:00 GMT" -> "14:05"
                time_str = pub_date.split(" ")[4][:5]
            except Exception:
                time_str = datetime.now().strftime("%H:%M")

            articles.append({"time": time_str, "title": title, "link": link})
        return articles
    except Exception as e:
        return [{"time": "--:--", "title": f"Warte auf News-Update... ({e})", "link": "#"}]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_economic_calendar() -> list:
    """Wirtschaftskalender (aktuell statische Beispieldaten, ohne unnötige Web-Anfrage)."""
    return [
        {"time": "14:30", "event": "[USD] Core CPI (Inflation) MoM", "forecast": "0.2%", "actual": "0.4%", "previous": "0.2%", "strength": "High"},
        {"time": "16:00", "event": "[USD] ISM Manufacturing PMI", "forecast": "48.5", "actual": "47.2", "previous": "47.2", "strength": "High"},
        {"time": "18:00", "event": "[EUR] ECB President Lagarde Speaks", "forecast": "-", "actual": "-", "previous": "-", "strength": "Medium"},
    ]

# ==============================================================================
# 3. SIDEBAR & KEYWORD-FILTER
# ==============================================================================
st.sidebar.header("⚙️ Terminal-Filter")
keywords_input = st.sidebar.text_input(
    "🚨 Eilmeldungs-Filter (Komma-getrennt)",
    "Krieg, Verhandlung, Fed, Inflation, Zinsen"
)
keywords = [kw.strip().lower() for kw in keywords_input.split(",") if kw.strip()]

if st.sidebar.button("🔄 News jetzt aktualisieren"):
    fetch_cnbc_rss_feed.clear()

st.sidebar.markdown("---")
st.sidebar.caption("Terminal v3.5 • Verified Assets")

# ==============================================================================
# 4. MAIN INTERFACE
# ==============================================================================
st.image(LOGO_URL, width=140)
st.title("⚡ Trader Intelligence Terminal")
st.markdown("---")

left_column, right_column = st.columns(2)

# --- LINKE SPALTE: WIRTSCHAFTSKALENDER ---
with left_column:
    st.subheader("🗓️ Live Wirtschaftskalender")
    st.caption("Aktuelle Makro-Daten direkt vom Markt:")

    for ev in fetch_live_economic_calendar():
        with st.container(border=True):
            color = "white"
            signal_text = "Keine Abweichung"

            if ev["actual"] != "-" and ev["forecast"] != "-":
                try:
                    act_val = float(ev["actual"].replace("%", "").replace("K", "").replace("M", ""))
                    for_val = float(ev["forecast"].replace("%", "").replace("K", "").replace("M", ""))

                    if "CPI" in ev["event"] or "Inflation" in ev["event"]:
                        if act_val > for_val:
                            color, signal_text = "#FF4B4B", "🔴 BÄRISCH (Inflation steigt)"
                        else:
                            color, signal_text = "#00E676", "🟢 BULLISCH (Inflation sinkt)"
                    else:
                        if act_val >= for_val:
                            color, signal_text = "#00E676", "🟢 BULLISCH (Über Prognose)"
                        else:
                            color, signal_text = "#FF4B4B", "🔴 BÄRISCH (Unter Prognose)"
                except Exception:
                    pass

            st.markdown(f"### {ev['time']} - {ev['event']}")
            st.markdown(
                f"**Prognose:** {ev['forecast']} | **Vorher:** {ev['previous']} | "
                f"**Aktuell:** <span style='color:{color}; font-weight:bold; font-size:1.1rem;'>{ev['actual']}</span>",
                unsafe_allow_html=True
            )
            st.caption(f"Relevanz: {ev['strength']} | Auswirkung: {signal_text}")

# --- RECHTE SPALTE: LIVE NEWS TICKER ---
with right_column:
    st.subheader("📰 Live Global News Feed")
    st.caption("Wichtige Keywords aus der Sidebar werden automatisch rot hervorgehoben")

    for news in fetch_cnbc_rss_feed():
        has_keyword = any(kw in news["title"].lower() for kw in keywords)

        with st.container(border=True):
            if has_keyword:
                st.markdown(
                    f"🚨 <span style='color:#FF4B4B; font-weight:bold;'>[{news['time']}] {news['title']}</span>",
                    unsafe_allow_html=True
                )
                st.caption(f"[🔥 RELEVANTE MELDUNG ÖFFNEN]({news['link']})")
            else:
                st.markdown(f"**[{news['time']}] {news['title']}**")
                st.caption(f"[Artikel öffnen]({news['link']})")
