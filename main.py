# Bee Finanças — Streamlit App (v8.6 BRAZILIAN EDITION)
# ---------------------------------------------------------------
# ✅ ANALISAR: Preço agora é REAL (tempo real), não texto fixo.
# ✅ IDIOMA: Resumo da empresa traduzido automaticamente p/ PT-BR.
# ✅ DEPENDÊNCIA: Requer 'pip install deep-translator' para tradução.
# ---------------------------------------------------------------

import os
import re
import math
import random
import warnings
from datetime import datetime, timezone, timedelta
import textwrap

import streamlit as st
import pandas as pd
import feedparser
import requests

# --------------------------------------------------------------------------------
# IMPORTAÇÃO DE BIBLIOTECAS
# --------------------------------------------------------------------------------
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except Exception:
    go = None
    px = None

try:
    from dateutil import parser as dtparser
except Exception:
    dtparser = None

try:
    from PIL import Image
    import io
except Exception:
    Image = None
    io = None

# Tenta importar tradutor (se não tiver, usa fallback)
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

# =====================================================================================
# 0) CONFIG / PATHS
# =====================================================================================
st.set_page_config(page_title="Bee Finanças", page_icon="🐝", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")

DATA_DIR = os.path.join(os.path.expanduser("~"), ".bee_financas")
os.makedirs(DATA_DIR, exist_ok=True)
CARTEIRA_FILE = os.path.join(DATA_DIR, "minha_carteira.csv")

# =====================================================================================
# 1) CSS / UI (DESIGN PREMIUM)
# =====================================================================================
st.markdown(
    """
<style>
/* --- FUNDO E GERAL --- */
.stApp{
  background:
    radial-gradient(circle at 15% 15%, rgba(255, 215, 0, 0.04), transparent 35%),
    radial-gradient(circle at 85% 85%, rgba(89, 0, 179, 0.08), transparent 35%),
    #0B0F14;
}

h1, h2, h3, h4 {
  color: #FFD700 !important;
  font-family: 'Inter', sans-serif;
  font-weight: 800;
  letter-spacing: -0.03em;
}

/* --- SIDEBAR --- */
section[data-testid="stSidebar"]{
  background: #090C10;
  border-right: 1px solid rgba(255,255,255,0.05);
}

div[data-testid="stSidebarUserContent"] {
    padding-top: 10px; 
    display: flex;
    flex-direction: column;
    height: 100%;
}
div[data-testid="stSidebarUserContent"] .stButton {
    margin-bottom: 0px !important;
}
div[data-testid="stVerticalBlock"] {
    gap: 0.3rem !important;
}

/* Ajuste da Logo na Sidebar */
section[data-testid="stSidebar"] img {
    display: block;
    margin-left: auto;
    margin-right: auto;
    margin-bottom: 15px;
    object-fit: contain;
    max-width: 100%;
}

/* --- MENU BUTTONS --- */
.navbtn button {
  width: 100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%) !important;
  color: #909090 !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  border-radius: 8px !important;
  padding: 0.5rem 1rem !important;
  margin: 0px !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  text-align: left !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
  height: 42px !important;
  display: flex !important;
  align-items: center !important;
}
.navbtn button:hover, .navbtn button:focus {
  background: linear-gradient(90deg, rgba(255,215,0,0.08) 0%, rgba(255,215,0,0.02) 100%) !important;
  color: #fff !important;
  border-color: rgba(255,215,0,0.3) !important;
  border-left: 3px solid #FFD700 !important;
  padding-left: 0.9rem !important;
  transform: translateX(2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.navbtn button p { font-size: 14px !important; }

.menu-header {
    font-size: 10px;
    text-transform: uppercase;
    color: #444;
    font-weight: 800;
    letter-spacing: 1px;
    margin-top: 15px;
    margin-bottom: 5px;
    padding-left: 5px;
}

/* --- SIDEBAR TICKER --- */
.ticker-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    padding-bottom: 6px;
}
.t-name { font-size: 13px; font-weight: 700; color: #aaa; }
.t-data { text-align: right; line-height: 1.2; }
.t-price { font-size: 13px; font-weight: 600; color: #fff; display: block; }
.t-pct { font-size: 11px; font-weight: 700; }

/* --- CARDS & WIDGETS --- */
.bee-card{
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 18px;
  backdrop-filter: blur(4px);
}
.card-title{ color: #FFD700; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
.kpi{ color:#fff; font-weight: 800; font-size: 26px; }
.sub{ color: #666; font-size: 12px; }

/* Correção de tamanho de fonte nas Métricas */
[data-testid="stMetricValue"] {
    font-size: 24px !important;
}

/* --- TOP 5 LIST STYLE --- */
.top5-link { text-decoration: none; display: block; }
.top5-row {
    display: flex; 
    justify-content: space-between; 
    align-items: center;
    background: rgba(255,255,255,0.025); 
    border-bottom: 1px solid rgba(255,255,255,0.04);
    border-radius: 8px; 
    padding: 10px 12px; 
    margin-bottom: 4px;
    transition: 0.2s;
}
.top5-row:hover { background: rgba(255,255,255,0.08); transform: translateX(2px); border-left: 2px solid #FFD700; }
.top5-badge { font-weight: 800; color: #000; background: #4CAF50; padding: 2px 8px; border-radius: 4px; font-size: 12px; }

/* --- VIDEO CARD --- */
.video-card {
  display: flex;
  flex-direction: column;
  background: #161b22;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
  text-decoration: none;
  height: 100%;
  transition: transform 0.2s;
}
.video-card:hover { transform: translateY(-4px); border-color: #FFD700; }
.video-thumb { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
.video-info { padding: 12px; display: flex; flex-direction: column; justify-content: space-between; flex-grow: 1; }
.video-ch { font-size: 10px; color: #FFD700; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 4px; }
.video-tt { font-size: 13px; color: #fff; font-weight: 600; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.video-dt { font-size: 11px; color: #666; margin-top: 8px; }

/* --- NEWS --- */
.news-item { padding: 10px; border-left: 2px solid #333; margin-bottom: 8px; background: rgba(255,255,255,0.01); text-decoration:none; display:block;}
.news-item:hover { border-left-color: #FFD700; background: rgba(255,255,255,0.04); }
.news-title { color: #ddd; font-weight:600; font-size:13px; }
.news-meta { color: #555; font-size:11px; margin-top:3px; }

/* --- INPUTS --- */
.stTextInput input, .stNumberInput input, .stSelectbox div { background: #12171E !important; color: #fff !important; border: 1px solid #333 !important; border-radius: 10px !important; }
.yellowbtn button{ background: #FFD700 !important; color:#000 !important; border: none !important; font-weight: 800 !important; border-radius: 10px !important; padding: 0.6rem 1.2rem !important; }
.yellowbtn button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,215,0,0.3); }

/* --- TABS ALIGNMENT --- */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { height: 40px; white-space: nowrap; border-radius: 4px; padding: 0 16px; color: #888; }
.stTabs [aria-selected="true"] { color: #FFD700; background-color: rgba(255,215,0,0.1); }

</style>
""",
    unsafe_allow_html=True,
)


# =====================================================================================
# 2) HELPERS
# =====================================================================================
def human_time_ago(dt: datetime) -> str:
    if not dt: return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    sec = int((now - dt).total_seconds())
    if sec < 60: return "agora"
    m = sec // 60
    if m < 60: return f"{m}m"
    h = m // 60
    if h < 24: return f"{h}h"
    d = h // 24
    return f"{d}d"


def normalize_ticker(ativo: str, tipo: str, moeda: str) -> str:
    a = (ativo or "").strip().upper()
    if not a: return ""
    if a.endswith(".SA") or a.endswith("-USD") or a.endswith("=X") or a.startswith("^"): return a
    if tipo == "Cripto": return a if "-" in a else f"{a}-USD"
    if a in ("BRL=X", "USDBRL", "USD", "DOLAR"): return "BRL=X"
    has_digit = any(ch.isdigit() for ch in a)
    if moeda == "BRL" and has_digit and not a.endswith(".SA"): return f"{a}.SA"
    return a


def format_market_cap(x: float) -> str:
    if not x: return "—"
    if x >= 1e12: return f"{x / 1e12:.2f} T"
    if x >= 1e9: return f"{x / 1e9:.2f} B"
    if x >= 1e6: return f"{x / 1e6:.2f} M"
    return f"{x:,.0f}"


@st.cache_data(ttl=600)
def get_usdbrl() -> float:
    if yf is None: return 5.80
    try:
        h = yf.Ticker("BRL=X").history(period="1d")
        return float(h["Close"].iloc[-1])
    except:
        return 5.80


@st.cache_data(ttl=600)
def yf_last_and_prev_close(tickers: list[str]) -> pd.DataFrame:
    if yf is None or not tickers: return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])
    try:
        data = yf.download(tickers, period="7d", progress=False, threads=True, group_by="ticker")
    except:
        return pd.DataFrame()

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
                    var = ((last - prev) / prev) * 100.0 if prev != 0 else 0.0
                    out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var})
        except:
            pass
    return pd.DataFrame(out)


