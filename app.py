import csv
import html
import re
import time
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
    from deep_translator import DeeplTranslator, GoogleTranslator, MyMemoryTranslator
except Exception:  # Paket fehlt -> App läuft ohne Übersetzung weiter
    DeeplTranslator = GoogleTranslator = MyMemoryTranslator = None

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
.tt-row {{ display:grid; grid-template-columns:14px 44px minmax(0,1fr) 104px; gap:7px; padding:7px 10px; font-size:12px; align-items:center; border-bottom:1px solid #1c2230; color:#e6e9ef; }}
.tt-row:last-child {{ border-bottom:none; }}
.tt-scn-card {{ margin-bottom:6px; }}
.tt-scn {{ display:flex; justify-content:space-between; gap:8px; font-size:12px; padding:5px 8px;
  background:#0f131b; border-radius:8px; margin-top:4px; color:#c3c9d3; }}
.tt-result {{ margin-top:8px; padding:8px 10px; border:1px solid; border-radius:8px; font-size:14px; font-weight:700; }}
.tt-ist {{ display:inline-block; padding:0 4px; border:1px solid; border-radius:4px; font-weight:700; }}
.tt-res-vals {{ display:block; font-size:11px; font-weight:400; color:#c3c9d3; margin-top:3px; }}
.tt-row.tt-hd {{ font-size:9px; color:#8a94a3; padding:6px 10px; }}
.tt-mono {{ font-family:'JetBrains Mono', ui-monospace, monospace; }}
.tt-muted {{ color:#9aa4b2; }}
.tt-imp {{ font-size:9px; display:block; }}
.tt-vals {{ font-size:10px; line-height:1.3; }}
.tt-note {{ font-size:10px; color:#8a94a3; }}

/* Analyse-Zeitraum und Chart-Zeitrahmen als kleine Schalter */
div[data-testid="stRadio"] label p {{ font-size:12px; }}
div[data-testid="stRadio"] > div {{ gap:4px; }}

/* News-Karten: alle exakt gleich breit (volle Spaltenbreite) */
div[class*="st-key-nline_"], div.st-key-news_top, div.st-key-gal_card,
div[class*="st-key-nline_"] .stButton, div.st-key-news_top .stButton, div.st-key-gal_card .stButton {{
  width:100% !important; max-width:100% !important; }}
div[class*="st-key-nline_"] button div, div.st-key-news_top button div, div.st-key-gal_card button div {{
  width:100%; justify-content:flex-start; text-align:left; }}
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


def de_day(dt) -> str:
    """Deutscher Wochentag, kurz."""
    return ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][dt.weekday()]


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


def card_button(label: str, key: str) -> bool:
    """Button über die volle Breite (neue und ältere Streamlit-Versionen)."""
    try:
        return st.button(label, key=key, width="stretch")
    except TypeError:
        return st.button(label, key=key, use_container_width=True)


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
def _secret(name: str):
    """Optionaler Schlüssel aus den Streamlit-Secrets (fehlt er, wird er übersprungen)."""
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def translators() -> list:
    """Übersetzer in der Reihenfolge, in der sie probiert werden: (Name, Erzeuger, max. Zeichen)."""
    if GoogleTranslator is None:
        return []
    chain = []
    deepl_key = _secret("DEEPL_API_KEY")
    if deepl_key:
        chain.append(("DeepL", lambda: DeeplTranslator(api_key=deepl_key, source="en", target="de",
                                                       use_free_api=True), 4500))
    chain.append(("Google", lambda: GoogleTranslator(source="en", target="de"), 4500))
    email = _secret("MYMEMORY_EMAIL")  # optional: erhöht das kostenlose Tageslimit von MyMemory
    chain.append(("MyMemory", lambda: MyMemoryTranslator(source="en-GB", target="de-DE",
                                                         **({"email": email} if email else {})), 480))
    return chain


def split_text(text: str, max_len: int) -> list:
    """Langen Text an Absätzen, Sätzen und notfalls Wörtern in Stücke teilen – ohne etwas abzuschneiden."""
    if len(text) <= max_len:
        return [text]
    pieces = []
    for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
        while len(sent) > max_len:  # sehr langer Satz: an einem Leerzeichen trennen
            cut = sent.rfind(" ", 0, max_len)
            cut = cut if cut > 0 else max_len
            pieces.append(sent[:cut])
            sent = sent[cut:].strip()
        if sent:
            pieces.append(sent)
    parts, cur = [], ""
    for piece in pieces:
        if cur and len(cur) + len(piece) + 1 > max_len:
            parts.append(cur)
            cur = piece
        else:
            cur = f"{cur} {piece}".strip()
    if cur:
        parts.append(cur)
    return parts


def _set_status(text: str):
    try:
        st.session_state["tr_status"] = text
    except Exception:
        pass


@st.cache_data(ttl=86400, show_spinner=False)
def _translate_cached(text: str) -> str:
    """Probiert alle Übersetzer nacheinander. Nur Erfolge werden 24 Std. gespeichert."""
    errors = []
    for name, make, max_len in translators():
        try:
            tr = make()
            out = " ".join((tr.translate(chunk) or "") for chunk in split_text(text, max_len)).strip()
            if not out:
                raise ValueError("leere Antwort")
            if len(text) > 25 and out.strip().lower() == text.strip().lower():
                raise ValueError("unverändert zurückgegeben")
            _set_status(f"✓ {name}")
            return out
        except Exception as ex:
            errors.append(f"{name}: {type(ex).__name__} {str(ex)[:80]}")
    _set_status("✗ " + " | ".join(errors) if errors else "✗ kein Übersetzer verfügbar")
    raise RuntimeError("keine Übersetzung möglich")


def translate_text(text: str) -> str:
    if not text or GoogleTranslator is None:
        return text
    try:
        return _translate_cached(text)
    except Exception:
        return text  # Rückfall: Original, beim nächsten Laden neuer Versuch


def translate_many(texts: tuple) -> list:
    """Schlagzeilen einzeln übersetzen (jede wird 24 Std. gespeichert)."""
    return [translate_text(t) for t in texts]


def translate_paragraphs(paragraphs: list) -> list:
    """Artikeltext übersetzen: erst gesammelt, wenn die Absätze dabei verloren gehen, einzeln."""
    joined = "\n\n".join(paragraphs)
    if len(joined) <= 4500:
        out = translate_text(joined)
        parts = [x.strip() for x in out.split("\n\n") if x.strip()]
        if out != joined and len(parts) == len(paragraphs):
            return parts
    return [translate_text(p) for p in paragraphs]


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
    return items[:25]


def add_translations(items: list) -> list:
    """Schlagzeilen ins Deutsche übersetzen (erfolgreiche Übersetzungen werden 24 Std. gespeichert)."""
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
# 6. DATEN: WIRTSCHAFTSKALENDER (live mit Ist-Werten)
# ==============================================================================
# Eigene Bewertung aus Sicht des NQ-Future-Traders – NICHT die Dollar-Farben der Quelle.
# Jede Regel sagt: Kommt der Wert HÖHER als die Prognose, ist das für den NQ ...
#   -1 = bärisch (z. B. höhere Inflation -> höhere Zinsen -> Tech fällt)
#   +1 = bullisch (z. B. stärkere Konjunktur -> mehr Gewinne)
# Drittes Feld True = doppeldeutig ("gute Nachricht kann schlecht für den Markt sein") -> ⇅
# Reihenfolge zählt: die erste passende Regel gewinnt.
NQ_RULES = [
    (["rate decision", "funds rate", "refinancing rate", "deposit facility", "interest rate"], -1, False),
    (["bond auction", "note auction", "bill auction"], -1, False),
    (["cpi", "ppi", "pce", "inflation", "price index", "average hourly earnings",
      "employment cost", "import prices", "wage"], -1, False),
    (["unemployment rate", "unemployment claims", "jobless claims", "continuing claims"], -1, True),
    (["non-farm", "nonfarm", "non farm", "payrolls", "adp", "jolts", "employment change"], 1, True),
    (["ism", "pmi", "retail sales", "gdp", "consumer confidence", "consumer sentiment",
      "durable goods", "industrial production", "factory orders", "housing starts",
      "building permits", "home sales", "productivity", "business confidence", "zew", "ifo",
      "empire state", "philly fed", "philadelphia fed", "manufacturing index", "economic optimism",
      "personal spending"], 1, True),
]

# Live-Quelle: TradingView-Wirtschaftskalender (Vorher / Prognose / Ist, Ist-Wert direkt zur Veröffentlichung)
TV_CALENDAR_URL = "https://economic-calendar.tradingview.com/events"
TV_HEADERS = {**HEADERS, "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"}
TV_COUNTRIES = {"US": "USD", "EU": "EUR", "DE": "EUR"}
TV_IMPORTANCE = {1: "High", 0: "Medium"}  # -1 = niedrig, wird ausgeblendet


def calendar_direction(title: str):
    """Gibt (Richtung, doppeldeutig?) aus Sicht des NQ zurück."""
    t = title.lower()
    for keys, direction, ambiguous in NQ_RULES:
        if any(k in t for k in keys):
            return direction, ambiguous
    return 0, False


def direction_hint(direction: int) -> str:
    """Kurzer Hinweis, welches Ergebnis für den NQ gut wäre."""
    if direction < 0:
        return "unter Prognose = ▲"
    if direction > 0:
        return "über Prognose = ▲"
    return ""


def plain_number(value):
    """Zahl ohne Einheit ('0.3%' -> 0.3, '180K' -> 180, '1,234K' -> 1234)."""
    if value in (None, "", "–", "-"):
        return None
    s = str(value).strip().replace(" ", "")
    s = re.sub(r"[%KMBT]+$", "", s)
    if "," in s and "." in s and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "")
    if "," in s and "." not in s and not re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
        s = s.replace(",", ".")
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_value(val, scale: str = "", unit: str = "") -> str:
    """Zahl aus der Quelle lesbar machen, z. B. 0.3 + '%' -> '0.3%', 250 + 'K' -> '250K'."""
    if val is None:
        return "–"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "–"
    txt = f"{num:,.2f}".rstrip("0").rstrip(".") if abs(num) >= 1000 else f"{num:g}"
    return f"{txt}{scale or ''}{unit if unit == '%' else ''}"


def make_event(dt, country, title, impact, actual, forecast, previous) -> dict:
    """Ein Termin – mit eigener NQ-Bewertung, sobald der Ist-Wert da ist."""
    direction, ambiguous = calendar_direction(title)
    a, f = plain_number(actual), plain_number(forecast)
    sig = 0
    if a is not None and f is not None and a != f:
        sig = direction * (1 if a > f else -1)
    return {
        "dt": dt, "country": country, "title": f"{country} {title}", "impact": impact,
        "actual": actual or "–", "forecast": forecast or "–", "previous": previous or "–",
        "signal": sig, "direction": direction, "ambiguous": ambiguous,
    }


def load_calendar_tradingview() -> list:
    now_utc = datetime.now(ZoneInfo("UTC"))
    start = (now_utc - pd.Timedelta(days=2)).strftime("%Y-%m-%dT00:00:00.000Z")
    end = (now_utc + pd.Timedelta(days=8)).strftime("%Y-%m-%dT00:00:00.000Z")
    r = requests.get(TV_CALENDAR_URL, headers=TV_HEADERS, timeout=6,
                     params={"from": start, "to": end, "countries": ",".join(TV_COUNTRIES)})
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        raise ValueError(data.get("errmsg") or "Kalender-Fehler")
    events = []
    for ev in data.get("result", []):
        impact = TV_IMPORTANCE.get(ev.get("importance"))
        country = TV_COUNTRIES.get(ev.get("country"))
        if not impact or not country:
            continue
        try:
            dt = datetime.fromisoformat(str(ev["date"]).replace("Z", "+00:00")).astimezone(BERLIN)
        except Exception:
            continue
        scale, unit = ev.get("scale") or "", ev.get("unit") or ""
        events.append(make_event(
            dt, country, ev.get("title", ""), impact,
            fmt_value(ev.get("actual"), scale, unit) if ev.get("actual") is not None else "",
            fmt_value(ev.get("forecast"), scale, unit) if ev.get("forecast") is not None else "",
            fmt_value(ev.get("previous"), scale, unit) if ev.get("previous") is not None else "",
        ))
    return events


def load_calendar_forexfactory() -> list:
    """Rückfall-Quelle (ohne Ist-Werte)."""
    r = requests.get(CALENDAR_URL, headers=HEADERS, timeout=5)
    events = []
    for ev in r.json():
        if ev.get("country") not in ("USD", "EUR") or ev.get("impact") not in ("High", "Medium"):
            continue
        try:
            dt = datetime.fromisoformat(ev["date"]).astimezone(BERLIN)
        except Exception:
            continue
        events.append(make_event(dt, ev["country"], ev.get("title", ""), ev.get("impact"),
                                 ev.get("actual", ""), ev.get("forecast", ""), ev.get("previous", "")))
    return events


@st.cache_data(ttl=30, show_spinner=False)
def load_calendar():
    """Gibt (Termine, Quelle) zurück. Alle 30 Sekunden frisch."""
    for name, loader in (("TradingView · live", load_calendar_tradingview),
                         ("ForexFactory · ohne Ist-Werte", load_calendar_forexfactory)):
        try:
            events = loader()
            if events:
                events.sort(key=lambda x: x["dt"])
                return events, name
        except Exception:
            continue
    return [], ""


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
    # US-Daten zählen voll, Euro-Daten nur halb (geringerer Einfluss auf den Nasdaq),
    # wichtige Termine (●●●) doppelt so stark wie mittlere (●●)
    raw = sum(ev["signal"] * (1 if ev["country"] == "USD" else 0.5) * (1 if ev["impact"] == "High" else 0.5)
              for ev in released)
    score = clamp(int(raw + (0.5 if raw > 0 else -0.5)), -2, 2)  # ab ±0,5 zählt es
    if released:
        reasons = []
        for ev in released[-4:]:
            verdict = "▲ bullisch" if ev["signal"] > 0 else "▼ bärisch"
            warn = " ⇅ Achtung, Markt kann es anders sehen." if ev["ambiguous"] else ""
            reasons.append(f"{ev['title']}: {ev['actual']} (Prognose {ev['forecast']}) – {verdict}.{warn}")
    else:
        upcoming = [ev for ev in pool if ev["dt"] >= now_ and ev["impact"] == "High"]
        reasons = ([f"Noch keine Ergebnisse {span}. Wichtig: " + ", ".join(
            f"{de_day(ev['dt'])} {ev['dt']:%H:%M} {ev['title']}" for ev in upcoming[:3]) + "."]
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
    st.session_state["_article_opened"] = time.time()  # Auto-Aktualisierung pausieren, solange du liest
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
tr_status_slot = st.sidebar.empty()  # wird am Ende mit dem Übersetzungs-Status befüllt
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
for _n in news:
    _n.setdefault("title_de", _n["title"])
calendar, calendar_source = load_calendar()

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
# 13b. SZENARIO-KARTE: NÄCHSTER WICHTIGER TERMIN (Countdown, Szenarien, Live-Ergebnis)
# ==============================================================================
def countdown(dt: datetime) -> str:
    minutes = int((dt - datetime.now(BERLIN)).total_seconds() // 60)
    if -1 <= minutes <= 0:
        return "JETZT"
    if minutes < 0:
        return f"vor {-minutes} Min"
    if minutes < 60:
        return f"in {minutes} Min"
    if minutes < 24 * 60:
        return f"in {minutes // 60} Std {minutes % 60} Min"
    return f"{de_day(dt)} {dt:%d.%m. %H:%M}"


def scenario_slot(events: list) -> list:
    """Alle Termine zum nächsten ●●●-Zeitpunkt – bleibt nach der Veröffentlichung 60 Min stehen."""
    now_ = datetime.now(BERLIN)
    window = [ev for ev in events if ev["impact"] == "High" and ev["dt"] >= now_ - pd.Timedelta(minutes=60)]
    if not window:
        return []
    first = min(ev["dt"] for ev in window)
    return [ev for ev in events if ev["dt"] == first][:4]


WARN = f'<span style="color:{AMBER};font-weight:700" title="Doppeldeutig">⇅</span>'

slot = scenario_slot(calendar)
if slot:
    when = slot[0]["dt"]
    is_due = when <= datetime.now(BERLIN)
    head_col = AMBER if is_due or (when - datetime.now(BERLIN)).total_seconds() < 3600 else "#9aa4b2"
    st.markdown(
        f'<div class="tt-h2" style="margin-top:12px">Nächster wichtiger Termin '
        f'<span style="color:{head_col};font-weight:700">{countdown(when)} · {when:%H:%M} Uhr</span></div>',
        unsafe_allow_html=True,
    )
    cards = []
    for ev in slot:
        fc, released = ev["forecast"], ev["actual"] not in ("–", "")
        dots = "●●●" if ev["impact"] == "High" else "●●"
        warn = f" {WARN}" if ev["ambiguous"] else ""
        if released:
            # Ergebnis ist da: sofortige Bewertung
            ra, rl, rc = bias_style(ev["signal"])
            body = (f'<div class="tt-result" style="border-color:{rc};color:{rc}">{ra} {rl.upper()}{warn}'
                    f'<span class="tt-res-vals">Vorher {e(ev["previous"])} · Prognose {e(fc)} · '
                    f'<b>Ist {e(ev["actual"])}</b></span></div>')
        elif ev["direction"] != 0 and plain_number(fc) is not None:
            up_a, up_l, up_c = bias_style(ev["direction"])
            dn_a, dn_l, dn_c = bias_style(-ev["direction"])
            body = (f'<div class="tt-scn"><span>Über {e(fc)}</span><b style="color:{up_c}">{up_a} {up_l}</b></div>'
                    f'<div class="tt-scn"><span>Unter {e(fc)}</span><b style="color:{dn_c}">{dn_a} {dn_l}</b></div>')
        else:
            body = '<div class="tt-note">Keine klare Richtung für den NQ.</div>'
        if ev["ambiguous"]:
            body += (f'<div class="tt-note" style="margin-top:5px">{WARN} Achtung: Gute Nachricht kann schlecht '
                     'für den Markt sein (Zinsen) – Reaktion beobachten.</div>')
        cards.append(
            f'<div class="tt-card tt-scn-card"><div style="display:flex;justify-content:space-between;'
            f'font-size:13px;font-weight:700"><span>{e(ev["title"])}</span>'
            f'<span style="color:{AMBER if ev["impact"] == "High" else "#9aa4b2"};font-size:10px">{dots}</span></div>'
            + ("" if released else
               f'<div class="tt-note" style="margin:2px 0 4px">Vorher {e(ev["previous"])} · Prognose {e(fc)}</div>')
            + f"{body}</div>"
        )
    st.markdown("".join(cards), unsafe_allow_html=True)

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
        shown = [ev for ev in calendar if ev["dt"] >= now][:8]
        sub = "Heute nichts · nächste Termine"
    st.markdown(f'<div class="tt-h2">Wirtschaftskalender <span>{sub}</span></div>', unsafe_allow_html=True)

    if not calendar:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">Kalender gerade nicht erreichbar.</div>',
                    unsafe_allow_html=True)
    elif not shown:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">Keine weiteren Termine diese Woche.</div>',
                    unsafe_allow_html=True)
    else:
        rows = ['<div class="tt-row tt-hd"><span></span><span>ZEIT</span><span>EREIGNIS</span>'
                '<span>VORH / PROG / IST</span></div>']
        for ev in shown:
            a, _, c = bias_style(ev["signal"])  # eigene NQ-Bewertung, sobald der Ist-Wert da ist
            dots = "●●●" if ev["impact"] == "High" else "●●"
            dcol = AMBER if ev["impact"] == "High" else "#9aa4b2"
            day = "" if ev["dt"].date() == today else f"{de_day(ev['dt'])} "
            released = ev["actual"] not in ("–", "")
            hint = direction_hint(ev["direction"]) if not released else ""
            # Eine Farbe für alles: Pfeil, Terminname und Ist-Wert (grün = bullisch, rot = bärisch für den NQ)
            title_col = c if released and ev["signal"] != 0 else "#e6e9ef"
            if released and ev["signal"] != 0:
                actual_html = (f'<b class="tt-ist" style="color:{c};border-color:{c};'
                               f'background:{"rgba(52,211,153,0.14)" if ev["signal"] > 0 else "rgba(248,113,113,0.14)"}">'
                               f'{e(ev["actual"])}</b>')
            elif released:
                actual_html = f'<b class="tt-ist" style="color:{NEUTRAL};border-color:#3a4456">{e(ev["actual"])}</b>'
            else:
                actual_html = '<b class="tt-muted">–</b>'
            rows.append(
                f'<div class="tt-row"><span style="color:{c};font-weight:700;font-size:13px">{a}</span>'
                f'<span class="tt-mono tt-muted">{day}{ev["dt"]:%H:%M}</span>'
                f'<span><b style="font-weight:600;color:{title_col}">{e(ev["title"])}</b>'
                f'{" " + WARN if ev["ambiguous"] else ""}'
                f'<span class="tt-imp"><span style="color:{dcol}">{dots}</span>'
                + (f' <span class="tt-muted">· {hint}</span>' if hint else "")
                + '</span></span>'
                f'<span class="tt-mono tt-vals"><span class="tt-muted">{e(ev["previous"])}</span> / '
                f'{e(ev["forecast"])} / {actual_html}</span></div>'
            )
        st.markdown(f'<div class="tt-cal">{"".join(rows)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="tt-note" style="margin-top:4px">▲ bullisch / ▼ bärisch für den NQ · '
                    f'{WARN} Achtung, Markt kann es anders sehen · Quelle: {e(calendar_source)}</div>',
                    unsafe_allow_html=True)

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

        # Nur die sichtbaren Meldungen übersetzen (schneller, schont das Übersetzungs-Kontingent)
        add_translations([top] + rest[:2] + ([gallery[idx]] if gallery else []))

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
        if card_button(f"{md_arrow(top['score'])}  {md_safe(top['title_de'])}", key="news_top"):
            show_article(top)

        # Zwei weitere Meldungen als kompakte Zeilen
        for i, n in enumerate(rest[:2]):
            key = f"nline_kw_{i}" if has_kw(n) else f"nline_{i}"
            if card_button(f"{md_arrow(n['score'])}  {md_safe(n['title_de'])}  ·  {t(n)}", key=key):
                show_article(n)

        # Galerie: eine Karte, mit ‹ und › weiterblättern
        if gallery:
            st.markdown(
                f'<div class="tt-h2" style="margin-top:10px">Weitere Meldungen '
                f'<span>{idx + 1} / {len(gallery)}</span></div>',
                unsafe_allow_html=True,
            )
            if card_button(f"{md_arrow(g['score'])}  {md_safe(g['title_de'])}", key="gal_card"):
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

# Übersetzungs-Status in der Sidebar (zeigt, welcher Übersetzer arbeitet oder warum es scheitert)
if GoogleTranslator is None:
    tr_status_slot.caption("Übersetzung: ✗ Paket fehlt – requirements.txt prüfen")
else:
    tr_status_slot.caption("Übersetzung: " + st.session_state.get("tr_status", "✓ aus Zwischenspeicher"))

# ==============================================================================
# 15. AUTOMATISCHE AKTUALISIERUNG
# ==============================================================================
# Kurz vor und nach einem wichtigen Termin alle 30 Sekunden, sonst jede Minute.
# Pausiert, solange du einen Artikel liest (3 Min).
REFRESH_SECONDS = 60
if slot and abs((slot[0]["dt"] - datetime.now(BERLIN)).total_seconds()) < 15 * 60:
    REFRESH_SECONDS = 30
st.session_state["_last_full_run"] = time.time()

if hasattr(st, "fragment"):
    @st.fragment(run_every=REFRESH_SECONDS)
    def _auto_refresh():
        now_ts = time.time()
        reading = now_ts - st.session_state.get("_article_opened", 0) < 180
        if reading:
            return
        if now_ts - st.session_state.get("_last_full_run", now_ts) >= REFRESH_SECONDS - 2:
            st.rerun()

    _auto_refresh()
