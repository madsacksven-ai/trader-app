import html
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

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
.tt-pills {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:6px; margin:8px 0; }}
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
.tt-top {{ display:block; text-decoration:none !important; background:#1a1f12; border:1px solid {AMBER}; border-radius:12px; padding:10px 12px; color:#e6e9ef !important; margin-bottom:6px; }}
.tt-top .tt-meta {{ display:flex; justify-content:space-between; font-size:10px; font-weight:700; }}
.tt-top .tt-hl {{ font-size:14px; font-weight:600; line-height:1.35; margin-top:4px; display:block; }}
.tt-line {{ display:flex; gap:8px; align-items:flex-start; text-decoration:none !important; background:#131822; border:1px solid #232a36; border-radius:10px; padding:7px 10px; color:#e6e9ef !important; margin-bottom:6px; font-size:12px; }}
.tt-line .tt-hl {{ font-weight:600; flex:1; line-height:1.35; }}
.tt-kw {{ border-color:{AMBER} !important; }}
.tt-gal-hint {{ font-size:11px; color:#9aa4b2; margin:6px 0 4px; display:flex; justify-content:space-between; }}
.tt-gal {{ display:flex; gap:10px; overflow-x:auto; scroll-snap-type:x mandatory; -webkit-overflow-scrolling:touch; padding-bottom:6px; }}
.tt-gcard {{ flex:0 0 260px; scroll-snap-align:start; background:#131822; border:1px solid #232a36; border-radius:12px; padding:10px 11px; display:flex; flex-direction:column; gap:7px; color:#e6e9ef; }}
.tt-gcard .tt-meta {{ display:flex; justify-content:space-between; font-size:10px; }}
.tt-gcard .tt-hl {{ font-size:13px; font-weight:600; line-height:1.35; }}
.tt-gcard a {{ font-size:11px; font-weight:600; color:#7cc4ff !important; }}
.tt-note {{ font-size:10px; color:#8a94a3; }}
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


# ==============================================================================
# 3. DATEN: KURSE
# ==============================================================================
TIMEFRAMES = {"5m": ("5m", "2d"), "15m": ("15m", "5d"), "1h": ("1h", "1mo")}


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


@st.cache_data(ttl=300, show_spinner=False)
def load_prev_close():
    try:
        d = yf.download(SYMBOL, interval="1d", period="10d", progress=False, auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.dropna(subset=["Close"])
        if len(d) >= 2:
            return float(d["Close"].iloc[-2]), float(d["Close"].iloc[-1])
    except Exception:
        pass
    return None, None


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP der aktuellen Handelssitzung (Start 18:00 New Yorker Zeit)."""
    if df.empty or "Volume" not in df:
        return pd.Series(dtype=float)
    ny = df.index.tz_convert(NEW_YORK)
    # Sitzung beginnt um 18:00 ET -> alles ab 18:00 zählt zum Folgetag
    session = (ny + pd.Timedelta(hours=6)).date
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].fillna(0)
    grp = pd.Series(session, index=df.index)
    pv = (typical * vol).groupby(grp).cumsum()
    vv = vol.groupby(grp).cumsum().replace(0, pd.NA)
    return (pv / vv).astype(float)


# ==============================================================================
# 4. DATEN: NEWS
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
                "desc": (it.findtext("description") or "").strip(),
                "dt": dt,
                "score": news_score(title),
            })
    items.sort(key=lambda x: x["dt"] or datetime.min.replace(tzinfo=BERLIN), reverse=True)
    return items[:25]


# ==============================================================================
# 5. DATEN: WIRTSCHAFTSKALENDER
# ==============================================================================
# Steigt dieser Wert stärker als erwartet: gut (+1) oder schlecht (-1) für den NQ?
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
# 6. ANALYSE: TAGES-BIAS
# ==============================================================================
def technical_analysis(df: pd.DataFrame, vwap: pd.Series, prev_close):
    reasons, score = [], 0
    if df.empty:
        return 0, ["Keine Kursdaten verfügbar."]
    last = float(df["Close"].iloc[-1])
    if len(vwap.dropna()):
        v = float(vwap.dropna().iloc[-1])
        if last > v:
            score += 1
            reasons.append(f"Kurs liegt über dem VWAP ({v:,.0f}).")
        else:
            score -= 1
            reasons.append(f"Kurs liegt unter dem VWAP ({v:,.0f}).")
    if len(df) >= 50:
        ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
        if ema20 > ema50:
            score += 1
            reasons.append("Kurzfristiger Trend aufwärts (EMA 20 über EMA 50).")
        else:
            score -= 1
            reasons.append("Kurzfristiger Trend abwärts (EMA 20 unter EMA 50).")
    if prev_close:
        if last > prev_close:
            score += 1
            reasons.append(f"Über dem Vortagesschluss ({prev_close:,.0f}).")
        else:
            score -= 1
            reasons.append(f"Unter dem Vortagesschluss ({prev_close:,.0f}).")
    return score, reasons


def calendar_analysis(events: list):
    today = datetime.now(BERLIN).date()
    released = [ev for ev in events if ev["dt"].date() == today and ev["signal"] != 0]
    score = sum(ev["signal"] for ev in released)
    if released:
        reasons = [f"{ev['title']}: {ev['actual']} (Prognose {ev['forecast']}) "
                   f"{'▲ gut' if ev['signal'] > 0 else '▼ schlecht'} für NQ." for ev in released]
    else:
        upcoming = [ev for ev in events if ev["dt"].date() == today and ev["impact"] == "High"]
        reasons = (["Noch keine Ergebnisse. Wichtig heute: " + ", ".join(
            f"{ev['dt']:%H:%M} {ev['title']}" for ev in upcoming[:3]) + "."]
            if upcoming else ["Heute keine wichtigen Termine mit Ergebnis."])
    return max(-2, min(2, score)), reasons


def news_analysis(news: list):
    recent = news[:12]
    score = sum(n["score"] for n in recent)
    bull = sum(1 for n in recent if n["score"] > 0)
    bear = sum(1 for n in recent if n["score"] < 0)
    reasons = [f"Letzte {len(recent)} Meldungen: {bull} positiv, {bear} negativ."] if recent \
        else ["Keine News verfügbar."]
    return (1 if score >= 2 else -1 if score <= -2 else 0), reasons


# ==============================================================================
# 7. SIDEBAR
# ==============================================================================
st.sidebar.header("⚙️ Einstellungen")
keywords_input = st.sidebar.text_input(
    "Eilmeldungs-Filter (Komma-getrennt)", "Fed, Inflation, Zinsen, rate, war, tariff, Nasdaq"
)
keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
if st.sidebar.button("🔄 Alles aktualisieren"):
    st.cache_data.clear()
st.sidebar.caption("Kursdaten: Yahoo Finance (verzögert) · News: CNBC · Kalender: ForexFactory")

# ==============================================================================
# 8. KOPFZEILE
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
# 9. OBEN: CHART + TAGES-BIAS
# ==============================================================================
tf = st.radio("Zeitrahmen", list(TIMEFRAMES), horizontal=True, label_visibility="collapsed")
interval, period = TIMEFRAMES[tf]

prices = load_prices(interval, period)
intraday = load_prices("5m", "2d")  # Analyse immer auf 5-Minuten-Basis
prev_close, _ = load_prev_close()
vwap_intraday = session_vwap(intraday)
news = load_news()
calendar = load_calendar()

t_score, t_reasons = technical_analysis(intraday, vwap_intraday, prev_close)
c_score, c_reasons = calendar_analysis(calendar)
n_score, n_reasons = news_analysis(news)
total = t_score + c_score + n_score
bias_val = 1 if total >= 2 else -1 if total <= -2 else 0
arrow, label, color = bias_style(bias_val)
strength = 1 if abs(total) <= 2 else 2 if abs(total) <= 4 else 3
strength_txt = {1: "schwach", 2: "mittel", 3: "stark"}[strength]

col_chart, col_analysis = st.columns([2.2, 1], gap="small")

with col_chart:
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
        show_vwap = session_vwap(prices).reindex(show.index)
        x = show.index.tz_convert(BERLIN)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=x, open=show["Open"], high=show["High"], low=show["Low"], close=show["Close"],
            increasing_line_color=BULL, decreasing_line_color=BEAR,
            increasing_fillcolor=BULL, decreasing_fillcolor=BEAR, name="NQ",
        ))
        if tf != "1h":
            fig.add_trace(go.Scatter(x=x, y=show_vwap, mode="lines", name="VWAP",
                                     line=dict(color=AMBER, width=1.3, dash="dot")))
        if prev_close:
            fig.add_hline(y=prev_close, line=dict(color="#5b6578", width=1, dash="dash"),
                          annotation_text="Vortagesschluss", annotation_font_size=10,
                          annotation_font_color="#9aa4b2", annotation_position="bottom right")
        fig.add_annotation(
            xref="paper", yref="paper", x=0.01, y=0.98, xanchor="left", yanchor="top",
            text=f"<span style='font-size:10px'>TAGES-BIAS</span><br><b>{arrow} {label}</b>",
            showarrow=False, align="left", font=dict(color=color, size=15),
            bgcolor="rgba(15,19,27,0.9)", bordercolor=color, borderwidth=1, borderpad=6,
        )
        fig.update_layout(
            height=330, margin=dict(l=0, r=0, t=4, b=0), showlegend=False,
            paper_bgcolor="#0f131b", plot_bgcolor="#0f131b",
            font=dict(color="#9aa4b2", size=10), xaxis_rangeslider_visible=False,
            xaxis=dict(gridcolor="#1c2230", rangebreaks=[dict(bounds=["sat", "mon"])]),
            yaxis=dict(gridcolor="#1c2230", side="right"),
            dragmode=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col_analysis:
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
  <div class="tt-h2" style="margin-top:0">Tagesanalyse <span>{now:%H:%M} Uhr</span></div>
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
# 10. UNTEN: KALENDER LINKS, NEWS RECHTS
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
    st.markdown('<div class="tt-h2">News <span>mit Einschätzung für NQ</span></div>', unsafe_allow_html=True)
    if not news:
        st.markdown('<div class="tt-card tt-muted" style="font-size:12px">News gerade nicht erreichbar.</div>',
                    unsafe_allow_html=True)
    else:
        def has_kw(n):
            return any(k in n["title"].lower() for k in keywords)

        # Top-Meldung: neueste mit Stichwort, sonst die neueste überhaupt
        top = next((n for n in news if has_kw(n)), news[0])
        rest = [n for n in news if n is not top]

        def tag(s, upper=False):
            a, l, c = bias_style(s)
            return f'<span style="color:{c};font-weight:700">{a} {l.upper() if upper else l}</span>'

        def t(n):
            return f"{n['dt']:%H:%M}" if n["dt"] else "--:--"

        desc = e(top["desc"][:160]) if top["desc"] else ""
        st.markdown(
            f'<a class="tt-top" href="{e(top["link"])}" target="_blank">'
            f'<span class="tt-meta"><span style="color:{AMBER}">TOP-MELDUNG · {t(top)}</span>{tag(top["score"], True)}</span>'
            f'<span class="tt-hl">{e(top["title"])}</span>'
            + (f'<span style="font-size:11px;color:#c3c9d3">{desc}</span>' if desc else "")
            + "</a>",
            unsafe_allow_html=True,
        )

        lines = []
        for n in rest[:2]:
            a, _, c = bias_style(n["score"])
            kw = " tt-kw" if has_kw(n) else ""
            lines.append(
                f'<a class="tt-line{kw}" href="{e(n["link"])}" target="_blank">'
                f'<span style="color:{c};font-weight:700;width:14px">{a}</span>'
                f'<span class="tt-hl">{e(n["title"])}</span>'
                f'<span class="tt-muted" style="font-size:10px">{t(n)}</span></a>'
            )
        st.markdown("".join(lines), unsafe_allow_html=True)

        gallery = rest[2:]
        if gallery:
            cards = []
            for n in gallery:
                strength_dots = "●" * abs(n["score"]) + "○" * (2 - abs(n["score"]))
                border = f' style="border-color:{AMBER}"' if has_kw(n) else ""
                cards.append(
                    f'<div class="tt-gcard"{border}>'
                    f'<span class="tt-meta"><span class="tt-muted">CNBC · {t(n)}</span>{tag(n["score"], True)}</span>'
                    f'<span class="tt-hl">{e(n["title"])}</span>'
                    f'<span style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span class="tt-muted" style="font-size:10px">Stärke {strength_dots}</span>'
                    f'<a href="{e(n["link"])}" target="_blank">Artikel lesen ›</a></span></div>'
                )
            st.markdown(
                f'<div class="tt-gal-hint"><span>Weitere Meldungen</span><span>← wischen → · {len(gallery)}</span></div>'
                f'<div class="tt-gal">{"".join(cards)}</div>',
                unsafe_allow_html=True,
            )
