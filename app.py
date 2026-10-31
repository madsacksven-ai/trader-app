import csv
import html
import re
from datetime import datetime
from pathlib import Path
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

try:
    from deep_translator import GoogleTranslator
except Exception:  # Paket fehlt -> App läuft ohne Übersetzung weiter
    GoogleTranslator = None

# ==============================================================================
# 1. GRUNDEINSTELLUNGEN
# ==============================================================================
st.set_page_config(
    page_title="Trader Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BERLIN = ZoneInfo("Europe/Berlin")
NEW_YORK = ZoneInfo("America/New_York")
SYMBOL = "NQ=F"  # Nasdaq-100 Future (Front-Monat), Yahoo-Daten mit kurzer Verzögerung
LOGO_URL = "https://raw.githubusercontent.com/madsacksven-ai/trader-app/main/logo.png"
NEWS_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Top News
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",   # Economy
]
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

BULL, BEAR, NEUTRAL = "#34d399", "#f87171", "#c3c9d3"
AMBER = "#f5b544"

# ==============================================================================
# 2. DESIGN (kompakt, dunkel)
# ==============================================================================
st.markdown(
    f"""
<style>
.stApp {{ background: #0b0e14; }}
.block-container {{ padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }}
h1, h2, h3 {{ margin: 0 !important; }}
.tt-head {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }}
.tt-brand {{ display:flex; align-items:center; gap:10px; }}
.tt-brand img {{ width:34px; height:34px; border-radius:8px; }}
.tt-title {{ font-weight:700; font-size:17px; color:#e6e9ef; }}
.tt-sub {{ font-size:12px; color:#9aa4b2; }}
.tt-live {{ font-size:11px; color:#9aa4b2; display:flex; align-items:center; gap:6px; }}
.tt-dot {{ width:8px; height:8px; border-radius:50%; background:{BULL}; display:inline-block; }}
.tt-price {{ font-family:'JetBrains Mono', ui-monospace, monospace; font-size:26px; font-weight:600; color:#e6e9ef; }}
.tt-chg {{ font-family:'JetBrains Mono', ui-monospace, monospace; font-size:14px; margin-left:10px; }}
.tt-h2 {{ font-size:13px; font-weight:700; color:#e6e9ef; display:flex; justify-content:space-between; align-items:baseline; margin:8px 0 6px; }}
.tt-h2 span {{ font-size:10px; font-weight:400; color:#9aa4b2; }}
.tt-card {{ background:#131822; border:1px solid #232a36; border-radius:12px; padding:10px 12px; }}
.tt-pills {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:6px; margin:8px 0 2px; }}
.tt-pill {{ background:#0f131b; border-radius:8px; padding:7px 8px; font-size:11px; color:#9aa4b2; }}
.tt-pill b {{ display:block; font-size:12px; margin-top:2px; }}
.tt-bars {{ display:flex; gap:3px; align-items:center; font-size:12px; color:#9aa4b2; justify-content:space-between; }}
.tt-bar {{ width:24px; height:6px; border-radius:3px; display:inline-block; margin-left:3px; }}
.tt-cal {{ background:#131822; border:1px solid #232a36; border-radius:12px; overflow:hidden; }}
.tt-row {{ display:grid; grid-template-columns:44px minmax(0,1fr) 112px 18px; gap:8px; padding:7px 10px; font-size:12px; align-items:center; border-bottom:1px solid #1c2230; color:#e6e9ef; }}
.tt-row:last-child {{ border-bottom:none; }}
.tt-row.tt-hd {{ font-size:9px; color:#8a94a3; padding:6px 10px; }}
.tt-mono {{ font-family:'JetBrains Mono', ui-monospace, monospace; }}
.tt-muted {{ color:#9aa4b2; }}
.tt-imp {{ font-size:9px; display:block; }}
.tt-vals {{ font-size:10px; line-height:1.3; }}
.tt-note {{ font-size:10px; color:#8a94a3; }}

/* Analyse-Zeitraum und Chart-Zeitrahmen als kleine Schalter */
div[data-testid="stRadio"] label p {{ font-size:12px; }}
div[data-testid="stRadio"] > div {{ gap:4px; }}

/* News-Karten sind selbst Buttons: antippen = Artikel öffnen */
div[class*="st-key-nline_"] button, div.st-key-news_top button, div.st-key-gal_card button {{
  width:100%; justify-content:flex-start; text-align:left; background:#131822;
  border:1px solid #232a36; border-radius:10px; padding:7px 10px; min-height:42px; color:#e6e9ef; }}
div[class*="st-key-nline_"] button p, div.st-key-gal_card button p {{ font-size:12px; text-align:left; line-height:1.35; }}
div[class*="st-key-nline_kw"] button {{ border-color:{AMBER}; }}
div.st-key-news_top button, div.st-key-gal_card button {{ flex-direction:column; align-items:flex-start; gap:4px; border-radius:12px; padding:10px 12px; }}
div.st-key-news_top button {{ background:#1a1f12; border-color:{AMBER}; }}
div.st-key-news_top button p {{ font-size:14px; font-weight:600; text-align:left; line-height:1.35; }}
div.st-key-news_top button::before, div.st-key-gal_card button::before {{
  display:block; font-size:10px; font-weight:700; letter-spacing:0.03em; }}
div.st-key-news_top button::before {{ color:{AMBER}; }}
div.st-key-gal_card button::before {{ color:#9aa4b2; }}
div.st-key-gal_card button {{ min-height:84px; }}
div.st-key-galnav div[data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; gap:6px; }}
div.st-key-galnav div[data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 0 !important; }}
div.st-key-galnav button {{ width:100%; min-height:40px; background:#131822; border:1px solid #2a3344; color:#e6e9ef; }}
div[data-testid="stExpander"] details {{ background:#0f131b; border:1px solid #232a36; border-radius:10px; }}
div[data-testid="stExpander"] summary p {{ font-size:12px; font-weight:600; }}
</style>
""",
    unsafe_allow_html=True,
)