# --- FUNÇÃO BEE TV ---
CHANNEL_IDS = {
    "Bruno Perini": "UCw069r5R90_t7A5jQYg23yA",
    "Geração de Dividendos": "UCzLAzI6Q-0WX2IbKfLmtZUw",
    "Primo Pobre": "UCfdmc3wsZYbfiL-iT4D0XIg",
    "Gêmeos Investem": "UC-hA65Fjv5X8h-J92zc_L8Q",
    "Fernando Ulrich": "UCLJkh3QjHsLtK0LZFd28oGg",
    "Eitonilda": "UC08-XJ_5Ymd53kKPy3fk9GQ",
    "Investidor Sardinha": "UCM3vJxmuJJkk1r0yzFI9eZg"
}


@st.cache_data(ttl=900)
def get_bee_tv_feed_randomized():
    pool = []
    for nome, ch_id in CHANNEL_IDS.items():
        try:
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch_id}"
            feed = feedparser.parse(url)
            for entry in getattr(feed, "entries", [])[:5]:
                title_lower = entry.title.lower()
                is_short = "#short" in title_lower

                thumb = None
                if 'media_thumbnail' in entry:
                    thumb = entry.media_thumbnail[0]['url']
                elif 'media_content' in entry:
                    thumb = entry.media_content[0]['url']
                else:
                    vid_id = entry.yt_videoid if 'yt_videoid' in entry else entry.link.split("v=")[-1]
                    thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"

                dt_obj = None
                if dtparser and 'published' in entry:
                    dt_obj = dtparser.parse(entry.published)
                    if dt_obj.tzinfo is None: dt_obj = dt_obj.replace(tzinfo=timezone.utc)

                pool.append({
                    "canal": nome, "titulo": entry.title, "link": entry.link,
                    "thumb": thumb, "dt": dt_obj, "timestamp": dt_obj.timestamp() if dt_obj else 0, "is_short": is_short
                })
        except:
            continue

    pool.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_pool = pool[:50]

    videos_longos = [v for v in recent_pool if not v['is_short']]
    videos_shorts = [v for v in recent_pool if v['is_short']]

    random.shuffle(videos_longos)
    random.shuffle(videos_shorts)

    final_selection = []
    final_selection.extend(videos_longos[:4])
    final_selection.extend(videos_shorts[:2])

    if len(final_selection) < 6:
        rest = videos_longos[4:] + videos_shorts[2:]
        random.shuffle(rest)
        final_selection.extend(rest[:(6 - len(final_selection))])

    random.shuffle(final_selection)
    return final_selection[:6]


