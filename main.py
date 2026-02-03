# Bee Finanças — Streamlit App (vFINAL)
# ---------------------------------------------------------------
# Arquivo: main.py
# Requisitos: streamlit, pandas, yfinance, plotly, feedparser, requests, pillow, deep-translator, python-dateutil
# ---------------------------------------------------------------

import os
import re
import math
import warnings
from datetime import datetime, timezone, timedelta

import streamlit as st
import pandas as pd
import requests
import feedparser
from PIL import Image

warnings.filterwarnings("ignore")

# =========================
# CONFIG
# =========================
APP_VERSION = "v23.2 (FINAL)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")

# IMPORTS opcionais
try:
    import yfinance as yf
except:
    yf = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except:
    go = None
    px = None

try:
    from dateutil import parser as dtparser
except:
    dtparser = None

try:
    from deep_translator import GoogleTranslator
except:
    GoogleTranslator = None


# =========================
# HELPERS VISUAIS / FORMAT
# =========================
def process_logo_transparency(image_path):
    if not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            # remove fundo branco
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img
    except:
        return None


def fmt_br_money(v, prefix="R$"):
    try:
        v = float(v)
    except:
        return "—"
    s = f"{v:,.2f}"  # 1,234,567.89
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234.567,89
    return f"{prefix} {s}"


def fmt_br_int(v):
    try:
        v = float(v)
    except:
        return "—"
    s = f"{v:,.0f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def fmt_pct(v):
    try:
        v = float(v)
    except:
        return "—"
    s = f"{v:+.2f}%"
    s = s.replace(".", ",")
    return s


def human_time_ago(dt: datetime) -> str:
    if not dt:
        return ""
    try:
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        sec = int((now - dt).total_seconds())
        if sec < 60:
            return "agora"
        m = sec // 60
        if m < 60:
            return f"{m}m"
        h = m // 60
        if h < 24:
            return f"{h}h"
        d = h // 24
        return f"{d}d"
    except:
        return ""


def normalize_ticker(ativo: str, tipo: str, moeda: str) -> str:
    a = (ativo or "").strip().upper()
    if not a:
        return ""
    if a.endswith(".SA") or a.endswith("-USD") or a.endswith("=X") or a.startswith("^"):
        return a
    if tipo == "Cripto":
        return a if "-" in a else f"{a}-USD"
    if a in ("BRL=X", "USDBRL", "USD", "DOLAR"):
        return "BRL=X"
    has_digit = any(ch.isdigit() for ch in a)
    if moeda == "BRL" and has_digit and not a.endswith(".SA"):
        return f"{a}.SA"
    return a


def format_market_cap(x: float) -> str:
    if not x:
        return "—"
    try:
        x = float(x)
    except:
        return "—"
    if x >= 1e12:
        return f"{x/1e12:.2f} T".replace(".", ",")
    if x >= 1e9:
        return f"{x/1e9:.2f} B".replace(".", ",")
    if x >= 1e6:
        return f"{x/1e6:.2f} M".replace(".", ",")
    return fmt_br_int(x)


# =========================
# STREAMLIT CONFIG
# =========================
logo_img = process_logo_transparency(LOGO_PATH)
page_icon = logo_img if logo_img else "🐝"