def e(text) -> str:
    """Text sicher für HTML machen."""
    return html.escape(str(text))


def bias_style(score: int):
    if score > 0:
        return "▲", "Bullisch", BULL
    if score < 0:
        return "▼", "Bärisch", BEAR
    return "●", "Neutral", NEUTRAL


def md_arrow(score: int) -> str:
    """Farbiger Pfeil für Button-Beschriftungen."""
    if score > 0:
        return ":green[▲]"
    if score < 0:
        return ":red[▼]"
    return ":gray[●]"


def md_safe(text: str) -> str:
    """Zeichen entschärfen, die Streamlit sonst als Formatierung liest (z. B. $ als Formel)."""
    for ch in ["\\", "$", "*", "_", "`", "[", "]", "#", "~"]:
        text = text.replace(ch, "\\" + ch)
    return text


def css_text(text: str) -> str:
    """Text sicher für CSS content:"…" machen."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("<", "")


# ==============================================================================
# MEINE ZONEN (aus der Datei zones.csv im GitHub-Repo)
# ==============================================================================
ZONE_COLORS = {
    "gruen": "52,211,153", "grün": "52,211,153", "rot": "248,113,113", "blau": "124,196,255",
    "gelb": "245,181,68", "orange": "251,146,60", "grau": "156,163,175", "lila": "192,132,252",
}


def to_price(val: str):
    s = (val or "").strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:      # 21.050,5 -> 21050.5
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                 # 21050,5 -> 21050.5
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_zones() -> list:
    """Liest zones.csv: Name;Von;Bis;Farbe (Von = Bis ergibt eine Linie)."""
    path = Path(__file__).parent / "zones.csv"
    if not path.exists():
        return []
    zones = []
    try:
        with path.open(encoding="utf-8-sig") as f:
            for row in csv.reader(f, delimiter=";"):
                if len(row) < 2 or row[0].strip().lower() in ("name", "") or row[0].startswith("#"):
                    continue
                lo = to_price(row[1])
                hi = to_price(row[2]) if len(row) > 2 else lo
                hi = lo if hi is None else hi
                if lo is None:
                    continue
                rgb = ZONE_COLORS.get(row[3].strip().lower() if len(row) > 3 else "", ZONE_COLORS["blau"])
                zones.append({"name": row[0].strip(), "lo": min(lo, hi), "hi": max(lo, hi), "rgb": rgb})
    except Exception:
        return []
    return zones


# ==============================================================================
# 3. ÜBERSETZUNG (Englisch -> Deutsch)
# ==============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def translate_text(text: str) -> str:
    if not text or GoogleTranslator is None:
        return text
    try:
        out = GoogleTranslator(source="en", target="de").translate(text[:4800])
        return out or text
    except Exception:
        return text


@st.cache_data(ttl=86400, show_spinner=False)
def translate_many(texts: tuple) -> list:
    """Übersetzt viele kurze Texte (Schlagzeilen) in EINER Anfrage."""
    if not texts or GoogleTranslator is None:
        return list(texts)
    try:
        joined = "\n".join(t.replace("\n", " ") for t in texts)
        out = GoogleTranslator(source="en", target="de").translate(joined[:4800]) or ""
        parts = [p.strip() for p in out.split("\n") if p.strip()]
        if len(parts) == len(texts):
            return parts
    except Exception:
        pass
    return [translate_text(t) for t in texts]  # Rückfall: einzeln übersetzen


def translate_paragraphs(paragraphs: list) -> list:
    """Längere Texte in Stücken unter 4500 Zeichen übersetzen."""
    result, chunk = [], []
    for p in paragraphs + [None]:
        if p is None or sum(len(x) for x in chunk) + len(p) > 4500:
            if chunk:
                out = translate_text("\n\n".join(chunk))
                result.extend([x.strip() for x in out.split("\n\n") if x.strip()])
                chunk = []
        if p is not None:
            chunk.append(p)
    return result


# ==============================================================================
# 4. DATEN: KURSE
# ==============================================================================
TIMEFRAMES = {"5m": ("5m", "2d"), "15m": ("15m", "5d"), "1h": ("1h", "1mo"), "1T": ("1d", "6mo")}


@st.cache_data(ttl=60, show_spinner=False)
def load_prices(interval: str, period: str) -> pd.DataFrame:
    try:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False, auto_adjust=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
    except Exception:
        return pd.DataFrame()


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP der aktuellen Handelssitzung (Start 18:00 New Yorker Zeit)."""
    if df.empty or "Volume" not in df:
        return pd.Series(dtype=float)
    ny = df.index.tz_convert(NEW_YORK)
    session = (ny + pd.Timedelta(hours=6)).date
    typical = ((df["High"] + df["Low"] + df["Close"]) / 3).astype(float)
    vol = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0).astype(float)
    grp = pd.Series(session, index=df.index)
    pv = (typical * vol).groupby(grp).cumsum()
    vv = vol.groupby(grp).cumsum()
    # Ohne Volumen (z. B. Wochenende) gibt es keinen VWAP -> leer statt Absturz
    return (pv / vv.where(vv > 0)).astype(float)