# --- RENDER TOP 5 CLICÁVEL ---
def render_top5_card(df, prefixo="R$", tipo="acao"):
    if df.empty:
        st.info("Sem dados.")
        return

    top5 = df.nlargest(5, "var_pct")
    if top5.empty or top5['var_pct'].max() <= 0:
        st.caption("Mercado em baixa (sem altas > 0%).")
        return

    for _, row in top5.iterrows():
        full_ticker = row['ticker']
        nome = full_ticker.replace(".SA", "").replace("-USD", "")
        preco = row['last']
        var = row['var_pct']

        if tipo == "acao":
            link = f"https://analitica.auvp.com.br/acoes/{nome.lower()}"
        else:
            link = f"https://investidor10.com.br/criptomoedas/{nome.lower()}/"

        if var > 0:
            html = textwrap.dedent(f"""
            <a href="{link}" target="_blank" class="top5-link">
                <div class="top5-row">
                    <div style="font-weight:700; color:#eee; font-size:14px;">{nome}</div>
                    <div style="text-align:right;">
                        <span class="top5-badge">+{var:.2f}%</span>
                        <div style="font-size:10px; color:#777; margin-top:2px;">{prefixo} {preco:,.2f}</div>
                    </div>
                </div>
            </a>
            """)
            st.markdown(html, unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def get_stock_history_plot(ticker: str, period="1y"):
    if yf is None or go is None: return None
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty: return None
        fig = go.Figure(data=[
            go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                           name=ticker)])
        fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                          plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=300)
        return fig
    except:
        return None