st.set_page_config(
    page_title="Bee Finanças",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# CSS (premium, limpo, menos texto)
# =========================
st.markdown(
    """
<style>
.stApp{
  background:
    radial-gradient(circle at 12% 10%, rgba(255, 215, 0, 0.06), transparent 35%),
    radial-gradient(circle at 88% 88%, rgba(89, 0, 179, 0.10), transparent 35%),
    #0B0F14;
}
h1, h2, h3, h4 {
  color: #FFD700 !important;
  font-family: 'Inter', sans-serif;
  font-weight: 900;
  letter-spacing: -0.02em;
}
section[data-testid="stSidebar"]{
  background: #090C10;
  border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] img {
  display: block;
  margin-left: auto;
  margin-right: auto;
  margin-bottom: 10px;
  object-fit: contain;
  max-width: 100%;
}

/* menos espaçamento feio */
div[data-testid="stVerticalBlock"] { gap: 0.28rem !important; }
div[data-testid="stSidebarUserContent"] .stButton { margin-bottom: 0px !important; }

/* nav button */
.navbtn button {
  width: 100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%) !important;
  color: #cfcfcf !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
  border-radius: 10px !important;
  padding: 0.55rem 1rem !important;
  font-weight: 750 !important;
  font-size: 14px !important;
  text-align: left !important;
  height: 44px !important;
  display: flex !important;
  align-items: center !important;
  transition: all 0.18s ease;
}
.navbtn button:hover {
  background: linear-gradient(90deg, rgba(255,215,0,0.10) 0%, rgba(255,215,0,0.02) 100%) !important;
  border-left: 3px solid #FFD700 !important;
  transform: translateX(2px);
  color: #fff !important;
}
.menu-header {
  font-size: 10px;
  text-transform: uppercase;
  color: #555;
  font-weight: 900;
  letter-spacing: 1px;
  margin-top: 12px;
  margin-bottom: 6px;
  padding-left: 6px;
}

/* cards */
.bee-card{
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(6px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
.card-title{
  color: rgba(255,215,0,0.95);
  font-weight: 900;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}
.kpi{
  color:#fff;
  font-weight: 900;
  font-size: 22px; /* menor pra não quebrar */
  line-height: 1.1;
}
.sub{ color: #707070; font-size: 12px; }

/* top refresh - pequeno */
.iconbtn button{
  width: 42px !important;
  height: 38px !important;
  border-radius: 10px !important;
  padding: 0px !important;
  font-weight: 900 !important;
}
.iconbtn button:hover{
  transform: translateY(-1px);
}

/* market monitor */
.ticker-pill {
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 3px solid #555;
  transition: 0.12s;
}
.ticker-pill:hover { transform: translateX(2px); background: rgba(255,255,255,0.06); }
.tp-up { border-left-color: #00C805; }
.tp-down { border-left-color: #FF3B30; }
.tp-neutral { border-left-color: #FFD700; }
.tp-name { font-weight: 800; font-size: 12px; color: #ddd; }
.tp-price { font-weight: 800; font-size: 12px; color: #fff; margin-right: 8px; }
.tp-pct { font-size: 10px; font-weight: 900; }

/* news card */
a.news-card-link { text-decoration: none; display:block; margin-bottom: 10px; }
.news-card-box {
  background: #161B22;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 14px;
  transition: all 0.18s ease;
}
.news-card-box:hover {
  border-color: rgba(255,215,0,0.7);
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.22);
}
.nc-title { color:#fff; font-weight: 850; font-size: 14px; line-height: 1.35; margin-bottom: 6px; }
.nc-meta { color:#8a8a8a; font-size: 12px; display:flex; gap: 8px; align-items:center; }
.nc-badge { background: rgba(255,215,0,0.14); color:#FFD700; padding:2px 8px; border-radius: 6px; font-size: 10px; font-weight: 900; text-transform: uppercase; }

/* inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
  background: #12171E !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 12px !important;
}
.yellowbtn button{
  background: #FFD700 !important;
  color:#000 !important;
  border: none !important;
  font-weight: 900 !important;
  border-radius: 12px !important;
}
.yellowbtn button:hover{
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(255,215,0,0.25);
}

/* esconder textos chatos */
small, .stCaption { color: rgba(255,255,255,0.35) !important; }

/* footer version */
.footer {
  margin-top: 16px;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.35);
  font-size: 12px;
  display:flex;
  justify-content: space-between;
  align-items:center;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# CACHE / DATA FETCH
# =========================
@st.cache_data(ttl=600)
def yf_last_and_prev_close(tickers: list[str]) -> pd.DataFrame:
    if yf is None or not tickers:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])
    try:
        data = yf.download(tickers, period="7d", progress=False, threads=True, group_by="ticker")
    except:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])

    out = []
    for t in tickers:
        try:
            s = None
            if isinstance(data.columns, pd.MultiIndex):
                if ("Close", t) in data.columns:
                    s = data[("Close", t)]
                elif (t, "Close") in data.columns:
                    s = data[(t, "Close")]
            else:
                s = data["Close"]

            if s is not None:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 2:
                    last = float(s.iloc[-1])
                    prev = float(s.iloc[-2])
                    var_pct = ((last - prev) / prev) * 100 if prev else 0.0
                    out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var_pct})
        except:
            pass

    return pd.DataFrame(out)


@st.cache_data(ttl=60)
def binance_prices_btc_brl():
    """
    BTCBRL e var 24h pela Binance (sem API key).
    """
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=4)
        if r.status_code != 200:
            return None
        j = r.json()
        # pega BTCBRL e USDTBRL (fallback)
        btcbrl = next((x for x in j if x.get("symbol") == "BTCBRL"), None)
        if btcbrl:
            last = float(btcbrl["lastPrice"])
            pct = float(btcbrl["priceChangePercent"])
            return {"price": last, "pct": pct, "source": "binance"}
        # fallback: BTCUSDT * USDTBRL
        btcusdt = next((x for x in j if x.get("symbol") == "BTCUSDT"), None)
        usdtbrl = next((x for x in j if x.get("symbol") == "USDTBRL"), None)
        if btcusdt and usdtbrl:
            last = float(btcusdt["lastPrice"]) * float(usdtbrl["lastPrice"])
            pct = float(btcusdt["priceChangePercent"])
            return {"price": last, "pct": pct, "source": "binance_calc"}
    except:
        pass
    return None


@st.cache_data(ttl=900)
def get_google_news_items(query: str, limit: int = 6) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
        items = []
        for e in getattr(feed, "entries", [])[:limit]:
            try:
                p_dt = dtparser.parse(e.published) if dtparser else datetime.now()
            except:
                p_dt = datetime.now()
            title = getattr(e, "title", "Notícia").rsplit(" - ", 1)[0]
            source = getattr(e, "source", {}).get("title") or "News"
            items.append({"title": title, "link": e.link, "source": source, "published_dt": p_dt})
        return items
    except:
        return []


@st.cache_data(ttl=1200)
def yf_info_extended(ticker: str) -> dict:
    if yf is None or not ticker:
        return {}
    try:
        tk = yf.Ticker(ticker)
        current_price = 0.0
        try:
            if hasattr(tk, "fast_info"):
                current_price = tk.fast_info.last_price
            else:
                h = tk.history(period="1d")
                if not h.empty:
                    current_price = h["Close"].iloc[-1]
        except:
            pass
        inf = tk.info or {}

        def safe_get(keys, d="—"):
            for k in keys:
                if k in inf and inf[k]:
                    return inf[k]
            return d

        summary = safe_get(["longBusinessSummary"], "")
        if summary and GoogleTranslator:
            try:
                summary = GoogleTranslator(source="auto", target="pt").translate(summary)
            except:
                pass

        return {
            "currentPrice": current_price,
            "longName": safe_get(["longName", "shortName"], ticker),
            "sector": safe_get(["sector"]),
            "industry": safe_get(["industry"]),
            "summary": summary,
            "trailingPE": safe_get(["trailingPE", "forwardPE"], None),
            "dividendYield": safe_get(["dividendYield"], None),
            "marketCap": safe_get(["marketCap"], None),
        }
    except:
        return {}


@st.cache_data(ttl=3600)
def get_stock_history_plot(ticker: str, period="1y"):
    if yf is None or go is None:
        return None
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty:
            return None
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df.index,
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name=ticker,
                )
            ]
        )
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
        )
        return fig
    except:
        return None


# =========================
# YouTube API (Bee TV)
# =========================
def get_youtube_key():
    # Cloud: st.secrets; local: env
    try:
        if "YOUTUBE_API_KEY" in st.secrets:
            return str(st.secrets["YOUTUBE_API_KEY"]).strip()
    except:
        pass
    return os.getenv("YOUTUBE_API_KEY", "").strip()


@st.cache_data(ttl=3600)
def yt_find_channel_id(api_key: str, channel_name: str) -> str | None:
    """
    Resolve canal -> channelId
    """
    if not api_key:
        return None
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": channel_name,
            "type": "channel",
            "maxResults": 1,
            "key": api_key,
        }
        r = requests.get(url, params=params, timeout=6)
        if r.status_code != 200:
            return None
        j = r.json()
        items = j.get("items", [])
        if not items:
            return None
        return items[0]["snippet"]["channelId"]
    except:
        return None


@st.cache_data(ttl=900)
def yt_search_videos(api_key: str, query: str, max_results: int = 12, channel_id: str | None = None):
    """
    Busca vídeos (search endpoint).
    """
    if not api_key:
        return []
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": "viewCount",
            "safeSearch": "none",
            "key": api_key,
        }
        if channel_id:
            params["channelId"] = channel_id
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return []
        j = r.json()
        out = []
        for it in j.get("items", []):
            vid = it.get("id", {}).get("videoId")
            sn = it.get("snippet", {})
            if vid:
                out.append(
                    {
                        "videoId": vid,
                        "title": sn.get("title", ""),
                        "channelTitle": sn.get("channelTitle", ""),
                        "publishedAt": sn.get("publishedAt", ""),
                        "thumb": (sn.get("thumbnails", {}).get("high", {}) or sn.get("thumbnails", {}).get("medium", {}) or {}).get("url", ""),
                    }
                )
        return out
    except:
        return_bal = []
        return return_bal


@st.cache_data(ttl=900)
def yt_videos_details(api_key: str, video_ids: list[str]):
    """
    details: duration + stats (likes/views)
    """
    if not api_key or not video_ids:
        return {}
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "maxResults": len(video_ids),
            "key": api_key,
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return {}
        j = r.json()
        mp = {}
        for it in j.get("items", []):
            vid = it.get("id")
            cd = it.get("contentDetails", {})
            stt = it.get("statistics", {})
            mp[vid] = {
                "duration": cd.get("duration", "PT0S"),
                "viewCount": int(stt.get("viewCount", 0) or 0),
                "likeCount": int(stt.get("likeCount", 0) or 0),
            }
        return mp
    except:
        return {}


def iso8601_duration_to_seconds(dur: str) -> int:
    # Ex: PT1H2M3S
    if not dur or not dur.startswith("PT"):
        return 0
    h = m = s = 0
    m1 = re.search(r"(\d+)H", dur)
    m2 = re.search(r"(\d+)M", dur)
    m3 = re.search(r"(\d+)S", dur)
    if m1:
        h = int(m1.group(1))
    if m2:
        m = int(m2.group(1))
    if m3:
        s = int(m3.group(1))
    return h * 3600 + m * 60 + s


def build_bee_tv_results(api_key: str, base_query: str, limit: int = 6):
    """
    Estratégia:
    1) Busca por canal favorito (prioridade) com query "base_query + canal"
    2) Se faltar, busca geral com base_query
    3) Filtra: sem shorts (< 90s), remove duplicados
    4) Se ficar vazio por filtros, relaxa automaticamente
    """
    favorites = ["Raul Sena", "Bruno Perini", "Geração de Valor", "Gêmeos Investem", "Primo Pobre"]

    # tenta resolver channel IDs
    fav_ids = []
    for ch in favorites:
        cid = yt_find_channel_id(api_key, ch)
        if cid:
            fav_ids.append((ch, cid))

    collected = []

    # 1) favoritos primeiro
    for ch, cid in fav_ids:
        q = f"{base_query} {ch}".strip()
        collected += yt_search_videos(api_key, q, max_results=8, channel_id=cid)

    # 2) completa com busca geral
    if len(collected) < limit * 3:
        collected += yt_search_videos(api_key, base_query, max_results=18, channel_id=None)

    # remove duplicados por videoId
    uniq = {}
    for v in collected:
        uniq[v["videoId"]] = v
    vids = list(uniq.values())

    # details
    ids = [v["videoId"] for v in vids]
    det = yt_videos_details(api_key, ids)

    # filtro sem shorts (>= 90s) + preferir vídeos mais longos
    enriched = []
    for v in vids:
        d = det.get(v["videoId"], {})
        sec = iso8601_duration_to_seconds(d.get("duration", "PT0S"))
        enriched.append(
            {
                **v,
                "seconds": sec,
                "views": d.get("viewCount", 0),
                "likes": d.get("likeCount", 0),
            }
        )

    # filtra sem shorts
    filtered = [x for x in enriched if x["seconds"] >= 90]

    # se ficou pouco, relaxa shorts (só remove < 45s)
    if len(filtered) < limit:
        filtered = [x for x in enriched if x["seconds"] >= 45]

    # ordena por views e favoritismo
    favset = set([ch for ch, _ in fav_ids])
    def score(x):
        bonus = 1_000_000_000 if x.get("channelTitle") in favset else 0
        return bonus + (x.get("views", 0) or 0)

    filtered.sort(key=score, reverse=True)

    return filtered[:limit]


# =========================
# APP STATE / DATA TABLES
# =========================
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

if "page" not in st.session_state:
    st.session_state["page"] = "🏠 Home"

if "carteira_selected" not in st.session_state:
    st.session_state["carteira_selected"] = None


def smart_load_csv(uploaded_file, sep_priority=","):
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=sep_priority)
        if len(df.columns) > 1:
            return df
    except:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";" if sep_priority == "," else ",")
        if len(df.columns) > 1:
            return df
    except:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
        return df
    except:
        pass

    return None


@st.cache_data(ttl=600)
def get_usdbrl() -> float:
    if yf is None:
        return 5.80
    try:
        return float(yf.Ticker("BRL=X").history(period="1d")["Close"].iloc[-1])
    except:
        return 5.80


def atualizar_precos_carteira_memory(df):
    df = df.copy()
    if df.empty:
        return df, {"total_brl": 0, "pnl_brl": 0, "pnl_pct": 0, "usdbrl": 5.80}

    usdbrl = get_usdbrl()

    df["Ticker_YF"] = df.apply(lambda r: normalize_ticker(str(r["Ativo"]), str(r["Tipo"]), str(r["Moeda"]).upper()), axis=1)
    df["Preco_Atual"] = 0.0

    # Renda fixa: mantém preço
    is_rf = df["Tipo"].str.contains("Renda Fixa|RF", case=False, na=False)
    df.loc[is_rf, "Preco_Atual"] = df.loc[is_rf, "Preco_Medio"]

    tickers = df.loc[~is_rf, "Ticker_YF"].unique().tolist()
    px_map = {}
    if tickers and yf is not None:
        px_df = yf_last_and_prev_close(tickers)
        for _, r in px_df.iterrows():
            px_map[r["ticker"]] = float(r["last"])

    for i, row in df.iterrows():
        if is_rf[i]:
            continue
        df.at[i, "Preco_Atual"] = float(px_map.get(row["Ticker_YF"], 0.0))

    for c in ["Qtd", "Preco_Medio"]:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["Preco_Atual_BRL"] = df["Preco_Atual"]
    mask_usd_source = df["Ticker_YF"].str.endswith("-USD")
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

    kpi = {"total_brl": total, "pnl_brl": pnl, "pnl_pct": pnl_pct, "usdbrl": usdbrl}
    return df, kpi


def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def kpi_card(title, value, sub="", color=None):
    st.markdown(
        f"""