# ==============================================================================
# 5. DATEN: NEWS
# ==============================================================================
BULL_WORDS = [
    "rally", "rallies", "surge", "soar", "jump", "gain", "record high", "beats", "beat estimates",
    "rate cut", "cuts rates", "cooling", "cools", "eases", "easing", "upgrade", "rebound",
    "stimulus", "ceasefire", "deal reached", "strong earnings", "optimism", "higher",
]
BEAR_WORDS = [
    "fall", "falls", "drop", "slump", "plunge", "tumble", "sell-off", "selloff", "misses",
    "rate hike", "hikes", "hot inflation", "inflation rises", "sticky inflation", "tariff",
    "war", "attack", "recession", "layoffs", "downgrade", "fears", "warning", "shutdown",
    "lower", "crash", "sanctions", "default",
]


def news_score(title: str) -> int:
    t = title.lower()
    s = sum(1 for w in BULL_WORDS if w in t) - sum(1 for w in BEAR_WORDS if w in t)
    return max(-2, min(2, s))


@st.cache_data(ttl=120, show_spinner=False)
def load_news() -> list:
    items, seen = [], set()
    for url in NEWS_FEEDS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=4)
            root = ET.fromstring(r.content)
        except Exception:
            continue
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            try:
                dt = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(BERLIN)
            except Exception:
                dt = None
            items.append({
                "title": title,
                "link": it.findtext("link") or "#",
                "desc": re.sub(r"<[^>]+>", "", it.findtext("description") or "").strip(),
                "dt": dt,
                "score": news_score(title),  # Einschätzung anhand der englischen Originalwörter
            })
    items.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=BERLIN), reverse=True)
    items = items[:25]

    # Schlagzeilen gesammelt ins Deutsche übersetzen
    titles_de = translate_many(tuple(n["title"] for n in items))
    for n, de in zip(items, titles_de):
        n["title_de"] = de
    return items