@st.cache_data(ttl=1200)
def yf_info_extended(ticker: str) -> dict:
    if yf is None or not ticker: return {}
    try:
        tk = yf.Ticker(ticker)

        # 1. Pega preço em tempo real (Fast Info)
        current_price = 0.0
        try:
            if hasattr(tk, 'fast_info'):
                current_price = tk.fast_info.last_price
            else:
                hist = tk.history(period="1d")
                if not hist.empty: current_price = hist['Close'].iloc[-1]
        except:
            pass

        inf = tk.info or {}

        def safe_get(keys, default="—"):
            for k in keys:
                if k in inf and inf[k] is not None: return inf[k]
            return default

        # 2. Tradução do Resumo
        summary_text = safe_get(["longBusinessSummary"], "")
        if summary_text and GoogleTranslator:
            try:
                summary_text = GoogleTranslator(source='auto', target='pt').translate(summary_text)
            except:
                pass  # Falha silenciosa se não tiver net ou api
        elif not summary_text:
            summary_text = "Resumo indisponível."

        return {
            "currentPrice": current_price,
            "longName": safe_get(["longName", "shortName"], ticker),
            "sector": safe_get(["sector"]),
            "industry": safe_get(["industry"]),
            "summary": summary_text,
            "trailingPE": safe_get(["trailingPE", "forwardPE"], None),
            "dividendYield": safe_get(["dividendYield", "trailingAnnualDividendYield"], None),
            "marketCap": safe_get(["marketCap"], None)
        }
    except:
        return {}


def try_remove_white_bg(image_path: str):
    if Image is None or io is None or not os.path.exists(image_path): return None
    try:
        im = Image.open(image_path).convert("RGBA")
        px = im.getdata()
        new_px = [(r, g, b, 0) if r > 230 and g > 230 and b > 230 else (r, g, b, a) for r, g, b, a in px]
        im.putdata(new_px)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    except:
        return None


# =====================================================================================
# 3) DADOS & LISTAS
# =====================================================================================
TICKERS_BR = ["VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", "PRIO3.SA", "RENT3.SA",
              "SUZB3.SA", "GGBR4.SA", "B3SA3.SA", "ABEV3.SA", "VIVT3.SA", "RADL3.SA", "LREN3.SA", "MGLU3.SA"]
TICKERS_CRIPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD"]


# =====================================================================================
# 4) YOUTUBE & NEWS
# =====================================================================================
@st.cache_data(ttl=900)
def get_google_news_items(query: str, limit: int = 6) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        feed = feedparser.parse(url)
        items = []
        for e in getattr(feed, "entries", [])[:limit]:
            try:
                p_dt = dtparser.parse(e.published) if dtparser else None
            except:
                p_dt = None
            title = getattr(e, "title", "Notícia").rsplit(" - ", 1)[0]
            source = getattr(e, "source", {}).get("title") or (
                e.title.rsplit(" - ", 1)[-1] if " - " in e.title else "News")
            items.append({"title": title, "link": e.link, "source": source, "published_dt": p_dt})
        return items
    except:
        return []


# =====================================================================================
# 5) CARTEIRA
# =====================================================================================
CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]


def carregar_carteira() -> pd.DataFrame:
    if not os.path.exists(CARTEIRA_FILE): return pd.DataFrame(columns=CARTEIRA_COLS)
    try:
        df = pd.read_csv(CARTEIRA_FILE)
        for c in CARTEIRA_COLS:
            if c not in df.columns: df[c] = ""
        return df
    except:
        return pd.DataFrame(columns=CARTEIRA_COLS)


def salvar_carteira(df: pd.DataFrame):
    df[CARTEIRA_COLS].to_csv(CARTEIRA_FILE, index=False)


