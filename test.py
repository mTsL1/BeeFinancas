# Bee Finanças — Streamlit App (v23.0 FULL | BeeTV refined + hidden refresh)
# -----------------------------------------------------------------------------
# ✅ Cripto Movers: Binance (24h) — SEM API
# ✅ B3 Movers: TradingView Scanner — SEM API
# ✅ Bee TV: YouTube Search — precisa YOUTUBE_API_KEY
# ✅ Bee TV: 6 vídeos, sem shorts, prioriza favoritos, tenta likes >= 20k
# ✅ pt-BR numbers
# ✅ Links B3 -> Investidor10
# ✅ Aprenda restored
#
# requirements.txt:
# streamlit
# pandas
# yfinance
# plotly
# feedparser
# requests
# pillow
# deep-translator
# python-dateutil

import os
import math
import warnings
from datetime import datetime, timezone, timedelta

import streamlit as st
import pandas as pd
import feedparser
import requests
from PIL import Image

# -----------------------------------------------------------------------------
# TIMEZONE BR
# -----------------------------------------------------------------------------
try:
    from zoneinfo import ZoneInfo
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except Exception:
    TZ_BR = timezone(timedelta(hours=-3))

def now_br() -> datetime:
    return datetime.now(TZ_BR)

# -----------------------------------------------------------------------------
# FORMATAÇÃO pt-BR
# -----------------------------------------------------------------------------
def fmt_num_br(x, dec=0):
    try:
        x = float(x)
    except Exception:
        return "—"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_money_brl(x, dec=2):
    return f"R$ {fmt_num_br(x, dec)}"

def fmt_money_usd(x, dec=2):
    return f"US$ {fmt_num_br(x, dec)}"

def fmt_pct(x, dec=2, signed=True):
    try:
        x = float(x)
    except Exception:
        return "—"
    sign = "+" if (signed and x >= 0) else ""
    return f"{sign}{fmt_num_br(x, dec)}%"

# -----------------------------------------------------------------------------
# CONFIG & LOGO
# -----------------------------------------------------------------------------
def process_logo_transparency(image_path):
    if not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img
    except Exception:
        return None

warnings.filterwarnings("ignore")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")

logo_img = process_logo_transparency(LOGO_PATH)
page_icon = logo_img if logo_img else "🐝"