@st.cache_data(ttl=3600, show_spinner=False)
def load_article(url: str) -> list:
    """Holt den Artikeltext (Absätze) von der CNBC-Seite."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=6)
        page = r.text
    except Exception:
        return []
    start = page.find("ArticleBody")
    body = page[start:] if start >= 0 else page
    paras = re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.S)
    clean = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in paras]
    return [p for p in clean if len(p) > 40][:15]


# ==============================================================================
# 6. DATEN: WIRTSCHAFTSKALENDER
# ==============================================================================
INFLATION_KEYS = ["cpi", "ppi", "pce", "inflation", "average hourly earnings", "import prices"]
GROWTH_KEYS = ["non-farm", "nonfarm", "ism", "pmi", "retail sales", "gdp", "consumer confidence", "durable"]
JOBLESS_KEYS = ["unemployment", "jobless claims"]


def calendar_direction(title: str) -> int:
    t = title.lower()
    if any(k in t for k in INFLATION_KEYS):
        return -1
    if any(k in t for k in JOBLESS_KEYS):
        return -1
    if any(k in t for k in GROWTH_KEYS):
        return 1
    return 0


def to_number(val):
    if val in (None, "", "-"):
        return None
    try:
        s = str(val).replace("%", "").replace(",", "")
        mult = 1
        if s.endswith("K"):
            s, mult = s[:-1], 1e3
        elif s.endswith("M"):
            s, mult = s[:-1], 1e6
        elif s.endswith("B"):
            s, mult = s[:-1], 1e9
        return float(s) * mult
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def load_calendar() -> list:
    try:
        r = requests.get(CALENDAR_URL, headers=HEADERS, timeout=5)
        raw = r.json()
    except Exception:
        return []
    events = []
    for ev in raw:
        if ev.get("country") not in ("USD", "EUR"):
            continue
        if ev.get("impact") not in ("High", "Medium"):
            continue
        try:
            dt = datetime.fromisoformat(ev["date"]).astimezone(BERLIN)
        except Exception:
            continue
        actual, forecast = ev.get("actual", ""), ev.get("forecast", "")
        a, f = to_number(actual), to_number(forecast)
        sig = 0
        if a is not None and f is not None and a != f:
            sig = calendar_direction(ev.get("title", "")) * (1 if a > f else -1)
        events.append({
            "dt": dt,
            "title": f"{ev['country']} {ev.get('title', '')}",
            "impact": ev.get("impact"),
            "forecast": forecast or "–",
            "actual": actual or "–",
            "previous": ev.get("previous") or "–",
            "signal": sig,
        })
    events.sort(key=lambda x: x["dt"])
    return events


# ==============================================================================
# 7. ANALYSE: BIAS FÜR TAG / WOCHE / MONAT
# ==============================================================================
def clamp(v, lo=-3, hi=3):
    return max(lo, min(hi, v))


def tech_day(df: pd.DataFrame, vwap: pd.Series, prev_close):
    reasons, score = [], 0
    if df.empty:
        return 0, ["Keine Intraday-Kursdaten verfügbar."]
    last = float(df["Close"].iloc[-1])
    if len(vwap.dropna()):
        v = float(vwap.dropna().iloc[-1])
        score += 1 if last > v else -1
        reasons.append(f"Kurs {'über' if last > v else 'unter'} dem VWAP ({v:,.0f}).")
    if len(df) >= 50:
        ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
        score += 1 if ema20 > ema50 else -1
        reasons.append("5-Min-Trend " + ("aufwärts (EMA 20 über EMA 50)." if ema20 > ema50
                                        else "abwärts (EMA 20 unter EMA 50)."))
    if prev_close:
        score += 1 if last > prev_close else -1
        reasons.append(f"Kurs {'über' if last > prev_close else 'unter'} dem Vortagesschluss ({prev_close:,.0f}).")
    return score, reasons


def tech_week(daily: pd.DataFrame):
    if len(daily) < 25:
        return 0, ["Zu wenig Tagesdaten für die Wochenanalyse."]
    reasons, score = [], 0
    last = float(daily["Close"].iloc[-1])
    ny = daily.index.tz_convert(NEW_YORK)
    week = ny.isocalendar().week.values == ny[-1].isocalendar()[1]
    week_open = float(daily["Open"][week].iloc[0])
    score += 1 if last > week_open else -1
    reasons.append(f"Kurs {'über' if last > week_open else 'unter'} der Wochen-Eröffnung ({week_open:,.0f}).")
    sma20 = float(daily["Close"].rolling(20).mean().iloc[-1])
    score += 1 if last > sma20 else -1
    reasons.append(f"Kurs {'über' if last > sma20 else 'unter'} dem 20-Tage-Durchschnitt ({sma20:,.0f}).")
    five_ago = float(daily["Close"].iloc[-6])
    score += 1 if last > five_ago else -1
    reasons.append(f"Letzte 5 Handelstage: {(last / five_ago - 1) * 100:+.1f} %.")
    return score, reasons


def tech_month(daily: pd.DataFrame):
    if len(daily) < 60:
        return 0, ["Zu wenig Tagesdaten für die Monatsanalyse."]
    reasons, score = [], 0
    last = float(daily["Close"].iloc[-1])
    ny = daily.index.tz_convert(NEW_YORK)
    month = (ny.month == ny[-1].month) & (ny.year == ny[-1].year)
    month_open = float(daily["Open"][month].iloc[0])
    score += 1 if last > month_open else -1
    reasons.append(f"Kurs {'über' if last > month_open else 'unter'} der Monats-Eröffnung ({month_open:,.0f}).")
    sma50 = float(daily["Close"].rolling(50).mean().iloc[-1])
    score += 1 if last > sma50 else -1
    reasons.append(f"Kurs {'über' if last > sma50 else 'unter'} dem 50-Tage-Durchschnitt ({sma50:,.0f}).")
    if len(daily) >= 200:
        sma200 = float(daily["Close"].rolling(200).mean().iloc[-1])
        score += 1 if sma50 > sma200 else -1
        reasons.append("Langfristtrend " + ("aufwärts (50-Tage über 200-Tage-Linie)." if sma50 > sma200
                                           else "abwärts (50-Tage unter 200-Tage-Linie)."))
    return score, reasons


def calendar_analysis(events: list, horizon: str):
    now_ = datetime.now(BERLIN)
    if horizon == "Tag":
        pool = [ev for ev in events if ev["dt"].date() == now_.date()]
        span = "heute"
    else:
        pool = events  # der Kalender-Feed deckt die aktuelle Woche ab
        span = "diese Woche"
    released = [ev for ev in pool if ev["signal"] != 0]
    score = clamp(sum(ev["signal"] for ev in released), -2, 2)
    if released:
        reasons = [f"{ev['title']}: {ev['actual']} (Prognose {ev['forecast']}) – "
                   f"{'▲ gut' if ev['signal'] > 0 else '▼ schlecht'} für NQ." for ev in released[-4:]]
    else:
        upcoming = [ev for ev in pool if ev["dt"] >= now_ and ev["impact"] == "High"]
        reasons = ([f"Noch keine Ergebnisse {span}. Wichtig: " + ", ".join(
            f"{ev['dt']:%a %H:%M} {ev['title']}" for ev in upcoming[:3]) + "."]
            if upcoming else [f"Keine wichtigen Termine mit Ergebnis {span}."])
    return score, reasons


def news_analysis(news: list, horizon: str):
    if horizon == "Monat":
        return 0, ["Tagesnachrichten zählen für den Monatsausblick nicht mit."]
    recent = news[:12] if horizon == "Tag" else news[:25]
    score = sum(n["score"] for n in recent)
    bull = sum(1 for n in recent if n["score"] > 0)
    bear = sum(1 for n in recent if n["score"] < 0)
    reasons = [f"Letzte {len(recent)} Meldungen: {bull} positiv, {bear} negativ."] if recent \
        else ["Keine News verfügbar."]
    return (1 if score >= 2 else -1 if score <= -2 else 0), reasons


# ==============================================================================
# 8. ARTIKEL-POP-UP
# ==============================================================================
@st.dialog("Meldung", width="large")
def show_article(item: dict):
    a, l, c = bias_style(item["score"])
    when = f"{item['dt']:%d.%m. %H:%M}" if item.get("dt") else ""
    st.markdown(
        f'<div style="font-size:11px;color:#9aa4b2;display:flex;justify-content:space-between">'
        f'<span>CNBC · {when}</span><span style="color:{c};font-weight:700">{a} {l.upper()} für NQ</span></div>'
        f'<div style="font-size:18px;font-weight:700;line-height:1.3;margin:6px 0 2px">{e(item["title_de"])}</div>'
        f'<div style="font-size:11px;color:#8a94a3">Original: {e(item["title"])}</div>',
        unsafe_allow_html=True,
    )
    with st.spinner("Artikel wird geladen und übersetzt …"):
        paragraphs = load_article(item["link"])
        text_de = translate_paragraphs(paragraphs) if paragraphs else []
    if text_de:
        st.markdown("\n\n".join(text_de))
    elif item.get("desc"):
        st.markdown(translate_text(item["desc"]))
    else:
        st.info("Der Volltext ist für diese Meldung nicht abrufbar (z. B. Video oder Bezahlartikel).")
    st.markdown(f'<span class="tt-note">Automatisch übersetzt. '
                f'<a href="{e(item["link"])}" target="_blank">Original bei CNBC öffnen</a></span>',
                unsafe_allow_html=True)


# ==============================================================================
# 9. SIDEBAR
# ==============================================================================
st.sidebar.header("⚙️ Einstellungen")
keywords_input = st.sidebar.text_input(
    "Eilmeldungs-Filter (Komma-getrennt, Deutsch oder Englisch)",
    "Fed, Inflation, Zinsen, rate, Krieg, war, Zölle, tariff, Nasdaq",
)
keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
if st.sidebar.button("🔄 Alles aktualisieren"):
    st.cache_data.clear()
st.sidebar.caption("Kursdaten: Yahoo Finance (verzögert) · News: CNBC · Kalender: ForexFactory · "
                   "Übersetzung: Google Translate")

# ==============================================================================
# 10. KOPFZEILE
# ==============================================================================
now = datetime.now(BERLIN)
st.markdown(
    f"""