def atualizar_precos_carteira(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    if df.empty: return df, {"total_brl": 0, "pnl_brl": 0, "pnl_pct": 0, "usdbrl": 5.80}

    usdbrl = get_usdbrl()
    df["Ticker_YF"] = df.apply(lambda r: normalize_ticker(str(r["Ativo"]), str(r["Tipo"]), str(r["Moeda"]).upper()),
                               axis=1)

    df["Preco_Atual"] = 0.0
    is_rf = df["Tipo"].str.contains("Renda Fixa|RF", case=False, na=False)
    df.loc[is_rf, "Preco_Atual"] = df.loc[is_rf, "Preco_Medio"]

    tickers = df.loc[~is_rf, "Ticker_YF"].unique().tolist()
    px_map = {}
    if tickers:
        px_df = yf_last_and_prev_close(tickers)
        for _, r in px_df.iterrows(): px_map[r["ticker"]] = float(r["last"])

    for i, row in df.iterrows():
        if is_rf[i]: continue
        tk = row["Ticker_YF"]
        curr = float(px_map.get(tk, 0.0))
        df.at[i, "Preco_Atual"] = curr

    df["Qtd"] = pd.to_numeric(df["Qtd"], errors="coerce").fillna(0)
    df["Preco_Medio"] = pd.to_numeric(df["Preco_Medio"], errors="coerce").fillna(0)

    df["Preco_Atual_BRL"] = df["Preco_Atual"]
    mask_usd = (df["Moeda"] == "USD") | (df["Ticker_YF"].str.endswith("-USD"))
    df.loc[mask_usd, "Preco_Atual_BRL"] *= usdbrl
    df.loc[mask_usd, "Preco_Medio_BRL"] = df.loc[mask_usd, "Preco_Medio"] * usdbrl
    df.loc[~mask_usd, "Preco_Medio_BRL"] = df.loc[~mask_usd, "Preco_Medio"]

    df["Total_BRL"] = df["Qtd"] * df["Preco_Atual_BRL"]
    df["Custo_BRL"] = df["Qtd"] * df["Preco_Medio_BRL"]
    df["PnL_BRL"] = df["Total_BRL"] - df["Custo_BRL"]
    df["PnL_BRL"] = df["Total_BRL"] - df["Custo_BRL"]
    df["PnL_Pct"] = df.apply(lambda x: (x["PnL_BRL"] / x["Custo_BRL"] * 100) if x["Custo_BRL"] > 0 else 0, axis=1)

    kpi = {
        "total_brl": df["Total_BRL"].sum(),
        "pnl_brl": df["PnL_BRL"].sum(),
        "pnl_pct": 0.0,
        "usdbrl": usdbrl
    }
    custo_total = df["Custo_BRL"].sum()
    if custo_total > 0: kpi["pnl_pct"] = (kpi["pnl_brl"] / custo_total) * 100

    return df, kpi


# =====================================================================================
# 6) UI COMPONENTS
# =====================================================================================
def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def kpi_card(title, value, sub, color=None):
    st.markdown(f"""
        <div class="bee-card" style="{f'border-top: 3px solid {color}' if color else ''}">
          <div class="card-title">{title}</div>
          <div class="kpi">{value}</div>
          <div class="sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)


# =====================================================================================
# 7) MAIN APP STRUCTURE
# =====================================================================================
if "page" not in st.session_state: st.session_state["page"] = "🏠 Home"
page = st.session_state["page"]

# --- SIDEBAR OTIMIZADA ---
with st.sidebar:
    # LOGO (Tamanho aumentado para 280)
    logo_data = try_remove_white_bg(LOGO_PATH)
    if logo_data:
        st.image(logo_data, width=280)
    elif os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=280)
    else:
        st.markdown("## 🐝 Bee Finanças")

    st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
    nav_btn("🏠 Home", "🏠 Home")
    nav_btn("📰 Notícias", "📰 News")

    st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
    nav_btn("🔍 Analisar", "🔍 Analisar")
    nav_btn("💼 Carteira", "💼 Carteira")
    nav_btn("🧮 Calculadoras", "🧮 Calculadoras")

    st.markdown("<p class='menu-header'>Learn</p>", unsafe_allow_html=True)
    nav_btn("🍿 Bee TV", "🍿 Bee TV")
    nav_btn("📱 Tutorial", "📱 Tutorial")

    st.divider()

    # --- MINI TICKER LATERAL (PREÇO + %) ---
    try:
        watch_list = ["^BVSP", "BRL=X", "BTC-USD", "IFIX.SA", "^GSPC", "^IXIC"]
        mini_ticks = yf_last_and_prev_close(watch_list)

        if not mini_ticks.empty:
            st.markdown(
                "<div style='font-size:12px; color:#666; font-weight:700; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>",
                unsafe_allow_html=True)

            name_map = {
                "^BVSP": "IBOV", "BRL=X": "USD", "BTC-USD": "BTC",
                "IFIX.SA": "IFIX", "^GSPC": "S&P", "^IXIC": "NASD"
            }

            for _, row in mini_ticks.iterrows():
                cor = "#4CAF50" if row['var_pct'] >= 0 else "#FF5252"
                nome = name_map.get(row['ticker'], row['ticker'])
                val = row['last']

                # Formatação condicional
                if row['ticker'] == 'BRL=X':
                    fmt_val = f"R$ {val:.2f}"
                elif 'USD' in row['ticker']:  # Crypto
                    fmt_val = f"US$ {val:,.0f}"
                else:  # Pontos
                    fmt_val = f"{val:,.0f}"

                st.markdown(
                    f"<div class='ticker-item'>"
                    f"<span class='t-name'>{nome}</span>"
                    f"<div class='t-data'>"
                    f"<span class='t-price'>{fmt_val}</span>"
                    f"<span class='t-pct' style='color:{cor};'>{row['var_pct']:+.2f}%</span>"
                    f"</div>"
                    f"</div>", unsafe_allow_html=True
                )
    except:
        pass

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.markdown("")  # Spacer
with c2:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex; justify-content:flex-end;'>", unsafe_allow_html=True)
    st.markdown("<div class='smallbtn'>", unsafe_allow_html=True)
    if st.button("↻ Atualizar"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin-top:0'>", unsafe_allow_html=True)

# =====================================================================================
# PAGE: HOME
# =====================================================================================
if page == "🏠 Home":
    # KPIs
    snap = yf_last_and_prev_close(["^BVSP", "BRL=X", "BTC-USD", "ETH-USD"])
    if not snap.empty:
        kpis = {
            "IBOV": snap[snap["ticker"] == "^BVSP"].iloc[0] if not snap[snap["ticker"] == "^BVSP"].empty else None,
            "DÓLAR": snap[snap["ticker"] == "BRL=X"].iloc[0] if not snap[snap["ticker"] == "BRL=X"].empty else None,
            "BITCOIN": snap[snap["ticker"] == "BTC-USD"].iloc[0] if not snap[
                snap["ticker"] == "BTC-USD"].empty else None,
        }
        c1, c2, c3 = st.columns(3)
        cols = [c1, c2, c3]
        idx = 0
        for label, data in kpis.items():
            with cols[idx]:
                if data is not None:
                    fmt = f"R$ {data['last']:.2f}" if label == "DÓLAR" else (
                        f"US$ {data['last']:,.0f}" if "BITCOIN" in label else f"{data['last']:,.0f} pts")
                    kpi_card(label, fmt, f"{data['var_pct']:+.2f}% (24h)",
                             color="#FFD700" if data['var_pct'] > 0 else "#FF5252")
                else:
                    kpi_card(label, "—", "...")
            idx += 1

    st.write("")

    # --- ACESSO RÁPIDO (CLEAN & FIXED) ---
    st.markdown("### ⚡ Acesso Rápido")
    with st.container():
        st.markdown("<div class='bee-card'>", unsafe_allow_html=True)

        # Input limpo sem label visível
        quick_ticker = st.text_input("Ticker", placeholder="Digite um ativo (ex: PETR4, BTC, AAPL)...",
                                     label_visibility="collapsed").upper().strip()

        if quick_ticker:
            tk_norm = normalize_ticker(quick_ticker, "Ação", "BRL")

            # Flex container para info e botões (travado na mesma linha)
            c_info, c_btns = st.columns([1.5, 1])

            with c_info:
                if px and yf:
                    hist = yf_last_and_prev_close([tk_norm])
                    if not hist.empty:
                        last = hist.iloc[0]['last']
                        var = hist.iloc[0]['var_pct']
                        cor_txt = "#4CAF50" if var >= 0 else "#FF5252"
                        st.markdown(f"""
                        <div style='margin-top:5px; margin-bottom:5px;'>
                            <span style='font-size:28px; font-weight:800; color:#fff;'>{tk_norm.replace('.SA', '')}</span>
                            <span style='font-size:28px; font-weight:600; color:{cor_txt}; margin-left:10px;'>{last:,.2f} ({var:+.2f}%)</span>
                        </div>
                        """, unsafe_allow_html=True)

            with c_btns:
                # Botões alinhados
                st.markdown(
                    "<div style='display:flex; gap:10px; justify-content:flex-end; align-items:center; height:100%;'>",
                    unsafe_allow_html=True)
                auvp = f"https://analitica.auvp.com.br/acoes/{quick_ticker.lower()}"

                # Apenas AUVP (Investidor10 removido a pedido)
                st.markdown(f"""
                    <a href="{auvp}" target="_blank" class="smallbtn" style="text-decoration:none; padding:10px 16px; background:#5900b3; color:white; border-radius:10px; font-weight:700;">💜 Ver na AUVP</a>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # SPARKLINE CHART (Pequeno e embutido)
            if px and yf:
                chart_data = yf.Ticker(tk_norm).history(period="1mo")
                if not chart_data.empty:
                    fig_mini = px.line(chart_data, y="Close")
                    fig_mini.update_layout(
                        xaxis_visible=False,
                        yaxis_visible=False,
                        margin=dict(l=0, r=0, t=5, b=5),
                        height=45,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    fig_mini.update_traces(line_color='#FFD700', line_width=2)
                    st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})

        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # TOP 5 + NEWS
    c_left, c_right = st.columns([1, 1.2])

    with c_left:
        st.markdown("### 🚀 Top 5 Altas")
        tab_acao, tab_cripto = st.tabs(["🇧🇷 Ações", "₿ Cripto"])
        with tab_acao:
            df_br = yf_last_and_prev_close(TICKERS_BR)
            render_top5_card(df_br, prefixo="R$", tipo="acao")
        with tab_cripto:
            df_cr = yf_last_and_prev_close(TICKERS_CRIPTO)
            render_top5_card(df_cr, prefixo="US$", tipo="cripto")

    with c_right:
        st.markdown("### 📰 Notícias")
        tab_news = st.tabs(["Últimas do Mercado"])
        with tab_news[0]:
            news = get_google_news_items("investimentos+brasil", limit=5)
            if news:
                for n in news:
                    ago = human_time_ago(n['published_dt'])
                    st.markdown(f"""
                        <a href="{n['link']}" target="_blank" class="news-item">
                            <div class="news-title">{n['title']}</div>
                            <div class="news-meta">{n['source']} • {ago}</div>
                        </a>
                        """, unsafe_allow_html=True)
            else:
                st.info("Sem notícias.")


# =====================================================================================
# PAGE: ANALISAR
# =====================================================================================
elif page == "🔍 Analisar":
    st.markdown("## 🔍 Análise")
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

            # PREÇO REAL (FAST INFO)
            cur_price = info.get('currentPrice', 0.0)
            m1.metric("Preço", f"R$ {cur_price:,.2f}" if cur_price else "—")

            # DY CORRIGIDO
            val_dy = info.get('dividendYield')
            if val_dy:
                fmt_dy = f"{val_dy}%" if val_dy > 1 else f"{val_dy * 100:.2f}%"
            else:
                fmt_dy = "—"

            m2.metric("DY", fmt_dy)

            val_pe = info.get('trailingPE')
            m3.metric("P/L", f"{val_pe:.2f}" if val_pe and val_pe is not None else "—")
            m4.metric("Valor", format_market_cap(info.get('marketCap')))

            st.markdown("---")
            fig = get_stock_history_plot(tk_real, period=periodo)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Sem gráfico.")

            with st.expander("Resumo da Empresa (PT-BR)"):
                st.write(info.get('summary', '—'))
        else:
            st.error("Ativo não encontrado.")


# =====================================================================================
# PAGE: CARTEIRA
# =====================================================================================
elif page == "💼 Carteira":
    st.markdown("## 💼 Carteira")
    df = carregar_carteira()

    with st.expander("➕ Adicionar Ativo", expanded=False):
        f1, f2, f3 = st.columns([1, 1, 1])
        with f1:
            tipo = st.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa"])
            ativo = st.text_input("Ticker").upper().strip()
        with f2:
            qtd = st.number_input("Qtd", min_value=0.0, step=0.01)
            preco = st.number_input("Preço Médio", min_value=0.0, step=0.01)
        with f3:
            moeda = st.selectbox("Moeda", ["BRL", "USD"])
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='yellowbtn'>", unsafe_allow_html=True)
            if st.button("Salvar"):
                if ativo and qtd > 0:
                    novo = {"Tipo": tipo, "Ativo": ativo, "Qtd": qtd, "Preco_Medio": preco, "Moeda": moeda, "Obs": "",
                            "Nome": ativo}
                    df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                    salvar_carteira(df)
                    st.success("Salvo!")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if not df.empty:
        with st.spinner("..."):
            df_calc, kpi = atualizar_precos_carteira(df)

        k1, k2, k3 = st.columns(3)
        with k1:
            kpi_card("Total", f"R$ {kpi['total_brl']:,.2f}", "Patrimônio")
        with k2:
            kpi_card("Resultado", f"R$ {kpi['pnl_brl']:,.2f}", f"{kpi['pnl_pct']:+.2f}%",
                     color="#4CAF50" if kpi['pnl_brl'] >= 0 else "#FF5252")
        with k3:
            kpi_card("Ativos", f"{len(df_calc)}", "Diversificação")

        st.write("")
        if px:
            g1, g2 = st.columns([1, 2])
            with g1:
                df_grp = df_calc.groupby("Ativo")["Total_BRL"].sum().reset_index()
                fig_pie = px.pie(df_grp, values='Total_BRL', names='Ativo', hole=0.5)
                fig_pie.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=220,
                                      paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                cols_view = ["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "Total_BRL", "PnL_Pct"]
                st.dataframe(
                    df_calc[cols_view].style.format({
                        "Qtd": "{:.2f}", "Preco_Medio": "R$ {:.2f}", "Preco_Atual_BRL": "R$ {:.2f}",
                        "Total_BRL": "R$ {:.2f}", "PnL_Pct": "{:+.2f}%"
                    }).bar(subset=["PnL_Pct"], align="mid", color=['#FF5252', '#4CAF50']),
                    use_container_width=True, height=220
                )

        with st.expander("Tabela Completa"):
            edited = st.data_editor(df_calc[CARTEIRA_COLS], num_rows="dynamic", use_container_width=True)
            if st.button("Salvar Edição"):
                salvar_carteira(edited)
                st.success("Salvo!")
                st.rerun()
    else:
        st.info("Carteira vazia.")


# =====================================================================================
# PAGE: CALCULADORAS
# =====================================================================================
elif page == "🧮 Calculadoras":
    st.markdown("## 🧮 Calculadoras")
    tabs = st.tabs(["Juros Compostos", "FIRE", "Meta"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        vp = c1.number_input("Inicial", value=1000.0)
        pmt = c2.number_input("Mensal", value=500.0)
        taxa = c3.number_input("Taxa Anual %", value=10.0)
        anos = st.slider("Anos", 1, 50, 10)
        if st.button("Calcular"):
            m = anos * 12
            r = (taxa / 100) / 12
            vf = vp * (1 + r) ** m + pmt * (((1 + r) ** m - 1) / r)
            st.success(f"Total: **R$ {vf:,.2f}**")

    with tabs[1]:
        gasto = st.number_input("Gasto Mensal", value=5000.0)
        tss = st.slider("Taxa de Saque %", 3.0, 6.0, 4.0, 0.1)
        st.markdown(f"### Meta FIRE: **R$ {(gasto * 12) / (tss / 100):,.2f}**")

    with tabs[2]:
        aport = st.number_input("Aporte", value=1000.0)
        tx = st.number_input("Taxa %", value=10.0)
        if st.button("Tempo p/ 1 Milhão"):
            r = (tx / 100) / 12
            n = math.log((1000000 * r) / aport + 1) / math.log(1 + r)
            st.success(f"**{n / 12:.1f} anos**")


# =====================================================================================
# PAGE: NEWS
# =====================================================================================
elif page == "📰 News":
    st.markdown("## 📰 Feed")
    termo = st.text_input("Buscar", "economia brasil")
    items = get_google_news_items(termo.replace(" ", "+"), limit=10)
    for n in items:
        st.markdown(f"""
            <a href="{n['link']}" target="_blank" class="bee-card" style="display:block; text-decoration:none; margin-bottom:10px;">
                <div style="font-weight:700; font-size:15px; color:#FFD700;">{n['title']}</div>
                <div style="font-size:11px; color:#aaa; margin-top:5px;">{n['source']} • {human_time_ago(n['published_dt'])}</div>
            </a>
            """, unsafe_allow_html=True)


# =====================================================================================
# PAGE: BEE TV
# =====================================================================================
elif page == "🍿 Bee TV":
    st.markdown("## 🍿 Bee TV")
    st.caption("Feed unificado: últimos vídeos dos seus canais favoritos.")

    if st.button("🔄 Atualizar Feed"):
        # Limpa cache para forçar novo sorteio
        get_bee_tv_feed_randomized.clear()
        st.rerun()

    # Usa a nova função com sorteio inteligente (4 longos + 2 shorts)
    vids = get_bee_tv_feed_randomized()

    if not vids:
        st.warning("Não foi possível carregar os vídeos no momento.")
    else:
        # Grid 3 colunas
        rows = [vids[i:i + 3] for i in range(0, len(vids), 3)]
        for row in rows:
            cols = st.columns(3)
            for i, v in enumerate(row):
                with cols[i]:
                    ago = human_time_ago(v['dt'])
                    st.markdown(f"""
                        <a href="{v['link']}" target="_blank" class="video-card">
                            <img src="{v['thumb']}" class="video-thumb">
                            <div class="video-info">
                                <div>
                                    <div class="video-ch">{v['canal']}</div>
                                    <div class="video-tt">{v['titulo']}</div>
                                </div>
                                <div class="video-dt">Postado {ago}</div>
                            </div>
                        </a>
                    """, unsafe_allow_html=True)


# =====================================================================================
# PAGE: TUTORIAL
# =====================================================================================
elif page == "📱 Tutorial":
    st.markdown("## 📱 Tutorial")
    st.info("Funcionalidades principais:")
    st.markdown(
        "- **Home:** Resumo rápido e notícias.\n- **Analisar:** Gráficos e dados fundamentalistas.\n- **Carteira:** Controle seus investimentos.")
else:
    st.write("Em construção.")