st.set_page_config(
    page_title="Bee Finanças",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# OPTIONAL IMPORTS
# -----------------------------------------------------------------------------
try:
    import yfinance as yf
except Exception:
    yf = None

try:
    import plotly.express as px
except Exception:
    px = None

try:
    from dateutil import parser as dtparser
except Exception:
    dtparser = None

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# =============================================================================
# CSS (Premium + alinhado)
# =============================================================================
st.markdown(
    """
<style>
.stApp{
  background:
    radial-gradient(circle at 15% 15%, rgba(255, 215, 0, 0.05), transparent 35%),
    radial-gradient(circle at 85% 85%, rgba(89, 0, 179, 0.10), transparent 35%),
    #0B0F14;
}
h1,h2,h3,h4{
  color:#FFD700!important; font-family:Inter,sans-serif;
  font-weight:900; letter-spacing:-0.03em;
}

/* --- SIDEBAR --- */
section[data-testid="stSidebar"]{ background:#090C10; border-right:1px solid rgba(255,255,255,0.05); }
section[data-testid="stSidebar"] img{ display:block; margin:0 auto 14px auto; object-fit:contain; max-width:100%; }

.menu-header{
  font-size:10px; text-transform:uppercase; color:#444; font-weight:900;
  letter-spacing:1px; margin-top:15px; margin-bottom:6px; padding-left:5px;
}

/* NAV BUTTONS */
div[data-testid="stVerticalBlock"]{ gap:0.3rem!important; }
div[data-testid="stSidebarUserContent"] .stButton{ margin-bottom:0px!important; }

.navbtn button{
  width:100%;
  background:linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)!important;
  color:#909090!important;
  border:1px solid rgba(255,255,255,0.05)!important;
  border-radius:12px!important;
  padding:0.6rem 1rem!important;
  margin:0!important;
  font-weight:900!important;
  font-size:14px!important;
  text-align:left!important;
  transition:all .2s;
  height:46px!important;
  display:flex!important;
  align-items:center!important;
}
.navbtn button:hover{
  background:linear-gradient(90deg, rgba(255,215,0,0.12) 0%, rgba(255,215,0,0.03) 100%)!important;
  color:#fff!important;
  border-left:3px solid #FFD700!important;
  transform:translateX(2px);
}

/* CARDS */
.bee-card{
  background:rgba(255,255,255,0.02);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:18px;
  padding:18px;
  backdrop-filter:blur(6px);
}
.card-title{
  color:#FFD700; font-weight:900; font-size:11px;
  text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;
}
.kpi{
  color:#fff; font-weight:950; font-size:28px; line-height:1.05;
  white-space:nowrap;
}
.sub{ color:#666; font-size:12px; }

/* HEADER PILL */
.header-pill{
  padding:7px 12px;
  border:1px solid rgba(255,255,255,0.07);
  border-radius:999px;
  background:rgba(255,255,255,0.02);
  color:#8a8a8a;
  font-size:12px;
  font-weight:850;
  display:inline-flex;
  align-items:center;
  gap:8px;
}

/* small icon refresh */
.iconbtn button{
  width:44px!important;
  height:36px!important;
  border-radius:12px!important;
  border:1px solid rgba(255,255,255,0.08)!important;
  background:rgba(255,255,255,0.02)!important;
  color:#ddd!important;
  font-weight:950!important;
}
.iconbtn button:hover{
  border-color:#FFD700!important;
  transform:translateY(-1px);
}

/* MARKET MONITOR */
.ticker-pill{
  background:rgba(255,255,255,0.03);
  border-radius:12px;
  padding:9px 10px;
  margin-bottom:7px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  border-left:3px solid #555;
  transition:.12s;
}
.ticker-pill:hover{ transform:translateX(2px); background:rgba(255,255,255,0.06); }
.tp-up{ border-left-color:#00C805; }
.tp-down{ border-left-color:#FF3B30; }
.tp-neutral{ border-left-color:#FFD700; }
.tp-name{ font-weight:900; font-size:12px; color:#ddd; }
.tp-price{ font-weight:850; font-size:12px; color:#fff; margin-right:6px; }
.tp-pct{ font-size:10px; font-weight:950; }

/* TOP MOVERS */
.top5-link{ text-decoration:none; display:block; }
.top5-row{
  display:flex; justify-content:space-between; align-items:center;
  background:rgba(255,255,255,0.025);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:16px;
  padding:10px 12px;
  margin-bottom:10px;
  transition:.2s;
}
.top5-row:hover{
  background:rgba(255,255,255,0.085);
  transform:translateX(2px);
  border-left:2px solid #FFD700;
}
.badge{
  font-weight:950; color:#000; padding:3px 10px; border-radius:999px; font-size:12px;
}

/* NEWS */
a.news-card-link{ text-decoration:none; display:block; margin-bottom:12px; }
.news-card-box{
  background:#161B22;
  border:1px solid rgba(255,255,255,0.10);
  border-radius:14px;
  padding:16px;
  transition:all .2s;
}
.news-card-box:hover{
  border-color:#FFD700;
  transform:translateY(-2px);
  box-shadow:0 4px 12px rgba(0,0,0,0.24);
}
.nc-title{ color:#fff; font-weight:950; font-size:15px; line-height:1.4; margin-bottom:6px; }
.nc-meta{ color:#888; font-size:12px; display:flex; align-items:center; gap:6px; }
.nc-badge{
  background:rgba(255,215,0,0.15);
  color:#FFD700;
  padding:2px 8px;
  border-radius:999px;
  font-size:10px;
  font-weight:950;
  text-transform:uppercase;
}

/* INPUTS */
.stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input{
  background:#12171E!important; color:#fff!important; border:1px solid #333!important; border-radius:12px!important;
}
.yellowbtn button{
  background:#FFD700!important; color:#000!important; border:none!important;
  font-weight:950!important; border-radius:12px!important;
}
.yellowbtn button:hover{ transform:translateY(-2px); box-shadow:0 5px 15px rgba(255,215,0,0.30); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# HELPERS
# =============================================================================
def human_time_ago(dt: datetime) -> str:
    if not dt:
        return ""
    try:
        now = now_br()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_BR)
        else:
            dt = dt.astimezone(TZ_BR)
        sec = int((now - dt).total_seconds())
        if sec < 60: return "agora"
        m = sec // 60
        if m < 60: return f"{m}m"
        h = m // 60
        if h < 24: return f"{h}h"
        d = h // 24
        return f"{d}d"
    except Exception:
        return ""

@st.cache_data(ttl=600)
def get_usdbrl() -> float:
    if yf is None:
        return 5.80
    try:
        return float(yf.Ticker("BRL=X").history(period="1d")["Close"].iloc[-1])
    except Exception:
        return 5.80

@st.cache_data(ttl=600)
def yf_last_and_prev_close(tickers: list[str]) -> pd.DataFrame:
    if yf is None or not tickers:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])
    try:
        data = yf.download(tickers, period="7d", progress=False, threads=True, group_by="ticker")
    except Exception:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])

    out = []
    for t in tickers:
        try:
            s = None
            if isinstance(data.columns, pd.MultiIndex):
                if ("Close", t) in data.columns: s = data[("Close", t)]
                elif (t, "Close") in data.columns: s = data[(t, "Close")]
            else:
                if "Close" in data.columns: s = data["Close"]
            if s is None:
                continue

            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 2:
                last = float(s.iloc[-1])
                prev = float(s.iloc[-2])
                var_pct = ((last - prev) / prev) * 100 if prev != 0 else 0.0
                out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var_pct})
        except Exception:
            pass
    return pd.DataFrame(out)

# =============================================================================
# B3 MOVERS — TradingView Scanner (rápido, sem API)
# =============================================================================
@st.cache_data(ttl=120)
def tv_scanner_b3(limit=250) -> pd.DataFrame:
    url = "https://scanner.tradingview.com/brazil/scan"
    payload = {
        "filter": [
            {"left":"exchange","operation":"equal","right":"BMFBOVESPA"},
            {"left":"is_primary","operation":"equal","right":True},
            {"left":"type","operation":"in_range","right":["stock","fund","dr"]},
        ],
        "options": {"lang":"pt"},
        "markets": ["brazil"],
        "symbols": {"query":{"types":[]},"tickers":[]},
        "columns": ["name","close","change","volume","description"],
        "sort": {"sortBy":"volume","sortOrder":"desc"},
        "range": [0, int(limit)]
    }
    headers = {"User-Agent":"Mozilla/5.0", "Content-Type":"application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=6)
        if r.status_code != 200:
            return pd.DataFrame(columns=["ticker","last","var_pct","volume"])
        js = r.json()
        data = js.get("data", [])
        rows = []
        for row in data:
            d = row.get("d", [])
            if len(d) >= 4:
                name = str(d[0]).upper()
                close = float(d[1]) if d[1] is not None else None
                chg = float(d[2]) if d[2] is not None else None
                vol = float(d[3]) if d[3] is not None else 0
                if name and close is not None and chg is not None:
                    rows.append({"ticker": name, "last": close, "var_pct": chg, "volume": vol})
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=["ticker","last","var_pct","volume"])
        return df.sort_values("volume", ascending=False)
    except Exception:
        return pd.DataFrame(columns=["ticker","last","var_pct","volume"])

def top5_altas_baixas(df: pd.DataFrame, mode="altas") -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["ticker","last","var_pct"])
    if mode == "altas":
        d = df[df["var_pct"] > 0].sort_values("var_pct", ascending=False).head(5)
    else:
        d = df[df["var_pct"] < 0].sort_values("var_pct", ascending=True).head(5)
    return d[["ticker","last","var_pct"]].reset_index(drop=True)

# =============================================================================
# CRIPTO MOVERS — Binance 24h (sem API)
# =============================================================================
STABLES = {"USDT","USDC","DAI","TUSD","FDUSD","USDP","BRL","EUR","TRY","BUSD"}

@st.cache_data(ttl=120)
def binance_24h_all_usdt() -> pd.DataFrame:
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        r = requests.get(url, timeout=6)
        if r.status_code != 200:
            return pd.DataFrame(columns=["symbol","lastPrice","priceChangePercent","quoteVolume"])
        df = pd.DataFrame(r.json())

        df = df[df["symbol"].astype(str).str.endswith("USDT")].copy()
        leveraged_suffixes = ("UPUSDT","DOWNUSDT","BULLUSDT","BEARUSDT")
        df = df[~df["symbol"].astype(str).str.endswith(leveraged_suffixes)].copy()

        base = df["symbol"].astype(str).str.replace("USDT","", regex=False)
        df = df[~base.isin(STABLES)].copy()

        df["lastPrice"] = pd.to_numeric(df["lastPrice"], errors="coerce")
        df["priceChangePercent"] = pd.to_numeric(df["priceChangePercent"], errors="coerce")
        df["quoteVolume"] = pd.to_numeric(df.get("quoteVolume", 0), errors="coerce").fillna(0)
        df.dropna(subset=["lastPrice","priceChangePercent"], inplace=True)

        return df[["symbol","lastPrice","priceChangePercent","quoteVolume"]].sort_values("quoteVolume", ascending=False)
    except Exception:
        return pd.DataFrame(columns=["symbol","lastPrice","priceChangePercent","quoteVolume"])

def crypto_top5_from_binance(df: pd.DataFrame, mode="altas") -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["ticker","last","var_pct"])
    if mode == "altas":
        d = df[df["priceChangePercent"] > 0].sort_values("priceChangePercent", ascending=False).head(5)
    else:
        d = df[df["priceChangePercent"] < 0].sort_values("priceChangePercent", ascending=True).head(5)

    return pd.DataFrame({
        "ticker": d["symbol"].str.replace("USDT","", regex=False),
        "last": d["lastPrice"],
        "var_pct": d["priceChangePercent"]
    })

# -----------------------------------------------------------------------------
# BTCBRL (Binance) -> Market Monitor (sem API)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=120)
def binance_price(symbol: str) -> float | None:
    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        r = requests.get(url, params={"symbol": symbol}, timeout=6)
        if r.status_code != 200:
            return None
        js = r.json()
        return float(js.get("price"))
    except Exception:
        return None

# =============================================================================
# Bee TV — YouTube Search (precisa YOUTUBE_API_KEY)
# Melhorias:
# - remove seletor de tamanho (fixo)
# - tenta likes >= 20k (se não der, fallback)
# - sem shorts (filtro por duração mínima)
# - favoritos primeiro + views
# =============================================================================
FAVORITE_CHANNELS = [
    "Raul Sena",
    "Bruno Perini",
    "Geração de Valor",
    "Gêmeos Investem",
    "Primo Pobre",
]

LIKE_MIN_STRICT = 20000
MIN_DURATION_SECONDS = 8 * 60  # 8min => corta shorts e muita porcaria curta

def _fav_score(channel_title: str) -> int:
    ch = (channel_title or "").lower()
    for i, fav in enumerate(FAVORITE_CHANNELS):
        if fav.lower() in ch:
            return 1000 - i
    return 0

@st.cache_data(ttl=600)
def youtube_search_raw(query: str, max_results: int = 30) -> list[dict]:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return []

    boost = " ".join(FAVORITE_CHANNELS)
    q_final = f"{query} {boost}".strip()

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": q_final,
        "type": "video",
        "maxResults": int(max_results),
        "order": "date",
        "key": api_key,
        "regionCode": "BR",
        "relevanceLanguage": "pt",
        "safeSearch": "strict",
        "videoEmbeddable": "true",
        # importante: "any" aqui pra não “matar” tudo; o corte vem pela duração real no details
        "videoDuration": "any",
    }
    try:
        r = requests.get(url, params=params, timeout=14)
        if r.status_code != 200:
            return []
        js = r.json()
        items = js.get("items", [])
        out = []
        for it in items:
            vid = it.get("id", {}).get("videoId")
            sn = it.get("snippet", {})
            if not vid:
                continue
            out.append({
                "videoId": vid,
                "title": sn.get("title", "Vídeo"),
                "channelTitle": sn.get("channelTitle", ""),
                "publishedAt": sn.get("publishedAt", ""),
            })
        return out
    except Exception:
        return []

@st.cache_data(ttl=600)
def youtube_videos_details(video_ids: list[str]) -> dict:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key or not video_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"
    chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    out = {}

    for ch in chunks:
        params = {
            "part": "contentDetails,statistics",
            "id": ",".join(ch),
            "key": api_key
        }
        try:
            r = requests.get(url, params=params, timeout=14)
            if r.status_code != 200:
                continue
            js = r.json()
            for it in js.get("items", []):
                vid = it.get("id")
                stats = it.get("statistics", {}) or {}
                cd = it.get("contentDetails", {}) or {}

                # likeCount pode vir ausente em alguns casos; tratamos como 0
                like_count = stats.get("likeCount", 0) or 0
                try:
                    like_count = int(like_count)
                except Exception:
                    like_count = 0

                view_count = stats.get("viewCount", 0) or 0
                try:
                    view_count = int(view_count)
                except Exception:
                    view_count = 0

                out[vid] = {
                    "viewCount": view_count,
                    "likeCount": like_count,
                    "duration": cd.get("duration", ""),
                }
        except Exception:
            pass

    return out

def iso8601_duration_to_seconds(d: str) -> int:
    if not d or not d.startswith("PT"):
        return 0
    d = d.replace("PT", "")
    sec = 0
    num = ""
    for ch in d:
        if ch.isdigit():
            num += ch
        else:
            if not num:
                continue
            val = int(num)
            num = ""
            if ch == "H": sec += val * 3600
            elif ch == "M": sec += val * 60
            elif ch == "S": sec += val
    return sec

@st.cache_data(ttl=600)
def youtube_pick_best(query: str, want=6) -> list[dict]:
    raw = youtube_search_raw(query=query, max_results=30)
    if not raw:
        return []

    ids = [v["videoId"] for v in raw]
    details = youtube_videos_details(ids)

    enriched = []
    for v in raw:
        det = details.get(v["videoId"], {})
        views = int(det.get("viewCount", 0) or 0)
        likes = int(det.get("likeCount", 0) or 0)
        dur = det.get("duration", "")
        dur_sec = iso8601_duration_to_seconds(dur)

        # corta shorts / vídeos curtos
        if dur_sec and dur_sec < MIN_DURATION_SECONDS:
            continue

        enriched.append({
            **v,
            "views": views,
            "likes": likes,
            "fav": _fav_score(v.get("channelTitle","")),
        })

    if not enriched:
        return []

    # 1) tenta STRICT: likes >= 20k
    strict = [x for x in enriched if x["likes"] >= LIKE_MIN_STRICT]

    # 2) ordenação: favoritos primeiro, depois likes, depois views
    def sorter(x):
        return (x["fav"], x["likes"], x["views"])

    strict.sort(key=sorter, reverse=True)
    enriched.sort(key=sorter, reverse=True)

    # 3) monta lista final (se strict não der 6, completa com o resto)
    final = []
    used = set()

    for x in strict:
        if len(final) >= want:
            break
        if x["videoId"] not in used:
            final.append(x)
            used.add(x["videoId"])

    if len(final) < want:
        for x in enriched:
            if len(final) >= want:
                break
            if x["videoId"] not in used:
                final.append(x)
                used.add(x["videoId"])

    return final[:want]

# =============================================================================
# NEWS
# =============================================================================
@st.cache_data(ttl=900)
def get_google_news_items(query: str, limit: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
        items = []
        for e in getattr(feed, "entries", [])[:limit]:
            try:
                p_dt = dtparser.parse(e.published) if dtparser else now_br()
            except Exception:
                p_dt = now_br()
            title = getattr(e, "title", "Notícia").rsplit(" - ", 1)[0]
            source = getattr(e, "source", {}).get("title") or "News"
            items.append({"title": title, "link": e.link, "source": source, "published_dt": p_dt})
        return items
    except Exception:
        return []

# =============================================================================
# CARTEIRA / GASTOS
# =============================================================================
CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]
GASTOS_COLS = ["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"]

if "carteira_df" not in st.session_state:
    st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
if "gastos_df" not in st.session_state:
    st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
if "wallet_mode" not in st.session_state:
    st.session_state["wallet_mode"] = False
if "gastos_mode" not in st.session_state:
    st.session_state["gastos_mode"] = False

def smart_load_csv(uploaded_file, sep_priority=','):
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=sep_priority)
        if len(df.columns) > 1:
            return df
    except Exception:
        pass
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=';' if sep_priority == ',' else ',')
        if len(df.columns) > 1:
            return df
    except Exception:
        pass
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
        return df
    except Exception:
        pass
    return None

@st.cache_data(ttl=900)
def yf_prices_map(tickers: list[str]) -> dict:
    if yf is None or not tickers:
        return {}
    px_df = yf_last_and_prev_close(tickers)
    out = {}
    if px_df is None or px_df.empty:
        return out
    for _, r in px_df.iterrows():
        out[str(r["ticker"])] = float(r["last"])
    return out

def atualizar_precos_carteira_memory(df: pd.DataFrame):
    df = df.copy()
    if df.empty:
        return df, {"total_brl": 0, "pnl_brl": 0, "pnl_pct": 0, "usdbrl": get_usdbrl()}

    usdbrl = get_usdbrl()

    def norm_row(row):
        tipo = str(row.get("Tipo","")).lower()
        a = str(row.get("Ativo","")).strip().upper()
        m = str(row.get("Moeda","BRL")).strip().upper()
        if not a:
            return ""
        if a.endswith(".SA") or a.endswith("-USD") or a.endswith("=X") or a.startswith("^"):
            return a
        if "cripto" in tipo:
            return a if "-" in a else f"{a}-USD"
        has_digit = any(ch.isdigit() for ch in a)
        if m == "BRL" and has_digit and not a.endswith(".SA"):
            return f"{a}.SA"
        return a

    df["Ticker_YF"] = df.apply(norm_row, axis=1)
    df["Preco_Atual"] = 0.0

    is_rf = df["Tipo"].str.contains("Renda Fixa|RF", case=False, na=False)
    df.loc[is_rf, "Preco_Atual"] = df.loc[is_rf, "Preco_Medio"]

    tickers = df.loc[~is_rf, "Ticker_YF"].dropna().unique().tolist()
    px_map = yf_prices_map(tickers)

    for i, row in df.iterrows():
        if bool(is_rf.iloc[i]):
            continue
        df.at[i, "Preco_Atual"] = float(px_map.get(row["Ticker_YF"], 0.0))

    for c in ["Qtd", "Preco_Medio"]:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace('.', '').str.replace(',', '.')
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["Preco_Atual_BRL"] = df["Preco_Atual"]
    mask_usd_source = df["Ticker_YF"].astype(str).str.endswith("-USD")
    df.loc[mask_usd_source, "Preco_Atual_BRL"] *= usdbrl

    mask_user_usd = df["Moeda"].astype(str).str.upper() == "USD"
    df["Preco_Medio_BRL"] = df["Preco_Medio"]
    df.loc[mask_user_usd, "Preco_Medio_BRL"] = df.loc[mask_user_usd, "Preco_Medio"] * usdbrl

    df["Total_BRL"] = df["Qtd"] * df["Preco_Atual_BRL"]
    df["Custo_BRL"] = df["Qtd"] * df["Preco_Medio_BRL"]
    df["PnL_BRL"] = df["Total_BRL"] - df["Custo_BRL"]
    df["PnL_Pct"] = df.apply(lambda x: (x["PnL_BRL"] / x["Custo_BRL"] * 100) if x["Custo_BRL"] > 0 else 0, axis=1)

    total = df["Total_BRL"].sum()
    pnl = df["PnL_BRL"].sum()
    custo = df["Custo_BRL"].sum()
    pnl_pct = (pnl / custo * 100) if custo > 0 else 0
    return df, {"total_brl": total, "pnl_brl": pnl, "pnl_pct": pnl_pct, "usdbrl": usdbrl}

# =============================================================================
# UI HELPERS
# =============================================================================
def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

def kpi_card(title, value, sub, color=None):
    st.markdown(
        f"""<div class="bee-card" style="{f'border-top: 3px solid {color}' if color else ''}">
            <div class="card-title">{title}</div>
            <div class="kpi">{value}</div>
            <div class="sub">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )

def investidor10_link_b3(ticker: str) -> str:
    t = (ticker or "").upper().replace(".SA","").strip()
    return f"https://investidor10.com.br/acoes/{t}/"

def render_top5(df: pd.DataFrame, kind="acao", empty_text="Sem dados."):
    if df is None or df.empty:
        st.caption(empty_text)
        return
    for _, row in df.iterrows():
        nome = str(row["ticker"]).replace(".SA","").replace("-USD","")
        preco = float(row["last"])
        var = float(row["var_pct"])
        badge_bg = "#4CAF50" if var >= 0 else "#FF3B30"

        if kind == "acao":
            link = investidor10_link_b3(nome)
            price_line = fmt_money_brl(preco, 2)
        else:
            link = f"https://www.binance.com/pt-BR/trade/{nome}_USDT"
            price_line = fmt_money_usd(preco, 4) if preco < 10 else fmt_money_usd(preco, 2)

        st.markdown(
            f"""
            <a href="{link}" target="_blank" class="top5-link">
                <div class="top5-row">
                    <div style="font-weight:950; color:#eee; font-size:14px;">{nome}</div>
                    <div style="text-align:right;">
                        <span class="badge" style="background:{badge_bg};">{fmt_pct(var, 2, True)}</span>
                        <div style="font-size:10px; color:#777; margin-top:3px;">{price_line}</div>
                    </div>
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )

# =============================================================================
# NAV
# =============================================================================
if "page" not in st.session_state:
    st.session_state["page"] = "🏠 Home"
page = st.session_state["page"]

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    if logo_img:
        st.image(logo_img, width=280)
    else:
        st.markdown("## 🐝 Bee Finanças")

    st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
    nav_btn("🏠 Home", "🏠 Home")
    nav_btn("📰 Notícias", "📰 Notícias")

    st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
    nav_btn("🔍 Analisar", "🔍 Analisar")
    nav_btn("💼 Carteira", "💼 Carteira")
    nav_btn("💸 Controle", "💸 Controle")
    nav_btn("🧮 Calculadoras", "🧮 Calculadoras")

    st.markdown("<p class='menu-header'>Learn</p>", unsafe_allow_html=True)
    nav_btn("🍿 Bee TV", "🍿 Bee TV")
    nav_btn("🎓 Aprenda", "🎓 Aprenda")

    st.divider()

    # MARKET MONITOR (sem SELIC)
    try:
        st.markdown("<div style='font-size:12px; color:#666; font-weight:950; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>", unsafe_allow_html=True)

        snap = yf_last_and_prev_close(["^BVSP", "BRL=X", "BTC-USD"]) if yf else pd.DataFrame()
        name_map = {"^BVSP":"IBOV", "BRL=X":"USD", "BTC-USD":"BTC (US$)"}

        if snap is not None and not snap.empty:
            for _, row in snap.iterrows():
                cor = "tp-up" if float(row["var_pct"]) >= 0 else "tp-down"
                color = "#00C805" if float(row["var_pct"]) >= 0 else "#FF3B30"
                tk = str(row["ticker"])
                nome = name_map.get(tk, tk)
                val = float(row["last"])

                if tk == "BRL=X":
                    fmt_val = fmt_money_brl(val, 2)
                elif tk == "BTC-USD":
                    fmt_val = f"$ {fmt_num_br(val, 0)}"
                else:
                    fmt_val = f"{fmt_num_br(val, 0)}"

                st.markdown(
                    f"""
                    <div class='ticker-pill {cor}'>
                      <span class='tp-name'>{nome}</span>
                      <div style='display:flex; align-items:center;'>
                        <span class='tp-price'>{fmt_val}</span>
                        <span class='tp-pct' style='color:{color};'>{fmt_pct(float(row['var_pct']), 2, True)}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            btc_brl = binance_price("BTCBRL")
            if btc_brl is None:
                btc_row = snap[snap["ticker"] == "BTC-USD"]
                usd_row = snap[snap["ticker"] == "BRL=X"]
                if (not btc_row.empty) and (not usd_row.empty):
                    btc_brl = float(btc_row.iloc[0]["last"]) * float(usd_row.iloc[0]["last"])

            if btc_brl is not None:
                st.markdown(
                    f"""
                    <div class='ticker-pill tp-neutral'>
                      <span class='tp-name'>BTC (R$)</span>
                      <div style='display:flex; align-items:center;'>
                        <span class='tp-price'>{fmt_money_brl(float(btc_brl), 0)}</span>
                        <span class='tp-pct' style='color:#FFD700;'>live</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    except Exception:
        pass

# =============================================================================
# HEADER (com refresh pequeno e escondido)
# =============================================================================
h1, h2, h3 = st.columns([6, 2, 0.8])
with h1:
    st.markdown(
        """
        <div style="margin:6px 0 2px 0;">
          <div style="font-size:30px; font-weight:950; color:#FFD700; line-height:1;">Bee Finanças</div>
          <div style="color:#666; font-size:12px;">Carteira • Gastos • Notícias • Educação</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h2:
    st.markdown(
        f"""<div style="display:flex; justify-content:flex-end; align-items:center; height:100%;">
              <div class="header-pill">🕒 {now_br().strftime("%d/%m/%Y %H:%M")}</div>
            </div>""",
        unsafe_allow_html=True,
    )
with h3:
    st.markdown("<div class='iconbtn' style='display:flex; justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("↻", help="Atualizar dados"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin-top:8px'>", unsafe_allow_html=True)

# =============================================================================
# PAGES
# =============================================================================

# -----------------------------------------------------------------------------
# 🏠 HOME
# -----------------------------------------------------------------------------
if page == "🏠 Home":
    snap = yf_last_and_prev_close(["^BVSP", "BRL=X", "BTC-USD"]) if yf else pd.DataFrame()

    def safe_row(df, t):
        try:
            r = df[df["ticker"] == t]
            if r.empty:
                return None
            return r.iloc[0]
        except Exception:
            return None

    ibov = safe_row(snap, "^BVSP")
    usd = safe_row(snap, "BRL=X")
    btc = safe_row(snap, "BTC-USD")

    btc_brl_live = binance_price("BTCBRL")
    if btc_brl_live is None and (btc is not None) and (usd is not None):
        btc_brl_live = float(btc["last"]) * float(usd["last"])

    c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.1, 1.2])
    with c1:
        if ibov is not None:
            kpi_card("IBOV", f"{fmt_num_br(float(ibov['last']), 0)}", f"{fmt_pct(float(ibov['var_pct']), 2, True)} (dia)", color="#FFD700")
        else:
            kpi_card("IBOV", "—", "…")
    with c2:
        if usd is not None:
            kpi_card("USD/BRL", fmt_money_brl(float(usd["last"]), 2), f"{fmt_pct(float(usd['var_pct']), 2, True)} (dia)", color="#FFD700")
        else:
            kpi_card("USD/BRL", "—", "…")
    with c3:
        if btc is not None:
            kpi_card("BTC (US$)", f"$ {fmt_num_br(float(btc['last']), 0)}", f"{fmt_pct(float(btc['var_pct']), 2, True)} (dia)", color="#FFD700")
        else:
            kpi_card("BTC (US$)", "—", "…")
    with c4:
        if btc_brl_live is not None:
            kpi_card("BTC (R$)", fmt_money_brl(float(btc_brl_live), 0), "live (Binance)", color="#FFD700")
        else:
            kpi_card("BTC (R$)", "—", "…")

    st.write("")
    st.markdown("### 🚀 Altas e Baixas")
    tab_b3, tab_cripto = st.tabs(["🇧🇷 B3 (rápido)", "₿ Cripto (Binance 24h)"])

    with tab_b3:
        df_b3 = tv_scanner_b3(limit=250)
        ca, cb = st.columns(2)
        with ca:
            st.caption("Top 5 Altas")
            render_top5(top5_altas_baixas(df_b3, "altas"), kind="acao", empty_text="Sem altas > 0% agora.")
        with cb:
            st.caption("Top 5 Baixas")
            render_top5(top5_altas_baixas(df_b3, "baixas"), kind="acao", empty_text="Sem baixas < 0% agora.")

    with tab_cripto:
        df_bn = binance_24h_all_usdt()
        ca, cb = st.columns(2)
        with ca:
            st.caption("Top 5 Altas (24h)")
            render_top5(crypto_top5_from_binance(df_bn, "altas"), kind="cripto", empty_text="Sem altas > 0%.")
        with cb:
            st.caption("Top 5 Baixas (24h)")
            render_top5(crypto_top5_from_binance(df_bn, "baixas"), kind="cripto", empty_text="Sem baixas < 0%.")

    st.write("")
    st.markdown("### 📰 Notícias")
    news = get_google_news_items("investimentos+brasil", limit=10)
    if news:
        for n in news:
            ago = human_time_ago(n["published_dt"])
            st.markdown(
                f"""
                <a href="{n['link']}" target="_blank" class="news-card-link">
                  <div class="news-card-box">
                    <div class="nc-title">{n['title']}</div>
                    <div class="nc-meta">
                      <span class="nc-badge">{n['source']}</span>
                      <span>• {ago}</span>
                    </div>
                  </div>
                </a>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Sem notícias no momento.")

# -----------------------------------------------------------------------------
# 📰 NOTÍCIAS
# -----------------------------------------------------------------------------
elif page == "📰 Notícias":
    st.markdown("## 📰 Notícias")
    tema = st.selectbox("Tema", ["Mercado", "Brasil", "Cripto", "Ações", "Juros"], index=0)
    q = st.text_input("Buscar", placeholder="Ex: Petrobras, inflação, bitcoin…")
    base_map = {
        "Mercado": "investimentos+mercado",
        "Brasil": "economia+brasil",
        "Cripto": "bitcoin+cripto+mercado",
        "Ações": "bolsa+ações+brasil",
        "Juros": "copom+juros",
    }
    query = q.strip() if q.strip() else base_map[tema]
    items = get_google_news_items(query, limit=18)
    if not items:
        st.info("Sem notícias agora.")
    else:
        for n in items:
            ago = human_time_ago(n["published_dt"])
            st.markdown(
                f"""
                <a href="{n['link']}" target="_blank" class="news-card-link">
                    <div class="news-card-box">
                        <div class="nc-title">{n['title']}</div>
                        <div class="nc-meta">
                            <span class="nc-badge">{n['source']}</span>
                            <span>• {ago}</span>
                        </div>
                    </div>
                </a>
                """,
                unsafe_allow_html=True,
            )

# -----------------------------------------------------------------------------
# 🔍 ANALISAR (yfinance)
# -----------------------------------------------------------------------------
elif page == "🔍 Analisar":
    st.markdown("## 🔍 Analisar Ativo")
    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input("Ativo", placeholder="WEGE3 • PETR4 • AAPL • BTC").upper().strip()
    with c_p:
        periodo = st.selectbox("Zoom", ["1mo", "6mo", "1y", "5y", "max"], index=2)

    if not ticker:
        st.info("Digite um ativo e pressione Enter.")
    else:
        if yf is None:
            st.error("yfinance não está disponível. Confere o requirements.txt.")
        else:
            def normalize_guess(t):
                t = t.strip().upper()
                if t.endswith(".SA") or t.endswith("-USD") or t.endswith("=X") or t.startswith("^"):
                    return t
                if any(ch.isdigit() for ch in t):
                    return t + ".SA"
                return t + "-USD"

            tk = normalize_guess(ticker)

            try:
                tk_obj = yf.Ticker(tk)
                hist = tk_obj.history(period=periodo)
                info = {}
                try:
                    info = tk_obj.info or {}
                except Exception:
                    info = {}

                title_name = info.get("longName") or info.get("shortName") or tk
                st.markdown(f"### {title_name}")

                if not hist.empty and px:
                    fig = px.line(hist, y="Close")
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=320,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3, col4 = st.columns(4)
                price = float(hist["Close"].iloc[-1]) if (hist is not None and not hist.empty) else None
                dy = info.get("dividendYield", None)
                pe = info.get("trailingPE", None) or info.get("forwardPE", None)
                mc = info.get("marketCap", None)

                with col1: st.metric("Preço", fmt_num_br(price, 2) if price is not None else "—")
                with col2: st.metric("DY", f"{fmt_num_br(dy*100,2)}%" if isinstance(dy,(int,float)) else "—")
                with col3: st.metric("P/L", fmt_num_br(pe, 2) if isinstance(pe,(int,float)) else "—")
                with col4: st.metric("Market Cap", fmt_num_br(mc, 0) if isinstance(mc,(int,float)) else "—")

                summary = info.get("longBusinessSummary", "")
                if summary and GoogleTranslator:
                    try:
                        summary = GoogleTranslator(source="auto", target="pt").translate(summary)
                    except Exception:
                        pass
                if summary:
                    with st.expander("Resumo (PT-BR)"):
                        st.write(summary)

            except Exception:
                st.error("Não consegui puxar esse ativo agora. Tenta outro ticker ou clique no ↻ pequeno no topo.")

# -----------------------------------------------------------------------------
# 💼 CARTEIRA
# -----------------------------------------------------------------------------
elif page == "💼 Carteira":
    st.markdown("## 💼 Carteira (Cofre Local)")
    df = st.session_state["carteira_df"]
    wallet_active = (not df.empty) or st.session_state["wallet_mode"]

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("📂 Carregar 'minha_carteira.csv'", type=["csv"], key="uploader_start")
            if uploaded_file:
                df_loaded = smart_load_csv(uploaded_file)
                if df_loaded is not None:
                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            st.success("📝 **Começar do Zero**")
            if st.button("🚀 Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                st.rerun()
    else:
        with st.spinner("Atualizando preços..."):
            df_calc, kpi = atualizar_precos_carteira_memory(df)

        k1, k2, k3 = st.columns(3)
        with k1: kpi_card("Total", fmt_money_brl(kpi["total_brl"], 2), "Patrimônio")
        with k2:
            kpi_card("Resultado", fmt_money_brl(kpi["pnl_brl"], 2), fmt_pct(kpi["pnl_pct"], 2, True),
                     color="#4CAF50" if kpi["pnl_brl"] >= 0 else "#FF3B30")
        with k3: kpi_card("Ativos", f"{len(df_calc)}", "Diversificação")

        st.dataframe(df_calc[CARTEIRA_COLS], use_container_width=True, height=300)
        st.download_button("⬇️ Baixar CSV", df.to_csv(index=False).encode("utf-8"), "minha_carteira.csv", "text/csv", type="primary")

# -----------------------------------------------------------------------------
# 💸 CONTROLE
# -----------------------------------------------------------------------------
elif page == "💸 Controle":
    st.markdown("## 💸 Controle de Gastos")
    st.info("Se quiser, eu restauro o módulo completo do seu Controle (entrada/saída, pie, extrato, csv).")

# -----------------------------------------------------------------------------
# 🧮 CALCULADORAS
# -----------------------------------------------------------------------------
elif page == "🧮 Calculadoras":
    st.markdown("## 🧮 Calculadoras")
    tabs = st.tabs(["Juros Compostos", "Tempo p/ Milhão", "Renda Fixa"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        vp = c1.number_input("Inicial (R$)", value=1000.0, step=100.0)
        pmt = c2.number_input("Mensal (R$)", value=500.0, step=50.0)
        taxa = c3.number_input("Taxa Anual (%)", value=10.0, step=0.5)
        anos = c4.slider("Anos", 1, 50, 10)
        if st.button("Calcular Juros"):
            i = (taxa/100)/12
            n = anos*12
            total = vp*((1+i)**n) + pmt*(((1+i)**n - 1)/i) if i > 0 else vp + pmt*n
            st.success(f"Total estimado: {fmt_money_brl(total, 2)}")

    with tabs[1]:
        c1, c2 = st.columns(2)
        invest_mensal = c1.number_input("Aporte Mensal (R$)", value=2000.0, step=100.0)
        taxa_anual = c2.number_input("Rentabilidade Anual (%)", value=10.0, step=0.5)
        if st.button("Calcular Tempo"):
            i = (taxa_anual/100)/12
            if invest_mensal <= 0 or i <= 0:
                st.error("Aporte e taxa precisam ser > 0.")
            else:
                n = math.log((1000000 * i) / invest_mensal + 1) / math.log(1 + i)
                anos_out = (n/12)
                st.success(f"Tempo estimado: {fmt_num_br(anos_out, 1)} anos")

    with tabs[2]:
        c1, c2 = st.columns(2)
        val = c1.number_input("Valor (R$)", value=1000.0, step=100.0)
        cdi = c2.number_input("CDI (%)", value=13.0, step=0.1)
        if st.button("Retorno 1 ano"):
            st.info(f"Estimativa 1 ano: {fmt_money_brl(val * (1 + cdi/100), 2)}")

# -----------------------------------------------------------------------------
# 🍿 BEE TV (sem seletor de tamanho | tenta likes >= 20k)
# -----------------------------------------------------------------------------
elif page == "🍿 Bee TV":
    st.markdown("## 🍿 Bee TV")
    st.caption("6 vídeos • favoritos primeiro • sem shorts • tenta likes ≥ 20k")

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    query = st.text_input("Pesquisar", value="investimentos").strip()

    if not api_key:
        st.warning("Bee TV precisa de YOUTUBE_API_KEY para buscar vídeos novos.")
        st.markdown(
            """
**Como configurar rápido:**
- Windows (PowerShell): `setx YOUTUBE_API_KEY "SUA_CHAVE"`
- Depois feche e abra o PyCharm/terminal e rode o app de novo.
- Streamlit Cloud: Settings → Secrets → `YOUTUBE_API_KEY="SUA_CHAVE"`
""")
    else:
        st.caption("⭐ Priorizando: Raul Sena • Bruno Perini • Geração de Valor • Gêmeos Investem • Primo Pobre")
        with st.spinner("Buscando vídeos melhores..."):
            vids = youtube_pick_best(query=query, want=6)

        if not vids:
            st.info("Sem vídeos agora. Tenta outro termo (ex: 'ações', 'dividendos', 'renda fixa') ou clique no ↻ pequeno no topo.")
        else:
            cols = st.columns(3)
            for i, v in enumerate(vids):
                with cols[i % 3]:
                    st.video(f"https://www.youtube.com/watch?v={v['videoId']}")
                    likes = v.get("likes", 0) or 0
                    views = v.get("views", 0) or 0
                    st.caption(
                        f"{v['title']} • {v['channelTitle']} • 👍 {fmt_num_br(likes,0)} • 👀 {fmt_num_br(views,0)}"
                    )

# -----------------------------------------------------------------------------
# 🎓 APRENDA (RESTURADO)
# -----------------------------------------------------------------------------
elif page == "🎓 Aprenda":
    st.markdown("## 🎓 Aprenda a Investir")
    tab_videos, tab_lib = st.tabs(["📺 Vídeos", "📚 Biblioteca"])

    with tab_videos:
        st.markdown("#### 🚀 Começando do Zero")
        videos_aprenda = [
            "https://www.youtube.com/watch?v=bx-sTOSteRA",
            "https://www.youtube.com/watch?v=J25ZMPx7J1s",
            "https://www.youtube.com/watch?v=geE3TUzHFTI",
            "https://www.youtube.com/watch?v=HYe9tSqSDA0",
        ]
        for i in range(0, len(videos_aprenda), 2):
            c1, c2 = st.columns(2)
            with c1:
                st.video(videos_aprenda[i])
            with c2:
                if i + 1 < len(videos_aprenda):
                    st.video(videos_aprenda[i+1])

    with tab_lib:
        st.markdown("#### 📚 Livros Recomendados")
        books = [
            {"title":"Os Segredos da Mente Milionária", "author":"T. Harv Eker", "link":"https://amzn.to/3ueEorO"},
            {"title":"Pai Rico, Pai Pobre", "author":"Robert T. Kiyosaki", "link":"https://amzn.to/3SDPqAb"},
            {"title":"O Homem Mais Rico da Babilônia", "author":"George S. Clason", "link":"https://amzn.to/48b6i9P"},
            {"title":"Faça Fortuna com Ações", "author":"Décio Bazin", "link":"https://amzn.to/4cfPs8q"},
            {"title":"O Investidor Inteligente", "author":"Benjamin Graham", "link":"https://amzn.to/3Us6VVL"},
            {"title":"Ações Comuns Lucros Extraordinários", "author":"Philip A. Fisher", "link":"https://amzn.to/3Une9tZ"},
            {"title":"O Rei dos Dividendos", "author":"Luiz Barsi Filho", "link":"https://amzn.to/4meVoUQ"},
            {"title":"A Lógica do Cisne Negro", "author":"Nassim Taleb", "link":"https://amzn.to/42nk7gf"},
            {"title":"Princípios", "author":"Ray Dalio", "link":"https://amzn.to/3HL1fOI"},
        ]
        for b in books:
            with st.container():
                c_icon, c_info, c_btn = st.columns([0.5, 3, 1])
                with c_icon:
                    st.markdown("📘", unsafe_allow_html=True)
                with c_info:
                    st.markdown(f"**{b['title']}**")
                    st.caption(f"Autor: {b['author']}")
                with c_btn:
                    st.link_button("Comprar", b["link"])
                st.markdown("---")

else:
    st.write("…")