<div class="bee-card" style="{f'border-top: 3px solid {color};' if color else ''}">
  <div class="card-title">{title}</div>
  <div class="kpi">{value}</div>
  <div class="sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    if logo_img:
        st.image(logo_img, width=280)
    else:
        st.markdown("## 🐝 Bee Finanças")

    st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
    nav_btn("🏠 Home", "🏠 Home")
    nav_btn("📰 Notícias", "📰 News")
    st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
    nav_btn("🔍 Analisar", "🔍 Analisar")
    nav_btn("💼 Carteira", "💼 Carteira")
    nav_btn("💸 Controle", "💸 Controle")
    st.markdown("<p class='menu-header'>Learn</p>", unsafe_allow_html=True)
    nav_btn("🍿 Bee TV", "🍿 Bee TV")
    nav_btn("🎓 Aprenda", "🎓 Aprenda")

    st.divider()

    # Market monitor (sem SELIC)
    try:
        # IBOV + USD via yfinance; BTC em R$ via Binance
        snap = yf_last_and_prev_close(["^BVSP", "BRL=X", "BTC-USD"])
        btcbrl = binance_prices_btc_brl()

        st.markdown(
            "<div style='font-size:12px; color:#666; font-weight:900; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>",
            unsafe_allow_html=True,
        )

        # IBOV
        if not snap.empty and not snap[snap["ticker"] == "^BVSP"].empty:
            row = snap[snap["ticker"] == "^BVSP"].iloc[0]
            cor = "tp-up" if row["var_pct"] >= 0 else "tp-down"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>IBOV</span>
  <div style='display:flex; align-items:center;'>
    <span class='tp-price'>{fmt_br_int(row["last"])}</span>
    <span class='tp-pct' style='color:{"#00C805" if row["var_pct"]>=0 else "#FF3B30"};'>{fmt_pct(row["var_pct"])}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        # USD/BRL
        if not snap.empty and not snap[snap["ticker"] == "BRL=X"].empty:
            row = snap[snap["ticker"] == "BRL=X"].iloc[0]
            cor = "tp-up" if row["var_pct"] >= 0 else "tp-down"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>USD</span>
  <div style='display:flex; align-items:center;'>
    <span class='tp-price'>{fmt_br_money(row["last"])}</span>
    <span class='tp-pct' style='color:{"#00C805" if row["var_pct"]>=0 else "#FF3B30"};'>{fmt_pct(row["var_pct"])}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        # BTC USD
        if not snap.empty and not snap[snap["ticker"] == "BTC-USD"].empty:
            row = snap[snap["ticker"] == "BTC-USD"].iloc[0]
            cor = "tp-up" if row["var_pct"] >= 0 else "tp-down"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>BTC (US$)</span>
  <div style='display:flex; align-items:center;'>
    <span class='tp-price'>$ {fmt_br_int(row["last"])}</span>
    <span class='tp-pct' style='color:{"#00C805" if row["var_pct"]>=0 else "#FF3B30"};'>{fmt_pct(row["var_pct"])}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        # BTC BRL via Binance
        if btcbrl:
            cor = "tp-up" if btcbrl["pct"] >= 0 else "tp-down"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>BTC (R$)</span>
  <div style='display:flex; align-items:center;'>
    <span class='tp-price'>{fmt_br_money(btcbrl["price"])}</span>
    <span class='tp-pct' style='color:{"#00C805" if btcbrl["pct"]>=0 else "#FF3B30"};'>{fmt_pct(btcbrl["pct"])}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
    except:
        pass

    # Footer versão
    st.markdown(
        f"""
<div class="footer">
  <div>Bee Finanças</div>
  <div>{APP_VERSION}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# =========================
# TOP BAR (botão refresh pequeno)
# =========================
top_left, top_right = st.columns([10, 1])
with top_right:
    st.markdown("<div class='iconbtn'>", unsafe_allow_html=True)
    if st.button("↻", help="Atualizar dados"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:rgba(255,255,255,0.06); margin-top:6px'>", unsafe_allow_html=True)

page = st.session_state["page"]

# =========================
# HOME
# =========================
if page == "🏠 Home":
    # KPIs
    c1, c2, c3, c4 = st.columns(4)

    snap = yf_last_and_prev_close(["^BVSP", "BRL=X", "BTC-USD"])
    btcbrl = binance_prices_btc_brl()

    ibov = snap[snap["ticker"] == "^BVSP"].iloc[0] if not snap.empty and not snap[snap["ticker"] == "^BVSP"].empty else None
    usd = snap[snap["ticker"] == "BRL=X"].iloc[0] if not snap.empty and not snap[snap["ticker"] == "BRL=X"].empty else None
    btcusd = snap[snap["ticker"] == "BTC-USD"].iloc[0] if not snap.empty and not snap[snap["ticker"] == "BTC-USD"].empty else None

    with c1:
        if ibov is not None:
            kpi_card("IBOV", fmt_br_int(ibov["last"]), f'{fmt_pct(ibov["var_pct"])} (dia)', color="#FFD700")
        else:
            kpi_card("IBOV", "—", "")

    with c2:
        if usd is not None:
            kpi_card("USD/BRL", fmt_br_money(usd["last"]), f'{fmt_pct(usd["var_pct"])} (dia)', color="#FFD700")
        else:
            kpi_card("USD/BRL", "—", "")

    with c3:
        if btcusd is not None:
            kpi_card("BTC (US$)", f'$ {fmt_br_int(btcusd["last"])}', f'{fmt_pct(btcusd["var_pct"])} (dia)', color="#FFD700")
        else:
            kpi_card("BTC (US$)", "—", "")

    with c4:
        if btcbrl:
            # evita quebrar: sempre money br e já cabe
            kpi_card("BTC (R$)", fmt_br_money(btcbrl["price"]), f'{fmt_pct(btcbrl["pct"])} (24h)', color="#FFD700")
        else:
            kpi_card("BTC (R$)", "—", "")

    st.write("")
    st.markdown("### ⚡ Acesso Rápido")
    st.markdown("<div class='bee-card'>", unsafe_allow_html=True)
    quick_ticker = st.text_input(
        "Ticker",
        placeholder="Ex: PETR4, WEGE3, AAPL...",
        label_visibility="collapsed",
    ).upper().strip()

    if quick_ticker:
        tk_norm = normalize_ticker(quick_ticker, "Ação", "BRL")
        if yf is not None:
            hist = yf_last_and_prev_close([tk_norm])
            if not hist.empty:
                last = hist.iloc[0]["last"]
                var = hist.iloc[0]["var_pct"]
                cor_txt = "#00C805" if var >= 0 else "#FF3B30"
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div style='font-size:22px; font-weight:900; color:#fff;'>{tk_norm.replace('.SA','')}</div>"
                    f"<div style='font-size:18px; font-weight:900; color:{cor_txt};'>{fmt_br_money(last)} • {fmt_pct(var)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Investidor10 (não StatusInvest)
                # Ações: https://investidor10.com.br/acoes/petr4/
                # FIIs: https://investidor10.com.br/fiis/hglg11/
                base = quick_ticker.lower()
                link_i10 = f"https://investidor10.com.br/acoes/{base}/"
                st.markdown(
                    f"""<div style="margin-top:10px;">
<a href="{link_i10}" target="_blank" style="text-decoration:none; font-weight:900; color:#fff; background:#5900b3; padding:10px 14px; border-radius:12px; display:inline-block;">
🔗 Abrir no Investidor10
</a></div>""",
                    unsafe_allow_html=True,
                )

                if px is not None:
                    chart_data = yf.Ticker(tk_norm).history(period="1mo")
                    if not chart_data.empty:
                        fig_mini = px.line(chart_data, y="Close")
                        fig_mini.update_layout(
                            xaxis_visible=False,
                            yaxis_visible=False,
                            margin=dict(l=0, r=0, t=10, b=0),
                            height=70,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            showlegend=False,
                        )
                        st.plotly_chart(fig_mini, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1, 1.2])
    with right:
        st.markdown("### 📰 Notícias")
        news = get_google_news_items("investimentos+brasil", limit=6)
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

# =========================
# ANALISAR
# =========================
elif page == "🔍 Analisar":
    st.markdown("## 🔍 Analisar")
    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input("Ativo", placeholder="WEGE3").upper().strip()
    with c_p:
        periodo = st.selectbox("Zoom", ["1mo", "6mo", "1y", "5y", "max"], index=2)

    if ticker:
        tk_real = normalize_ticker(ticker, "Ação", "BRL")
        info = yf_info_extended(tk_real)

        if info:
            st.markdown(f"### {info.get('longName', ticker)}")
            m1, m2, m3, m4 = st.columns(4)
            cur_price = info.get("currentPrice", 0.0)
            m1.metric("Preço", fmt_br_money(cur_price) if cur_price else "—")

            val_dy = info.get("dividendYield")
            if val_dy is not None:
                dy_str = f"{(float(val_dy) * 100):.2f}%".replace(".", ",")
            else:
                dy_str = "—"
            m2.metric("DY", dy_str)

            val_pe = info.get("trailingPE")
            m3.metric("P/L", (f"{float(val_pe):.2f}".replace(".", ",") if val_pe else "—"))
            m4.metric("Valor", format_market_cap(info.get("marketCap")))

            st.markdown("---")
            fig = get_stock_history_plot(tk_real, period=periodo)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Sem gráfico.")

            # Resumo (sem textão no topo; só em expander)
            with st.expander("Resumo"):
                st.write(info.get("summary", "—"))
        else:
            st.error("Ativo não encontrado.")

# =========================
# CARTEIRA (com clique -> popup analisador)
# =========================
elif page == "💼 Carteira":
    st.markdown("## 💼 Carteira (Cofre Local)")

    wallet_active = (not st.session_state["carteira_df"].empty) or st.session_state["wallet_mode"]

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("📂 Carregar minha_carteira.csv", type=["csv"], key="uploader_start")
            if uploaded_file:
                df_loaded = smart_load_csv(uploaded_file)
                if df_loaded is not None:
                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            st.success("📝 Começar do Zero")
            if st.button("🚀 Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                st.rerun()

    else:
        df = st.session_state["carteira_df"]

        with st.expander("➕ Adicionar Ativo", expanded=True):
            f1, f2, f3 = st.columns([1, 1, 1])
            with f1:
                tipo = st.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa"])
                ativo = st.text_input("Ticker").upper().strip()
            with f2:
                qtd = st.number_input("Qtd", min_value=0.0, step=0.01)
                preco = st.number_input("Preço Pago", min_value=0.0, step=0.01)
            with f3:
                moeda = st.selectbox("Moeda", ["BRL", "USD"])
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<div class='yellowbtn'>", unsafe_allow_html=True)
                if st.button("Adicionar"):
                    if ativo and qtd > 0:
                        if ativo in df["Ativo"].values:
                            idx = df[df["Ativo"] == ativo].index[0]
                            old_q = float(df.at[idx, "Qtd"])
                            old_pm = float(df.at[idx, "Preco_Medio"])
                            new_q = old_q + qtd
                            new_pm = ((old_q * old_pm) + (qtd * preco)) / new_q if new_q > 0 else 0
                            df.at[idx, "Qtd"] = new_q
                            df.at[idx, "Preco_Medio"] = new_pm
                        else:
                            df = pd.concat(
                                [
                                    df,
                                    pd.DataFrame(
                                        [
                                            {
                                                "Tipo": tipo,
                                                "Ativo": ativo,
                                                "Nome": ativo,
                                                "Qtd": qtd,
                                                "Preco_Medio": preco,
                                                "Moeda": moeda,
                                                "Obs": "",
                                            }
                                        ]
                                    ),
                                ],
                                ignore_index=True,
                            )
                        st.session_state["carteira_df"] = df
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🗑️ Remover Ativo", expanded=False):
            if not df.empty:
                ativos_disponiveis = df["Ativo"].unique().tolist()
                ativo_rm = st.selectbox("Selecione para remover", ativos_disponiveis)
                if st.button(f"Excluir {ativo_rm}"):
                    df = df[df["Ativo"] != ativo_rm]
                    st.session_state["carteira_df"] = df
                    st.rerun()

        if not df.empty:
            df_calc, kpi = atualizar_precos_carteira_memory(df)

            k1, k2, k3 = st.columns(3)
            with k1:
                kpi_card("Total", fmt_br_money(kpi["total_brl"]), "Patrimônio", color="#FFD700")
            with k2:
                cor = "#00C805" if kpi["pnl_brl"] >= 0 else "#FF3B30"
                kpi_card("Resultado", fmt_br_money(kpi["pnl_brl"]), fmt_pct(kpi["pnl_pct"]), color=cor)
            with k3:
                kpi_card("Ativos", str(len(df_calc)), "Diversificação", color="#FFD700")

            st.write("")

            # tabela clicável (se Streamlit suportar seleção)
            show_cols = ["Tipo", "Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "Total_BRL", "PnL_Pct", "Moeda"]

            # arruma exibicao pt-br
            disp = df_calc[show_cols].copy()
            disp["Qtd"] = disp["Qtd"].map(lambda x: f"{x:.4f}".replace(".", ",") if isinstance(x, (int, float)) else x)
            disp["Preco_Medio"] = disp["Preco_Medio"].map(lambda x: fmt_br_money(x))
            disp["Preco_Atual_BRL"] = disp["Preco_Atual_BRL"].map(lambda x: fmt_br_money(x))
            disp["Total_BRL"] = disp["Total_BRL"].map(lambda x: fmt_br_money(x))
            disp["PnL_Pct"] = disp["PnL_Pct"].map(lambda x: fmt_pct(x))

            st.markdown("<div class='bee-card'>", unsafe_allow_html=True)
            st.markdown("<div class='card-title'>Clique em um ativo para abrir no Analisador</div>", unsafe_allow_html=True)

            # Tenta usar dataframe selection (novas versões)
            selected_ativo = None
            try:
                ev = st.dataframe(
                    disp,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=360,
                )
                # ev.selection.rows -> indices selecionados
                if ev and hasattr(ev, "selection") and ev.selection and ev.selection.rows:
                    idx = ev.selection.rows[0]
                    selected_ativo = str(df_calc.iloc[idx]["Ativo"])
            except:
                # fallback: selectbox
                selected_ativo = st.selectbox("Ativo", df_calc["Ativo"].astype(str).tolist())

            st.markdown("</div>", unsafe_allow_html=True)

            if selected_ativo:
                st.session_state["carteira_selected"] = selected_ativo

                # Popup/Modal do analisador
                def render_analyzer_popup(symbol: str):
                    sym = normalize_ticker(symbol, "Ação", "BRL")
                    info = yf_info_extended(sym)
                    st.markdown(f"### {symbol}")
                    if info:
                        cols = st.columns(4)
                        cols[0].metric("Preço", fmt_br_money(info.get("currentPrice", 0.0)))
                        dy = info.get("dividendYield")
                        cols[1].metric("DY", (f"{float(dy)*100:.2f}%".replace(".", ",") if dy else "—"))
                        pe = info.get("trailingPE")
                        cols[2].metric("P/L", (f"{float(pe):.2f}".replace(".", ",") if pe else "—"))
                        cols[3].metric("Market Cap", format_market_cap(info.get("marketCap")))
                        fig = get_stock_history_plot(sym, period="1y")
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        with st.expander("Resumo"):
                            st.write(info.get("summary", "—"))
                    else:
                        st.info("Sem dados para este ativo.")

                    # link investidor10
                    base = symbol.lower()
                    link_i10 = f"https://investidor10.com.br/acoes/{base}/"
                    st.link_button("Abrir no Investidor10", link_i10)

                try:
                    @st.dialog("Analisador")
                    def analyzer_dialog():
                        render_analyzer_popup(st.session_state["carteira_selected"])

                    if st.button("Abrir Analisador", use_container_width=False):
                        analyzer_dialog()
                except:
                    with st.expander("Analisador (abrir/fechar)", expanded=False):
                        render_analyzer_popup(st.session_state["carteira_selected"])

        st.write("---")
        st.download_button("⬇️ Baixar CSV", df.to_csv(index=False).encode("utf-8"), "minha_carteira.csv", "text/csv", type="primary")
        if st.button("Sair"):
            st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
            st.session_state["wallet_mode"] = False
            st.rerun()

# =========================
# CONTROLE DE GASTOS (restaurado)
# =========================
elif page == "💸 Controle":
    st.markdown("## 💸 Controle de Gastos")

    gastos_active = (not st.session_state["gastos_df"].empty) or st.session_state["gastos_mode"]

    if not gastos_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_gastos = st.file_uploader("📂 Carregar meus_gastos.csv", type=["csv"], key="uploader_gastos")
            if uploaded_gastos:
                df_g = smart_load_csv(uploaded_gastos)
                if df_g is not None:
                    st.session_state["gastos_df"] = df_g
                    st.session_state["gastos_mode"] = True
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            if st.button("📝 Criar Planilha de Gastos", use_container_width=True):
                st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
                st.session_state["gastos_mode"] = True
                st.rerun()
    else:
        df_g = st.session_state["gastos_df"].copy()
        df_g["Data"] = pd.to_datetime(df_g["Data"], errors="coerce")
        df_g.dropna(subset=["Data"], inplace=True)

        today = datetime.now()
        meses_disp = sorted(list(set(df_g["Data"].dt.strftime("%Y-%m"))))
        if not meses_disp:
            meses_disp = [today.strftime("%Y-%m")]

        mes_atual_str = today.strftime("%Y-%m")
        idx_mes = len(meses_disp) - 1
        if mes_atual_str in meses_disp:
            idx_mes = meses_disp.index(mes_atual_str)

        col_sel, _ = st.columns([1, 3])
        with col_sel:
            mes_selecionado = st.selectbox("Mês", meses_disp, index=idx_mes)

        mask_mes = df_g["Data"].dt.strftime("%Y-%m") == mes_selecionado
        df_filtered = df_g[mask_mes].copy()

        # valores
        df_filtered["Valor"] = pd.to_numeric(df_filtered["Valor"], errors="coerce").fillna(0)
        total_ent = df_filtered[df_filtered["Tipo"] == "Entrada"]["Valor"].sum()
        total_sai = df_filtered[df_filtered["Tipo"] == "Saída"]["Valor"].sum()
        saldo = total_ent - total_sai

        k1, k2, k3 = st.columns(3)
        k1.metric("Receitas", fmt_br_money(total_ent))
        k2.metric("Despesas", fmt_br_money(total_sai))
        k3.metric("Saldo", fmt_br_money(saldo))

        st.write("---")

        with st.expander("➕ Nova Transação", expanded=True):
            with st.form("form_gastos", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                d_data = c1.date_input("Data", value=today.date())
                default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Outros"]
                existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
                all_cats = sorted(list(set(default_cats + existing_cats)))
                all_cats.append("➕ Nova (digitar)")

                d_cat_select = c2.selectbox("Categoria", all_cats)
                d_cat_input = c2.text_input("Nova categoria", placeholder="Ex: Pet")
                d_desc = c3.text_input("Descrição", placeholder="Ex: Uber / Mercado")
                d_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"])

                c5, c6 = st.columns(2)
                d_val = c5.number_input("Valor", min_value=0.0, step=10.0)
                d_pag = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])

                if st.form_submit_button("Salvar"):
                    final_cat = d_cat_input if d_cat_select == "➕ Nova (digitar)" and d_cat_input else d_cat_select
                    if final_cat == "➕ Nova (digitar)":
                        final_cat = "Outros"

                    new_row = {
                        "Data": d_data,
                        "Categoria": final_cat,
                        "Descricao": d_desc,
                        "Tipo": d_tipo,
                        "Valor": d_val,
                        "Pagamento": d_pag,
                    }
                    df_g = pd.concat([df_g, pd.DataFrame([new_row])], ignore_index=True)
                    st.session_state["gastos_df"] = df_g
                    st.rerun()

        # Charts + extrato
        c_chart, c_table = st.columns([1, 2])
        with c_chart:
            if px is not None and not df_filtered.empty and total_sai > 0:
                df_pie = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
                fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.6)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=280, paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados no mês.")

        with c_table:
            # mostra tabela
            df_show = df_g.copy()
            df_show["Data"] = pd.to_datetime(df_show["Data"], errors="coerce")
            df_show = df_show.sort_values("Data", ascending=False)

            st.dataframe(df_show, use_container_width=True, height=340)

        st.write("---")
        st.download_button("⬇️ Baixar meus_gastos.csv", df_g.to_csv(index=False).encode("utf-8"), "meus_gastos.csv", "text/csv", type="primary")
        if st.button("Sair"):
            st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
            st.session_state["gastos_mode"] = False
            st.rerun()

# =========================
# NEWS (feed)
# =========================
elif page == "📰 News":
    st.markdown("## 📰 Notícias")
    items = get_google_news_items("investimentos+brasil", limit=10)
    for n in items:
        ago = human_time_ago(n["published_dt"])
        st.markdown(
            f"""
<a href="{n['link']}" target="_blank" class="news-card-link">
  <div class="news-card-box">
    <div class="nc-title">{n['title']}</div>
    <div class="nc-meta"><span class="nc-badge">{n['source']}</span><span>• {ago}</span></div>
  </div>
</a>
""",
            unsafe_allow_html=True,
        )

# =========================
# BEE TV (YouTube)
# =========================
elif page == "🍿 Bee TV":
    st.markdown("## 🍿 Bee TV")

    api_key = get_youtube_key()

    # UI limpa: só campo de busca
    query = st.text_input("Pesquisar", value="investimentos", label_visibility="visible")

    # botão discreto no topo já existe (↻). Aqui não precisa outro.

    if not api_key:
        st.warning("Bee TV precisa de YOUTUBE_API_KEY no Streamlit Cloud (Secrets) ou no seu PC (env).")
    else:
        # busca e mostra 6 vídeos
        vids = build_bee_tv_results(api_key, query.strip(), limit=6)

        if not vids:
            st.info("Sem vídeos agora. Tenta outro termo.")
        else:
            cols = st.columns(3)
            for i, v in enumerate(vids):
                with cols[i % 3]:
                    st.video(f"https://www.youtube.com/watch?v={v['videoId']}")
                    # sem textão, só título pequeno
                    st.caption(v["title"])

# =========================
# APRENDA (restaurado livros + vídeos)
# =========================
elif page == "🎓 Aprenda":
    st.markdown("## 🎓 Educação")
    tab_videos, tab_lib = st.tabs(["📺 Vídeos", "📚 Biblioteca"])

    with tab_videos:
        videos_aprenda = [
            ("Começando do Zero (Raul Sena)", "https://www.youtube.com/watch?v=bx-sTOSteRA"),
            ("Investir com Pouco (Bruno Perini)", "https://www.youtube.com/watch?v=J25ZMPx7J1s"),
            ("A Virada Financeira (Primo Pobre)", "https://www.youtube.com/watch?v=geE3TUzHFTI"),
            ("Minha História (Bruno Perini)", "https://www.youtube.com/watch?v=HYe9tSqSDA0"),
        ]
        for i in range(0, len(videos_aprenda), 2):
            c1, c2 = st.columns(2)
            with c1:
                st.video(videos_aprenda[i][1])
                st.caption(videos_aprenda[i][0])
            with c2:
                if i + 1 < len(videos_aprenda):
                    st.video(videos_aprenda[i + 1][1])
                    st.caption(videos_aprenda[i + 1][0])

    with tab_lib:
        books = [
            {"title": "Os Segredos da Mente Milionária", "author": "T. Harv Eker", "link": "https://amzn.to/3ueEorO"},
            {"title": "Pai Rico, Pai Pobre", "author": "Robert T. Kiyosaki", "link": "https://amzn.to/3SDPqAb"},
            {"title": "O Homem Mais Rico da Babilônia", "author": "George S. Clason", "link": "https://amzn.to/48b6i9P"},
            {"title": "Faça Fortuna com Ações", "author": "Décio Bazin", "link": "https://amzn.to/4cfPs8q"},
            {"title": "O Investidor Inteligente", "author": "Benjamin Graham", "link": "https://amzn.to/3Us6VVL"},
            {"title": "Ações Comuns Lucros Extraordinários", "author": "Philip A. Fisher", "link": "https://amzn.to/3Une9tZ"},
            {"title": "O Rei dos Dividendos", "author": "Luiz Barsi Filho", "author2": "Luiz Barsi Filho", "link": "https://amzn.to/4meVoUQ"},
            {"title": "A Lógica do Cisne Negro", "author": "Nassim Taleb", "link": "https://amzn.to/42nk7gf"},
            {"title": "Princípios", "author": "Ray Dalio", "link": "https://amzn.to/3HL1fOI"},
        ]

        for b in books:
            with st.container():
                c_icon, c_info, c_btn = st.columns([0.4, 3, 1])
                with c_icon:
                    st.markdown("📘")
                with c_info:
                    st.markdown(f"**{b['title']}**")
                    st.caption(f"Autor: {b.get('author','—')}")
                with c_btn:
                    st.link_button("Comprar", b["link"])
                st.markdown("---")

else:
    st.write("")

# footer versão no fim da página também (discreto)
st.markdown(
    f"""
<div class="footer">
  <div>Bee Finanças</div>
  <div>{APP_VERSION}</div>
</div>
""",
    unsafe_allow_html=True,
)