<div class="tt-head">
  <div class="tt-brand"><img src="{LOGO_URL}" alt="">
    <div><div class="tt-title">Trader Terminal</div><div class="tt-sub">NQ · Nasdaq-100 Future</div></div>
  </div>
  <div class="tt-live"><span class="tt-dot"></span>{now:%d.%m. %H:%M}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 11. DATEN LADEN
# ==============================================================================
intraday = load_prices("5m", "2d")
daily = load_prices("1d", "1y")
prev_close = float(daily["Close"].iloc[-2]) if len(daily) >= 2 else None
vwap_intraday = session_vwap(intraday)
news = load_news()
calendar = load_calendar()

col_chart, col_analysis = st.columns([2.2, 1], gap="small")

# ==============================================================================
# 12. ANALYSE (rechts bzw. auf dem Handy unter dem Chart)
# ==============================================================================
with col_analysis:
    horizon = st.radio("Analyse für", ["Tag", "Woche", "Monat"], horizontal=True,
                       label_visibility="collapsed", key="horizon")

    if horizon == "Tag":
        t_score, t_reasons = tech_day(intraday, vwap_intraday, prev_close)
    elif horizon == "Woche":
        t_score, t_reasons = tech_week(daily)
    else:
        t_score, t_reasons = tech_month(daily)
    c_score, c_reasons = calendar_analysis(calendar, horizon)
    n_score, n_reasons = news_analysis(news, horizon)

    total = t_score + c_score + n_score
    bias_val = 1 if total >= 2 else -1 if total <= -2 else 0
    arrow, label, color = bias_style(bias_val)
    strength = 1 if abs(total) <= 2 else 2 if abs(total) <= 4 else 3
    strength_txt = {1: "schwach", 2: "mittel", 3: "stark"}[strength]
    horizon_word = {"Tag": "TAGES", "Woche": "WOCHEN", "Monat": "MONATS"}[horizon]

    bars = "".join(
        f'<span class="tt-bar" style="background:{color if i < strength else "#2a3344"}"></span>'
        for i in range(3)
    )

    def pill(name, s):
        a, l, c = bias_style(s)
        return f'<div class="tt-pill">{name}<b style="color:{c}">{a} {l.lower()}</b></div>'

    st.markdown(
        f"""
<div class="tt-card">
  <div class="tt-h2" style="margin-top:0">{horizon_word.capitalize()}-Bias <span>{now:%H:%M} Uhr</span></div>
  <div style="font-size:20px;font-weight:700;color:{color}">{arrow} {label}</div>
  <div class="tt-bars" style="margin-top:6px">Signalstärke <span>{bars}<span style="color:#e6e9ef;margin-left:6px">{strength_txt}</span></span></div>
  <div class="tt-pills">{pill("Technik", t_score)}{pill("Kalender", c_score)}{pill("News/Makro", n_score)}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    with st.expander(f"Warum {label.lower()}? Begründung"):
        st.markdown("**Technik**\n\n" + "\n".join(f"- {r}" for r in t_reasons))
        st.markdown("**Kalender**\n\n" + "\n".join(f"- {r}" for r in c_reasons))
        st.markdown("**News/Makro**\n\n" + "\n".join(f"- {r}" for r in n_reasons))
        st.markdown('<span class="tt-note">Automatische Einschätzung aus einfachen Regeln, '
                    'keine Anlageberatung.</span>', unsafe_allow_html=True)

# ==============================================================================
# 13. CHART
# ==============================================================================
with col_chart:
    tf = st.radio("Zeitrahmen", list(TIMEFRAMES), horizontal=True, label_visibility="collapsed", key="tf")
    interval, period = TIMEFRAMES[tf]
    prices = load_prices(interval, period)

    if prices.empty:
        st.warning("Kursdaten gerade nicht erreichbar. Bitte gleich noch einmal laden.")
    else:
        last = float(prices["Close"].iloc[-1])
        ref = prev_close or float(prices["Close"].iloc[0])
        chg = last - ref
        chg_pct = chg / ref * 100 if ref else 0
        chg_col = BULL if chg >= 0 else BEAR
        st.markdown(
            f'<div><span class="tt-price">{last:,.2f}</span>'
            f'<span class="tt-chg" style="color:{chg_col}">{chg:+,.2f} · {chg_pct:+.2f} %</span></div>',
            unsafe_allow_html=True,
        )

        show = prices.tail(160)
        x = show.index.tz_convert(BERLIN)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=x, open=show["Open"], high=show["High"], low=show["Low"], close=show["Close"],
            increasing_line_color=BULL, decreasing_line_color=BEAR,
            increasing_fillcolor=BULL, decreasing_fillcolor=BEAR, name="NQ",
        ))
        if tf in ("5m", "15m"):
            show_vwap = session_vwap(prices).reindex(show.index)
            fig.add_trace(go.Scatter(x=x, y=show_vwap, mode="lines", name="VWAP",
                                     line=dict(color=AMBER, width=1.3, dash="dot")))
        if prev_close and tf != "1T":
            fig.add_hline(y=prev_close, line=dict(color="#5b6578", width=1, dash="dash"),
                          annotation_text="Vortagesschluss", annotation_font_size=10,
                          annotation_font_color="#9aa4b2", annotation_position="bottom right")
        # Eigene Zonen und Linien aus zones.csv
        y_lo, y_hi = float(show["Low"].min()), float(show["High"].max())
        pad = (y_hi - y_lo) * 0.06 or 10
        for z in load_zones():
            if z["hi"] < y_lo - pad or z["lo"] > y_hi + pad:
                continue  # Zone liegt außerhalb des sichtbaren Bereichs
            if z["hi"] - z["lo"] < 0.01:
                fig.add_hline(y=z["lo"], line=dict(color=f"rgba({z['rgb']},0.9)", width=1.5),
                              annotation_text=z["name"], annotation_position="top left",
                              annotation_font_size=10, annotation_font_color=f"rgb({z['rgb']})")
            else:
                fig.add_hrect(y0=z["lo"], y1=z["hi"], fillcolor=f"rgba({z['rgb']},0.15)",
                              line=dict(color=f"rgba({z['rgb']},0.6)", width=1),
                              annotation_text=z["name"], annotation_position="top left",
                              annotation_font_size=10, annotation_font_color=f"rgb({z['rgb']})")

        fig.add_annotation(
            xref="paper", yref="paper", x=0.01, y=0.98, xanchor="left", yanchor="top",
            text=f"<span style='font-size:10px'>{horizon_word}-BIAS</span><br><b>{arrow} {label}</b>",
            showarrow=False, align="left", font=dict(color=color, size=15),
            bgcolor="rgba(15,19,27,0.9)", bordercolor=color, borderwidth=1, borderpad=6,
        )
        breaks = [dict(bounds=["sat", "mon"])]  # Wochenenden ausblenden
        fig.update_layout(
            height=330, margin=dict(l=0, r=0, t=4, b=0), showlegend=False,
            paper_bgcolor="#0f131b", plot_bgcolor="#0f131b",
            font=dict(color="#9aa4b2", size=10), xaxis_rangeslider_visible=False,
            xaxis=dict(gridcolor="#1c2230", rangebreaks=breaks),
            yaxis=dict(gridcolor="#1c2230", side="right", range=[y_lo - pad, y_hi + pad]),
            dragmode=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ==============================================================================
# 14. UNTEN: KALENDER LINKS, NEWS RECHTS
# ==============================================================================
col_cal, col_news = st.columns(2, gap="small")

with col_cal:
    today = now.date()
    todays = [ev for ev in calendar if ev["dt"].date() == today]
    if todays:
        shown, sub = todays, "Heute · USD/EUR"
    else:
        shown = [ev for ev in calendar if ev["dt"] >= now][:6]
        sub = "Heute nichts · nächste Termine"
    st.markdown(f'<div class="tt-h2">Wirtschaftskalender <span>{sub}</span></div>', unsafe_allow_html=True)

    if not calendar:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">Kalender gerade nicht erreichbar.</div>',
                    unsafe_allow_html=True)
    elif not shown:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">Keine weiteren Termine diese Woche.</div>',
                    unsafe_allow_html=True)
    else:
        rows = ['<div class="tt-row tt-hd"><span>ZEIT</span><span>EREIGNIS</span>'
                '<span>PROG / AKT / VORH</span><span></span></div>']
        for ev in shown:
            a, _, c = bias_style(ev["signal"])
            dots = "●●●" if ev["impact"] == "High" else "●●"
            dcol = AMBER if ev["impact"] == "High" else "#9aa4b2"
            day = "" if ev["dt"].date() == today else f"{ev['dt']:%a} "
            rows.append(
                f'<div class="tt-row"><span class="tt-mono tt-muted">{day}{ev["dt"]:%H:%M}</span>'
                f'<span><b style="font-weight:600">{e(ev["title"])}</b>'
                f'<span class="tt-imp" style="color:{dcol}">{dots}</span></span>'
                f'<span class="tt-mono tt-vals">{e(ev["forecast"])} / <b>{e(ev["actual"])}</b> / '
                f'<span class="tt-muted">{e(ev["previous"])}</span></span>'
                f'<span style="color:{c};font-weight:700">{a}</span></div>'
            )
        st.markdown(f'<div class="tt-cal">{"".join(rows)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="tt-note" style="margin-top:4px">●●● hohe Relevanz · ▲ gut für NQ · '
                    '▼ schlecht für NQ</div>', unsafe_allow_html=True)

with col_news:
    st.markdown('<div class="tt-h2">News <span>auf Deutsch · Einschätzung für NQ</span></div>',
                unsafe_allow_html=True)
    if not news:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">News gerade nicht erreichbar.</div>',
                    unsafe_allow_html=True)
    else:
        def has_kw(n):
            text = (n["title"] + " " + n.get("title_de", "")).lower()
            return any(k in text for k in keywords)

        def t(n):
            return f"{n['dt']:%H:%M}" if n["dt"] else "--:--"

        # Top-Meldung: neueste mit Stichwort, sonst die neueste überhaupt
        top = next((n for n in news if has_kw(n)), news[0])
        rest = [n for n in news if n is not top]
        gallery = rest[2:]
        idx = st.session_state.get("gal_idx", 0) % len(gallery) if gallery else 0

        # Kopfzeilen der großen Karten (per CSS über dem Titel eingeblendet)
        card_css = f'div.st-key-news_top button::before {{ content:"TOP-MELDUNG · {css_text(t(top))}"; }}'
        if gallery:
            g = gallery[idx]
            dots = "●" * abs(g["score"]) + "○" * (2 - abs(g["score"]))
            card_css += (f' div.st-key-gal_card button::before {{ content:"CNBC · {css_text(t(g))} · Stärke {dots}"; }}')
            if has_kw(g):
                card_css += f" div.st-key-gal_card button {{ border-color:{AMBER}; }}"
        st.markdown(f"<style>{card_css}</style>", unsafe_allow_html=True)

        # Antippen der Karte öffnet direkt den Artikel – Pfeil immer vorne
        if st.button(f"{md_arrow(top['score'])}  {md_safe(top['title_de'])}", key="news_top"):
            show_article(top)

        # Zwei weitere Meldungen als kompakte Zeilen
        for i, n in enumerate(rest[:2]):
            key = f"nline_kw_{i}" if has_kw(n) else f"nline_{i}"
            if st.button(f"{md_arrow(n['score'])}  {md_safe(n['title_de'])}  ·  {t(n)}", key=key):
                show_article(n)

        # Galerie: eine Karte, mit ‹ und › weiterblättern
        if gallery:
            st.markdown(
                f'<div class="tt-h2" style="margin-top:10px">Weitere Meldungen '
                f'<span>{idx + 1} / {len(gallery)}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"{md_arrow(g['score'])}  {md_safe(g['title_de'])}", key="gal_card"):
                show_article(g)
            with st.container(key="galnav"):
                prev_col, next_col = st.columns(2)
                with prev_col:
                    if st.button("‹ Zurück", key="gal_prev"):
                        st.session_state["gal_idx"] = (idx - 1) % len(gallery)
                        st.rerun()
                with next_col:
                    if st.button("Weiter ›", key="gal_next"):
                        st.session_state["gal_idx"] = (idx + 1) % len(gallery)
                        st.rerun()
