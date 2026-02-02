# Bee Finanças — Streamlit App (v5.0 FULL)
# ---------------------------------------------------------------
# ✅ Home + KPIs + Altas/Baixas com SEMÂNTICA certa
# ✅ Explorar estilo AUVP (filtros + cards + métricas)
# ✅ Rankings por critério (var, market cap, DY, P/L)
# ✅ Carteira persistente (não some)
# ✅ Bee TV (RSS + fallback) robusto
# ✅ News RSS
# ✅ Calculadoras completas (Juros, RF, FIRE, Milhão, Alugar x Financiar com crédito)
# ---------------------------------------------------------------

import os
import re
import math
import time
import random
import warnings
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import feedparser
import requests

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from dateutil import parser as dtparser
except Exception:
    dtparser = None


# =====================================================================================
# 0) CONFIG
# =====================================================================================
st.set_page_config(page_title="Bee Finanças", page_icon="🐝", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")

DATA_DIR = os.path.join(os.path.expanduser("~"), ".bee_financas")
os.makedirs(DATA_DIR, exist_ok=True)
CARTEIRA_FILE = os.path.join(DATA_DIR, "minha_carteira.csv")


# =====================================================================================
# 1) CSS / THEME
# =====================================================================================
st.markdown(
    """
<style>
.stApp {
  background:
    radial-gradient(1100px 480px at 30% 10%, rgba(255,215,0,0.08), transparent 55%),
    radial-gradient(900px 420px at 85% 20%, rgba(89,0,179,0.10), transparent 55%),
    #0B0F14;
}

h1,h2,h3 { color: #FFD700 !important; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; font-weight: 950; }
p, span, div, label { color: #E6E6E6; }

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0A0E13 0%, #070A0F 100%);
  border-right: 1px solid rgba(255,255,255,0.06);
}

.sidebar-brand { display:flex; align-items:center; gap:10px; padding: 10px 2px 6px 2px; }
.sidebar-title { font-size: 16px; font-weight: 950; color: #FFD700; margin:0; }
.sidebar-sub { font-size: 11px; color: rgba(255,255,255,0.55); margin-top:-2px; }
.sidebar-group { margin-top: 10px; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: rgba(255,255,255,0.55); padding-left: 2px; }

.stButton > button {
  background: #FFD700 !important;
  color: #000 !important;   /* ✅ letra preta no amarelo */
  font-weight: 950 !important;
  border-radius: 14px !important;
  border: 0 !important;
  padding: 0.70rem 1.1rem !important;
  transition: 0.18s ease !important;
}
.stButton > button:hover { filter: brightness(1.05) !important; transform: translateY(-1px) !important; }

.btn-dark button {
  background: rgba(255,255,255,0.06) !important;
  color: #FFF !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
}
.btn-dark button:hover { border-color: rgba(255,215,0,0.35) !important; }

.stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea {
  background: rgba(255,255,255,0.04) !important;
  color: #FFF !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
}

[data-testid="stDataFrame"] {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  overflow: hidden;
}

.bee-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px;
}
.bee-card-title {
  color: rgba(255,215,0,0.95);
  font-weight: 950;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.bee-kpi { color: #FFFFFF; font-weight: 950; font-size: 30px; line-height: 1.1; }
.bee-sub { color: rgba(255,255,255,0.65); font-size: 12px; }

.feature-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 14px;
  transition: 0.18s ease;
  height: 100%;
}
.feature-card:hover { transform: translateY(-2px); border-color: rgba(255,215,0,0.35); }
.feature-title { font-weight: 950; font-size: 14px; color: #fff; }
.feature-sub { margin-top: 6px; color: rgba(255,255,255,0.65); font-size: 12px; }

.video-card {
  display: block;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  overflow: hidden;
  text-decoration: none;
  transition: 0.2s ease;
  height: 100%;
}
.video-card:hover { transform: translateY(-3px); border-color: rgba(255,215,0,0.45); }
.video-thumb { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
.video-info { padding: 10px 12px 12px 12px; }
.video-channel { color: rgba(255,215,0,0.95); font-size: 10px; text-transform: uppercase; font-weight: 950; letter-spacing: 0.08em; }
.video-title { color: #FFF; font-weight: 850; font-size: 13px; line-height: 1.35; margin-top: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.video-meta { margin-top: 8px; color: rgba(255,255,255,0.60); font-size: 11px; }

.news-item {
  display: block;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 10px 12px;
  text-decoration: none;
  margin-bottom: 10px;
  transition: 0.2s ease;
}
.news-item:hover { border-color: rgba(255,215,0,0.45); transform: translateY(-1px); }
.news-title { color: #FFF; font-weight: 900; font-size: 13px; line-height: 1.35; }
.news-meta { margin-top: 6px; color: rgba(255,255,255,0.65); font-size: 11px; }
</style>
""",
    unsafe_allow_html=True,
)


# =====================================================================================
# 2) UTIL
# =====================================================================================
def human_time_ago(dt: datetime) -> str:
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    sec = int(delta.total_seconds())
    if sec < 60:
        return "agora"
    minutes = sec // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} h"
    days = hours // 24
    return f"há {days} d"


def normalize_ticker(ativo: str, tipo: str, moeda: str) -> str:
    a = (ativo or "").strip().upper()
    if not a:
        return ""
    if a.endswith(".SA") or a.endswith("-USD") or a.endswith("=X") or a.startswith("^"):
        return a
    if tipo == "Cripto":
        if "-" not in a:
            return f"{a}-USD"
        return a
    if a in ("BRL=X", "USDBRL", "USD", "DOLAR", "DÓLAR"):
        return "BRL=X"
    has_digit = any(ch.isdigit() for ch in a)
    if moeda == "BRL" and has_digit:
        return f"{a}.SA"
    return a


def fmt_money_brl(x: float) -> str:
    try:
        return f"R$ {x:,.2f}"
    except Exception:
        return "—"


def fmt_pct(x: float) -> str:
    try:
        return f"{x:+.2f}%"
    except Exception:
        return "—"


@st.cache_data(ttl=600)
def get_usdbrl() -> float:
    if yf is None:
        return 5.80
    try:
        h = yf.Ticker("BRL=X").history(period="1d")
        return float(h["Close"].iloc[-1])
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

    def close_series(t: str):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if ("Close", t) in data.columns:
                    return data[("Close", t)]
                if (t, "Close") in data.columns:
                    return data[(t, "Close")]
        except Exception:
            pass

        try:
            close = data["Close"]
            if isinstance(close, pd.DataFrame) and t in close.columns:
                return close[t]
            if isinstance(close, pd.Series) and len(tickers) == 1:
                return close
        except Exception:
            pass
        return None

    for t in tickers:
        s = close_series(t)
        if s is None:
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 2:
            continue
        last = float(s.iloc[-1])
        prev = float(s.iloc[-2])
        var = ((last - prev) / prev) * 100.0 if prev != 0 else 0.0
        out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var})

    return pd.DataFrame(out)


@st.cache_data(ttl=1200)
def yf_info_fast(ticker: str) -> dict:
    """
    Pega métricas úteis sem travar demais.
    (yfinance info às vezes falha — por isso tudo com fallback)
    """
    if yf is None or not ticker:
        return {}
    try:
        tk = yf.Ticker(ticker)
        info = {}
        # fast_info (quando existe) é mais leve
        try:
            fi = tk.fast_info
            if fi:
                info["last_price"] = float(fi.get("last_price") or 0.0)
                info["market_cap"] = float(fi.get("market_cap") or 0.0)
                info["currency"] = fi.get("currency")
        except Exception:
            pass

        # info completo (pode falhar)
        try:
            inf = tk.info or {}
            # métricas clássicas
            info["trailingPE"] = inf.get("trailingPE")
            info["dividendYield"] = inf.get("dividendYield")
            info["longName"] = inf.get("longName") or inf.get("shortName")
            info["sector"] = inf.get("sector")
        except Exception:
            pass

        return info
    except Exception:
        return {}


def format_market_cap(x: float) -> str:
    try:
        x = float(x)
        if x <= 0:
            return "—"
        if x >= 1e12:
            return f"{x/1e12:.2f} T"
        if x >= 1e9:
            return f"{x/1e9:.2f} B"
        if x >= 1e6:
            return f"{x/1e6:.2f} M"
        return f"{x:,.0f}"
    except Exception:
        return "—"


# =====================================================================================
# 3) DATASETS (listas prontas)
# =====================================================================================
# Ações BR (lista enxuta top/queridinhas — dá pra expandir depois)
TICKERS_BR = [
    "VALE3.SA","PETR4.SA","ITUB4.SA","BBDC4.SA","BBAS3.SA","WEGE3.SA","PRIO3.SA","RENT3.SA","SUZB3.SA","GGBR4.SA",
    "B3SA3.SA","ABEV3.SA","TAEE11.SA","EGIE3.SA","ITSA4.SA","RADL3.SA","LREN3.SA","VIVT3.SA","JBSS3.SA",
]

# FIIs (lista exemplo)
TICKERS_FII = [
    "HGLG11.SA","XPLG11.SA","VISC11.SA","BCFF11.SA","KNRI11.SA","MXRF11.SA","HSML11.SA","HGRE11.SA","RBRP11.SA"
]

# Cripto
TICKERS_CRIPTO = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","DOGE-USD","AVAX-USD","ADA-USD"]

# US (exemplo)
TICKERS_US = ["AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META"]


# =====================================================================================
# 4) NEWS
# =====================================================================================
@st.cache_data(ttl=600)
def get_google_news_items(query: str, limit: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        published_dt = None
        try:
            if getattr(e, "published", None) and dtparser:
                published_dt = dtparser.parse(e.published)
                if published_dt.tzinfo is None:
                    published_dt = published_dt.replace(tzinfo=timezone.utc)
        except Exception:
            published_dt = None

        title = getattr(e, "title", "Notícia")
        source = title.rsplit(" - ", 1)[-1].strip() if " - " in title else "Google News"
        items.append({"title": title, "link": e.link, "source": source, "published_dt": published_dt})
    return items


# =====================================================================================
# 5) BEE TV
# =====================================================================================
CANAIS_GIGANTES = {
    "Me Poupe!": "UC8mDF5mWNGE-Kpfcvnn0bUg",
    "Fernando Ulrich": "UCLJkh3QjHsLtK0LZFd28oGg",
    "Primo Pobre": "UCOjXqrOxAdXa04obIQREfCA",
    "Investidor Sardinha (Raul Sena)": "UCM3vJxmuJJkk1r0yzFI9eZg",
    "Bruno Perini (Você MAIS Rico)": "UCCE-jo1GvBJqyj1b287h7jA",
}

@st.cache_data(ttl=900)
def buscar_videos_rss(canal_id: str, max_entries: int = 3) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}"
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code != 200 or not resp.text:
        return []
    feed = feedparser.parse(resp.text)
    if not getattr(feed, "entries", None):
        return []

    out = []
    for e in feed.entries[:max_entries]:
        yt_id = getattr(e, "yt_videoid", None)
        if not yt_id:
            m = re.search(r"v=([a-zA-Z0-9_-]{6,})", getattr(e, "link", ""))
            yt_id = m.group(1) if m else None

        published_dt = None
        try:
            if getattr(e, "published", None) and dtparser:
                published_dt = dtparser.parse(e.published)
                if published_dt.tzinfo is None:
                    published_dt = published_dt.replace(tzinfo=timezone.utc)
        except Exception:
            published_dt = None

        out.append(
            {
                "titulo": getattr(e, "title", "Vídeo"),
                "link": getattr(e, "link", "#"),
                "thumb": f"https://img.youtube.com/vi/{yt_id}/mqdefault.jpg" if yt_id else None,
                "published_dt": published_dt,
            }
        )
    return out


@st.cache_data(ttl=900)
def buscar_videos_aleatorios(n_canais: int = 6) -> tuple[list[dict], str]:
    nomes = list(CANAIS_GIGANTES.keys())
    random.shuffle(nomes)
    escolhidos = nomes[: min(n_canais, len(nomes))]

    videos = []
    any_rss_ok = False

    for nome in escolhidos:
        canal_id = CANAIS_GIGANTES[nome]

        try:
            entries = buscar_videos_rss(canal_id, max_entries=3)
            if entries:
                any_rss_ok = True
                pick = random.choice(entries)
                videos.append(
                    {
                        "canal": nome,
                        "titulo": pick["titulo"],
                        "link": pick["link"],
                        "thumb": pick["thumb"],
                        "published_dt": pick["published_dt"],
                    }
                )
                continue
        except Exception:
            pass

        videos.append(
            {
                "canal": nome,
                "titulo": "Abrir vídeos do canal",
                "link": f"https://www.youtube.com/channel/{canal_id}/videos",
                "thumb": None,
                "published_dt": None,
            }
        )

    return videos, ("rss" if any_rss_ok else "fallback")


# =====================================================================================
# 6) CARTEIRA (persistente)
# =====================================================================================
CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]

def carregar_carteira() -> pd.DataFrame:
    if not os.path.exists(CARTEIRA_FILE):
        return pd.DataFrame(columns=CARTEIRA_COLS)
    try:
        df = pd.read_csv(CARTEIRA_FILE)
    except Exception:
        return pd.DataFrame(columns=CARTEIRA_COLS)

    for c in CARTEIRA_COLS:
        if c not in df.columns:
            df[c] = "" if c in ("Nome", "Obs") else 0.0

    df["Tipo"] = df["Tipo"].replace("", "Ação/ETF/FII")
    df["Nome"] = df["Nome"].replace("", df["Ativo"])
    df["Moeda"] = df["Moeda"].replace("", "BRL")
    return df[CARTEIRA_COLS]


def salvar_carteira(df: pd.DataFrame) -> None:
    df = df.copy()
    for c in CARTEIRA_COLS:
        if c not in df.columns:
            df[c] = "" if c in ("Nome", "Obs") else 0.0
    df[CARTEIRA_COLS].to_csv(CARTEIRA_FILE, index=False)


def atualizar_precos_carteira(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    if df.empty:
        return df, {"total_brl": 0.0, "pnl_brl": 0.0, "pnl_pct": 0.0, "usdbrl": get_usdbrl()}

    usdbrl = get_usdbrl()

    df["Ticker_YF"] = df.apply(
        lambda r: normalize_ticker(
            str(r.get("Ativo", "")),
            str(r.get("Tipo", "Ação/ETF/FII")),
            str(r.get("Moeda", "BRL")).upper() or "BRL",
        ),
        axis=1,
    )

    is_rf = df["Tipo"].astype(str).str.strip().str.lower().isin(["renda fixa", "rf"])
    df["Preco_Atual_BRL"] = 0.0
    df.loc[is_rf, "Preco_Atual_BRL"] = 1.0

    tickers = df.loc[~is_rf, "Ticker_YF"].dropna().astype(str).unique().tolist()

    price_map = {}
    var_map = {}
    if tickers and yf is not None:
        px = yf_last_and_prev_close(tickers)
        for _, row in px.iterrows():
            price_map[str(row["ticker"])] = float(row["last"])
            var_map[str(row["ticker"])] = float(row["var_pct"])

    df["Var_1D"] = 0.0

    for i, r in df.iterrows():
        if bool(is_rf.iloc[i]):
            continue
        t = str(r["Ticker_YF"])
        last = float(price_map.get(t, 0.0))
        var = float(var_map.get(t, 0.0))

        moeda = str(r.get("Moeda", "BRL")).upper() or "BRL"
        if t.endswith("-USD") or moeda == "USD":
            last = last * usdbrl

        df.at[i, "Preco_Atual_BRL"] = last
        df.at[i, "Var_1D"] = var

    df["Qtd"] = pd.to_numeric(df["Qtd"], errors="coerce").fillna(0.0)
    df["Preco_Medio"] = pd.to_numeric(df["Preco_Medio"], errors="coerce").fillna(0.0)

    df["Total_BRL"] = df["Preco_Atual_BRL"] * df["Qtd"]

    custo = df["Preco_Medio"] * df["Qtd"]
    df["PnL_BRL"] = df["Total_BRL"] - custo
    df["PnL_Pct"] = 0.0
    mask = custo > 0
    df.loc[mask, "PnL_Pct"] = (df.loc[mask, "PnL_BRL"] / custo[mask]) * 100.0

    total_brl = float(df["Total_BRL"].sum())
    pnl_brl = float(df.loc[mask, "PnL_BRL"].sum())
    pnl_pct = float((pnl_brl / float(custo[mask].sum())) * 100.0) if float(custo[mask].sum()) > 0 else 0.0

    return df, {"total_brl": total_brl, "pnl_brl": pnl_brl, "pnl_pct": pnl_pct, "usdbrl": usdbrl}


# =====================================================================================
# 7) HOME SNAPSHOT
# =====================================================================================
@st.cache_data(ttl=600)
def get_market_snapshot() -> dict:
    if yf is None:
        return {"ok": False, "msg": "yfinance não está disponível. Instale com: pip install yfinance"}

    tickers_kpi = {"IBOV": "^BVSP", "USD/BRL": "BRL=X", "BTC": "BTC-USD"}
    df = yf_last_and_prev_close(list(tickers_kpi.values()))
    mp = {str(r["ticker"]): {"last": float(r["last"]), "var_pct": float(r["var_pct"])} for _, r in df.iterrows()}

    def pack(label, t):
        r = mp.get(t, None)
        if r is None:
            return {"label": label, "last": None, "var": None}
        return {"label": label, "last": r["last"], "var": r["var_pct"]}

    acoes = TICKERS_BR[:]
    cripto = TICKERS_CRIPTO[:]

    df_ac = yf_last_and_prev_close(acoes)
    df_cr = yf_last_and_prev_close(cripto)

    def pretty_symbol(t):
        return t.replace(".SA", "").replace("-USD", "")

    if not df_ac.empty:
        df_ac = df_ac.copy()
        df_ac["Ativo"] = df_ac["ticker"].apply(pretty_symbol)
        df_ac = df_ac[["Ativo", "var_pct"]].rename(columns={"var_pct": "Var"})

    if not df_cr.empty:
        df_cr = df_cr.copy()
        df_cr["Ativo"] = df_cr["ticker"].apply(pretty_symbol)
        df_cr = df_cr[["Ativo", "var_pct"]].rename(columns={"var_pct": "Var"})

    return {
        "ok": True,
        "kpis": [pack(k, v) for k, v in tickers_kpi.items()],
        "acoes": df_ac,
        "cripto": df_cr,
        "updated_at": datetime.now().strftime("%H:%M"),
    }


def show_top_bottom_semantic(df: pd.DataFrame):
    """
    ✅ Corrige o problema: "baixas" não pode mostrar positivo como se fosse queda.
    Regras:
      - Se existir negativos: Baixas = 5 menores (mais negativos)
      - Se NÃO existir negativos: mostra "Menores variações" e não chama de "baixas"
    """
    if df is None or df.empty:
        st.info("Sem dados agora.")
        return

    df = df.copy()
    df["Var"] = pd.to_numeric(df["Var"], errors="coerce").fillna(0.0)

    top = df.nlargest(5, "Var")

    negatives = df[df["Var"] < 0].copy()
    if not negatives.empty:
        bottom = negatives.nsmallest(5, "Var")
        bottom_title = "Top 5 baixas"
    else:
        bottom = df.nsmallest(5, "Var")
        bottom_title = "Menores variações"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Top 5 altas")
        t = top.copy()
        t["Var"] = t["Var"].map(lambda x: f"{x:+.2f}%")
        st.dataframe(t, use_container_width=True, hide_index=True)

    with c2:
        st.markdown(f"#### {bottom_title}")
        b = bottom.copy()
        b["Var"] = b["Var"].map(lambda x: f"{x:+.2f}%")
        st.dataframe(b, use_container_width=True, hide_index=True)


# =====================================================================================
# 8) NAV — sidebar only
# =====================================================================================
PAGES = [
    "🏠 Home",
    "🧭 Explorar",
    "🏆 Rankings",
    "🔍 Analisar",
    "💼 Carteira",
    "🧮 Calculadoras",
    "📰 News",
    "🍿 Bee TV",
    "📒 Gastos",
    "📱 Tutorial",
]

if "page" not in st.session_state:
    st.session_state["page"] = "🏠 Home"

st.sidebar.markdown(
    """
<div class="sidebar-brand">
  <div style="font-size:20px;">🐝</div>
  <div>
    <div class="sidebar-title">Bee Finanças</div>
    <div class="sidebar-sub">Seu painel financeiro pessoal</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

def nav_btn(label: str, page_key: str, help_text: str):
    with st.sidebar:
        st.markdown("<div class='btn-dark'>", unsafe_allow_html=True)
        if st.button(label, use_container_width=True, help=help_text, key=f"BTN_{page_key}"):
            st.session_state["page"] = page_key
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

st.sidebar.markdown("<div class='sidebar-group'>Explorar</div>", unsafe_allow_html=True)
nav_btn("🏠 Home", "🏠 Home", "Mercado e destaques")
nav_btn("🧭 Explorar", "🧭 Explorar", "Explorar ativos por filtros")
nav_btn("🏆 Rankings", "🏆 Rankings", "Rankings por critério")
nav_btn("🔍 Analisar", "🔍 Analisar", "Links + preço rápido")

st.sidebar.markdown("<div class='sidebar-group'>Ferramentas</div>", unsafe_allow_html=True)
nav_btn("💼 Carteira", "💼 Carteira", "Seu patrimônio em tempo real")
nav_btn("🧮 Calculadoras", "🧮 Calculadoras", "Juros, RF, FIRE, Milhão, Imóvel")
nav_btn("📒 Gastos (em breve)", "📒 Gastos", "Open Finance + orçamento (futuro)")

st.sidebar.markdown("<div class='sidebar-group'>Conteúdo</div>", unsafe_allow_html=True)
nav_btn("📰 News", "📰 News", "Notícias do mercado")
nav_btn("🍿 Bee TV", "🍿 Bee TV", "Vídeos e canais")
nav_btn("📱 Tutorial", "📱 Tutorial", "Passo a passo BTG")

st.sidebar.markdown("---")
st.sidebar.caption(f"📁 Carteira: {CARTEIRA_FILE}")

page = st.session_state["page"]


# =====================================================================================
# 9) TOP BAR
# =====================================================================================
topL, topR = st.columns([1, 2])
with topL:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=170)
    else:
        st.markdown("## 🐝 Bee Finanças")

with topR:
    st.write("")
    if st.button("🔄 Atualizar tudo"):
        st.cache_data.clear()
        st.rerun()

st.divider()


# =====================================================================================
# 10) PAGES
# =====================================================================================

# -------------------------------- HOME --------------------------------
if page == "🏠 Home":
    st.markdown("### 🔥 Resumo do dia")

    snap = get_market_snapshot()
    if not snap.get("ok"):
        st.warning(snap.get("msg", "Sem dados."))
    else:
        cols = st.columns(3)
        for i, k in enumerate(snap["kpis"]):
            with cols[i]:
                last = k["last"]
                var = k["var"]
                if last is None:
                    html = f"""
                    <div class="bee-card">
                      <div class="bee-card-title">{k['label']}</div>
                      <div class="bee-kpi">—</div>
                      <div class="bee-sub">Sem dados</div>
                    </div>
                    """
                else:
                    if k["label"] == "IBOV":
                        val = f"{last:,.0f}"
                    elif k["label"] == "USD/BRL":
                        val = f"R$ {last:,.2f}"
                    else:
                        val = f"US$ {last:,.0f}"
                    html = f"""
                    <div class="bee-card">
                      <div class="bee-card-title">{k['label']}</div>
                      <div class="bee-kpi">{val}</div>
                      <div class="bee-sub">{var:+.2f}% • atualizado {snap['updated_at']}</div>
                    </div>
                    """
                st.markdown(html, unsafe_allow_html=True)

        st.write("")
        st.markdown("### 📈 Maiores altas e baixas")
        tabA, tabB = st.tabs(["🇧🇷 Ações BR", "₿ Cripto"])
        with tabA:
            show_top_bottom_semantic(snap["acoes"])
        with tabB:
            show_top_bottom_semantic(snap["cripto"])


# -------------------------------- EXPLORAR --------------------------------
elif page == "🧭 Explorar":
    st.markdown("### 🧭 Explorar (estilo AUVP)")
    st.caption("Escolha o universo, filtre e veja cards com métricas.")

    colF1, colF2, colF3 = st.columns([1.2, 1, 1])

    with colF1:
        universo = st.selectbox("Universo", ["Ações BR", "FIIs", "Cripto", "Internacional (US)"])
    with colF2:
        ordenar = st.selectbox("Ordenar por", ["Variação 1D", "Market Cap", "Dividend Yield", "P/L"])
    with colF3:
        busca = st.text_input("Buscar (código ou nome)", placeholder="Ex: PETR, VALE, BTC...").strip().upper()

    if universo == "Ações BR":
        base = TICKERS_BR
    elif universo == "FIIs":
        base = TICKERS_FII
    elif universo == "Cripto":
        base = TICKERS_CRIPTO
    else:
        base = TICKERS_US

    # Fetch preços (var 1D)
    df_px = yf_last_and_prev_close(base) if yf is not None else pd.DataFrame()
    mp_px = {str(r["ticker"]): {"last": float(r["last"]), "var": float(r["var_pct"])} for _, r in df_px.iterrows()} if not df_px.empty else {}

    usdbrl = get_usdbrl()

    rows = []
    for t in base:
        info = yf_info_fast(t)
        last = mp_px.get(t, {}).get("last", info.get("last_price", 0.0) or 0.0)
        var = mp_px.get(t, {}).get("var", 0.0)
        name = info.get("longName") or t
        mc = info.get("market_cap", 0.0) or 0.0
        pe = info.get("trailingPE", None)
        dy = info.get("dividendYield", None)

        # Converte cripto/us pra BRL quando fizer sentido no display? aqui só mostra USD como USD no universo US/Cripto.
        currency = info.get("currency")
        if universo in ("Cripto", "Internacional (US)"):
            # display em USD
            pass
        else:
            # display em BRL já vem de .SA geralmente
            pass

        rows.append(
            {
                "Ticker": t,
                "Nome": name,
                "Preço": float(last) if last else 0.0,
                "Var1D": float(var),
                "MarketCap": float(mc) if mc else 0.0,
                "PE": pe if pe is not None else None,
                "DY": dy if dy is not None else None,
            }
        )

    df = pd.DataFrame(rows)

    # filtro por busca
    if busca:
        mask = df["Ticker"].str.contains(busca, na=False) | df["Nome"].astype(str).str.upper().str.contains(busca, na=False)
        df = df[mask].copy()

    # ordenar
    if ordenar == "Variação 1D":
        df = df.sort_values("Var1D", ascending=False)
    elif ordenar == "Market Cap":
        df = df.sort_values("MarketCap", ascending=False)
    elif ordenar == "Dividend Yield":
        # dy vem como fração (0.08), ordenar desc
        df["DY_num"] = pd.to_numeric(df["DY"], errors="coerce")
        df = df.sort_values("DY_num", ascending=False)
    else:
        # P/L menor é "melhor" (mas cuidado), então asc
        df["PE_num"] = pd.to_numeric(df["PE"], errors="coerce")
        df = df.sort_values("PE_num", ascending=True)

    st.write("")

    # Mostrar cards
    show_n = st.slider("Quantos mostrar", 6, 30, 12)
    show = df.head(show_n).reset_index(drop=True)

    cols = st.columns(3)
    for i, r in show.iterrows():
        t = r["Ticker"]
        name = str(r["Nome"])[:60]
        price = r["Preço"]
        var = r["Var1D"]
        mc = r["MarketCap"]
        pe = r["PE"]
        dy = r["DY"]

        price_txt = f"{price:,.2f}" if price else "—"
        if universo in ("Cripto", "Internacional (US)"):
            price_txt = f"US$ {price_txt}"
        else:
            price_txt = f"R$ {price_txt}"

        dy_txt = "—"
        if dy is not None and isinstance(dy, (int, float)):
            dy_txt = f"{(dy*100):.2f}%"

        pe_txt = "—"
        if pe is not None:
            try:
                pe_txt = f"{float(pe):.2f}"
            except Exception:
                pe_txt = "—"

        with cols[i % 3]:
            st.markdown(
                f"""
<div class="feature-card">
  <div class="feature-title">{t.replace(".SA","")}</div>
  <div class="feature-sub">{name}</div>
  <div style="margin-top:10px;font-weight:950;font-size:20px;color:#fff;">{price_txt}</div>
  <div style="margin-top:2px;color:rgba(255,255,255,0.7);font-size:12px;">Var 1D: <b>{var:+.2f}%</b></div>
  <div style="margin-top:6px;color:rgba(255,255,255,0.7);font-size:12px;">Market cap: <b>{format_market_cap(mc)}</b></div>
  <div style="margin-top:2px;color:rgba(255,255,255,0.7);font-size:12px;">P/L: <b>{pe_txt}</b> • DY: <b>{dy_txt}</b></div>
  <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
    <a href="https://investidor10.com.br/acoes/{t.replace(".SA","").lower()}/" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:8px 10px;border-radius:12px;background:#002e6e;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">📊 I10</span>
    </a>
    <a href="https://www.google.com/search?q=cota%C3%A7%C3%A3o+{t.replace(".SA","")}" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:8px 10px;border-radius:12px;background:#2b2f36;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">🔎 Google</span>
    </a>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )


# -------------------------------- RANKINGS --------------------------------
elif page == "🏆 Rankings":
    st.markdown("### 🏆 Rankings por critério")
    st.caption("Escolha um critério e o universo. (Métricas dependem do que o Yahoo Finance fornece.)")

    c1, c2, c3 = st.columns([1.2, 1.2, 1])

    with c1:
        universo = st.selectbox("Universo", ["Ações BR", "FIIs", "Cripto", "Internacional (US)"], key="rank_uni")
    with c2:
        criterio = st.selectbox("Critério", ["Variação 1D (alto/baixo)", "Market Cap (maiores)", "Dividend Yield (maiores)", "P/L (menores)"], key="rank_crit")
    with c3:
        topn = st.slider("Top N", 5, 30, 10, key="rank_topn")

    if universo == "Ações BR":
        base = TICKERS_BR
    elif universo == "FIIs":
        base = TICKERS_FII
    elif universo == "Cripto":
        base = TICKERS_CRIPTO
    else:
        base = TICKERS_US

    # preços + var
    df_px = yf_last_and_prev_close(base) if yf is not None else pd.DataFrame()
    mp_px = {str(r["ticker"]): {"last": float(r["last"]), "var": float(r["var_pct"])} for _, r in df_px.iterrows()} if not df_px.empty else {}

    rows = []
    for t in base:
        info = yf_info_fast(t)
        rows.append(
            {
                "Ativo": t.replace(".SA","").replace("-USD",""),
                "Ticker": t,
                "Preço": float(mp_px.get(t, {}).get("last", info.get("last_price", 0.0) or 0.0)),
                "Var1D": float(mp_px.get(t, {}).get("var", 0.0)),
                "MarketCap": float(info.get("market_cap", 0.0) or 0.0),
                "PE": info.get("trailingPE", None),
                "DY": info.get("dividendYield", None),
            }
        )

    df = pd.DataFrame(rows)

    st.write("")
    if criterio == "Variação 1D (alto/baixo)":
        tab1, tab2 = st.tabs(["🔥 Maiores altas", "📉 Baixas / Menores variações"])
        with tab1:
            d = df.sort_values("Var1D", ascending=False).head(topn)[["Ativo","Var1D","Preço"]].copy()
            d["Var1D"] = d["Var1D"].map(lambda x: f"{x:+.2f}%")
            st.dataframe(d, use_container_width=True, hide_index=True)
        with tab2:
            # ✅ semântica certa igual na Home
            negatives = df[df["Var1D"] < 0].copy()
            if not negatives.empty:
                d = negatives.sort_values("Var1D", ascending=True).head(topn)[["Ativo","Var1D","Preço"]].copy()
                title = "Piores quedas"
            else:
                d = df.sort_values("Var1D", ascending=True).head(topn)[["Ativo","Var1D","Preço"]].copy()
                title = "Menores variações (não teve quedas)"
            st.markdown(f"**{title}**")
            d["Var1D"] = d["Var1D"].map(lambda x: f"{x:+.2f}%")
            st.dataframe(d, use_container_width=True, hide_index=True)

    elif criterio == "Market Cap (maiores)":
        d = df.sort_values("MarketCap", ascending=False).head(topn)[["Ativo","MarketCap","Preço","Var1D"]].copy()
        d["MarketCap"] = d["MarketCap"].map(format_market_cap)
        d["Var1D"] = d["Var1D"].map(lambda x: f"{x:+.2f}%")
        st.dataframe(d, use_container_width=True, hide_index=True)

    elif criterio == "Dividend Yield (maiores)":
        df["DY_num"] = pd.to_numeric(df["DY"], errors="coerce")
        d = df.sort_values("DY_num", ascending=False).head(topn)[["Ativo","DY_num","Preço","Var1D"]].copy()
        d["DY_num"] = d["DY_num"].map(lambda x: "—" if pd.isna(x) else f"{(float(x)*100):.2f}%")
        d["Var1D"] = d["Var1D"].map(lambda x: f"{x:+.2f}%")
        d = d.rename(columns={"DY_num":"Dividend Yield"})
        st.dataframe(d, use_container_width=True, hide_index=True)

    else:
        df["PE_num"] = pd.to_numeric(df["PE"], errors="coerce")
        d = df.sort_values("PE_num", ascending=True).head(topn)[["Ativo","PE_num","Preço","Var1D"]].copy()
        d["PE_num"] = d["PE_num"].map(lambda x: "—" if pd.isna(x) else f"{float(x):.2f}")
        d["Var1D"] = d["Var1D"].map(lambda x: f"{x:+.2f}%")
        d = d.rename(columns={"PE_num":"P/L"})
        st.dataframe(d, use_container_width=True, hide_index=True)


# -------------------------------- ANALISAR --------------------------------
elif page == "🔍 Analisar":
    st.markdown("### 🔍 Analisar Ativo")
    st.caption("Links rápidos + prévia do preço.")

    ticker_raw = st.text_input("Código do ativo", placeholder="Ex: WEGE3, TAEE11, BTC, AAPL...").upper().strip()
    tipo_guess = "Ação/ETF/FII"
    moeda_guess = "BRL"
    if ticker_raw in ("BTC","ETH","SOL","BNB","XRP","DOGE","AVAX","ADA"):
        tipo_guess = "Cripto"
        moeda_guess = "USD"

    ticker_yf = normalize_ticker(ticker_raw, tipo_guess, moeda_guess)

    if ticker_raw:
        # links
        i10 = f"https://investidor10.com.br/acoes/{ticker_raw.lower()}/"
        google = f"https://www.google.com/search?q=cota%C3%A7%C3%A3o+{ticker_raw}"
        auvp_site = "https://analitica.auvp.com.br/"
        auvp_busca = f"https://www.google.com/search?q=site%3Aanalitica.auvp.com.br+{ticker_raw}"

        st.markdown(
            f"""
<div class="bee-card">
  <div class="bee-card-title">Links úteis</div>
  <div style="display:flex; gap:10px; flex-wrap:wrap;">
    <a href="{auvp_site}" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:10px 12px;border-radius:12px;background:#5900b3;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">💜 AUVP (site)</span>
    </a>
    <a href="{auvp_busca}" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:10px 12px;border-radius:12px;background:#2b2f36;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">🔎 AUVP + {ticker_raw}</span>
    </a>
    <a href="{i10}" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:10px 12px;border-radius:12px;background:#002e6e;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">📊 Investidor10</span>
    </a>
    <a href="{google}" target="_blank" style="text-decoration:none;">
      <span style="display:inline-block;padding:10px 12px;border-radius:12px;background:#2b2f36;border:1px solid rgba(255,255,255,0.10);font-weight:950;color:#fff;">🔎 Google</span>
    </a>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.write("")
        if yf is None or not ticker_yf:
            st.info("Sem yfinance ou ticker inválido.")
        else:
            px = yf_last_and_prev_close([ticker_yf])
            if px.empty:
                st.info("Não consegui puxar preço agora.")
            else:
                last = float(px["last"].iloc[0])
                var = float(px["var_pct"].iloc[0])

                if ticker_yf.endswith("-USD"):
                    st.metric("Preço", f"US$ {last:,.2f}", f"{var:+.2f}%")
                elif ticker_yf.endswith(".SA"):
                    st.metric("Preço", f"R$ {last:,.2f}", f"{var:+.2f}%")
                else:
                    st.metric("Preço", f"{last:,.2f}", f"{var:+.2f}%")


# -------------------------------- CARTEIRA --------------------------------
elif page == "💼 Carteira":
    st.markdown("### 💼 Carteira")
    st.caption("Salva no seu PC (não some).")

    df = carregar_carteira()

    with st.expander("➕ Adicionar ativo", expanded=False):
        a1, a2, a3 = st.columns([2, 1, 1])
        with a1:
            tipo = st.selectbox("Tipo", ["Ação/ETF/FII", "Cripto", "Renda Fixa"])
            ativo = st.text_input("Código (ex: WEGE3, TAEE11, BTC, AAPL)").upper().strip()
            nome = st.text_input("Nome (opcional)", value="")
        with a2:
            moeda = st.selectbox("Moeda", ["BRL", "USD"])
            qtd = st.number_input("Qtd / Valor", min_value=0.0, step=0.01)
        with a3:
            preco_m = st.number_input("Preço médio (opcional)", min_value=0.0, step=0.01)
            obs = st.text_input("Obs (opcional)", value="")
            st.write("")
            if st.button("Salvar ativo"):
                if ativo and qtd > 0:
                    novo = {
                        "Tipo": tipo,
                        "Ativo": ativo,
                        "Nome": nome if nome else ativo,
                        "Qtd": float(qtd),
                        "Preco_Medio": float(preco_m),
                        "Moeda": moeda,
                        "Obs": obs,
                    }
                    df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                    salvar_carteira(df)
                    st.success("Salvo!")
                    st.rerun()
                else:
                    st.error("Preencha o código e uma quantidade/valor > 0.")

    if df.empty:
        st.info("Carteira vazia.")
        st.stop()

    with st.spinner("Atualizando preços..."):
        df_calc, kpi = atualizar_precos_carteira(df)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Patrimônio (R$)", f"{kpi['total_brl']:,.2f}")
    with c2:
        st.metric("PnL (com PM)", f"{kpi['pnl_brl']:,.2f}", f"{kpi['pnl_pct']:+.2f}%")
    with c3:
        st.metric("USD/BRL", f"{kpi['usdbrl']:.2f}")

    st.write("")
    view_cols = ["Tipo","Ativo","Nome","Moeda","Qtd","Preco_Medio","Preco_Atual_BRL","Var_1D","Total_BRL","PnL_BRL","PnL_Pct","Obs"]
    view_cols = [c for c in view_cols if c in df_calc.columns]
    out = df_calc[view_cols].copy()

    # formatar algumas colunas para visual
    for col in ["Preco_Medio","Preco_Atual_BRL","Total_BRL","PnL_BRL"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    st.dataframe(out, use_container_width=True, hide_index=True)

    st.write("")
    st.markdown("#### ✍️ Editar e salvar (avançado)")
    edited = st.data_editor(df_calc[CARTEIRA_COLS], num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar tabela editada"):
        salvar_carteira(edited)
        st.success("Salvo!")
        st.rerun()


# -------------------------------- CALCULADORAS --------------------------------
elif page == "🧮 Calculadoras":
    st.markdown("### 🧮 Calculadoras")

    modo = st.radio(
        "Ferramenta",
        ["📈 Juros Compostos", "🏦 Renda Fixa (simples)", "🔥 FIRE", "💰 Meta do Milhão", "🏠 Alugar x Financiar"],
        horizontal=True,
    )
    st.write("---")

    # 1) Juros Compostos
    if modo == "📈 Juros Compostos":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            vp = st.number_input("Valor inicial (R$)", 0.0, step=100.0, value=1000.0)
        with c2:
            pmt = st.number_input("Aporte mensal (R$)", 0.0, step=100.0, value=500.0)
        with c3:
            i = st.number_input("Taxa anual (%)", 0.0, step=0.1, value=10.0)
        with c4:
            anos = st.number_input("Anos", 1, 60, value=10)

        if st.button("Calcular"):
            r = (i / 100.0) / 12.0
            n = int(anos * 12)
            if r == 0:
                vf = vp + pmt * n
            else:
                vf = vp * (1 + r) ** n + pmt * (((1 + r) ** n - 1) / r)
            st.success(f"Total estimado: **{fmt_money_brl(vf)}**")

    # 2) Renda fixa simples
    elif modo == "🏦 Renda Fixa (simples)":
        c1, c2, c3 = st.columns(3)
        with c1:
            valor = st.number_input("Valor aplicado (R$)", 0.0, step=100.0, value=10000.0)
        with c2:
            taxa = st.number_input("Taxa anual (%)", 0.0, step=0.1, value=12.0)
        with c3:
            meses = st.number_input("Meses", 1, 360, value=12)

        if st.button("Calcular"):
            r = (taxa / 100.0) / 12.0
            vf = valor * (1 + r) ** meses
            ganho = vf - valor
            st.success(f"Montante: **{fmt_money_brl(vf)}** • Ganho: **{fmt_money_brl(ganho)}**")

    # 3) FIRE (explicado)
    elif modo == "🔥 FIRE":
        st.caption("FIRE = independência financeira. Aqui é uma estimativa simples: quanto você precisa para sustentar seu gasto mensal.")
        c1, c2, c3 = st.columns(3)
        with c1:
            gasto = st.number_input("Gasto mensal (R$)", 0.0, step=100.0, value=8000.0)
        with c2:
            taxa_segura = st.number_input("Taxa segura (% a.a.)", 0.1, step=0.1, value=4.0)
        with c3:
            inflacao = st.number_input("Retorno real (% a.a.)", 0.1, step=0.1, value=6.0)

        if st.button("Calcular FIRE"):
            # alvo = gasto anual / taxa segura
            gasto_anual = gasto * 12.0
            alvo = gasto_anual / (taxa_segura / 100.0)
            st.success(f"Patrimônio-alvo estimado (FIRE): **{fmt_money_brl(alvo)}**")
            st.info("Interpretação: com esse patrimônio, uma retirada de ~taxa segura/ano tende a sustentar seu padrão (estimativa).")

    # 4) Meta do Milhão
    elif modo == "💰 Meta do Milhão":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            atual = st.number_input("Patrimônio atual (R$)", 0.0, step=1000.0, value=0.0)
        with c2:
            aporte = st.number_input("Aporte mensal (R$)", 0.0, step=100.0, value=1000.0)
        with c3:
            taxa = st.number_input("Rentabilidade anual (%)", 0.0, step=0.1, value=10.0)
        with c4:
            meta = st.number_input("Meta (R$)", 0.0, step=10000.0, value=1000000.0)

        if st.button("Calcular tempo"):
            r = (taxa / 100.0) / 12.0
            bal = atual
            m = 0
            while bal < meta and m < 2400:
                bal = bal * (1 + r) + aporte
                m += 1
            if m >= 2400:
                st.warning("Ficou muito longo (200 anos). Ajuste taxa/aporte.")
            else:
                anos = m // 12
                meses = m % 12
                st.success(f"Tempo estimado: **{anos} anos e {meses} meses**")

    # 5) Alugar x Financiar (com crédito)
    else:
        st.caption("Comparação estimativa. Útil pra ter noção (não é recomendação financeira).")

        col1, col2, col3 = st.columns(3)
        with col1:
            valor_imovel = st.number_input("Valor do imóvel (R$)", 0.0, step=10000.0, value=500000.0)
            valoriz = st.number_input("Valorização anual do imóvel (%)", 0.0, step=0.1, value=4.0)
            igpm = st.number_input("IGPM anual do aluguel (%)", 0.0, step=0.1, value=5.0)
        with col2:
            aluguel = st.number_input("Valor do aluguel (R$/mês)", 0.0, step=100.0, value=2000.0)
            entrada = st.number_input("Entrada (R$)", 0.0, step=10000.0, value=150000.0)
            custos = st.number_input("Custos do financiamento (R$)", 0.0, step=1000.0, value=30000.0)
        with col3:
            prazo_meses = st.number_input("Prazo (meses)", 1, 480, value=360)
            taxa_fin = st.number_input("Taxa anual do financiamento (%)", 0.0, step=0.1, value=10.0)
            retorno_inv = st.number_input("Rentabilidade anual investimento (%)", 0.0, step=0.1, value=11.0)

        def annuity_payment(pv: float, annual_rate_pct: float, n_months: int) -> float:
            if n_months <= 0:
                return 0.0
            r = (annual_rate_pct / 100.0) / 12.0
            if r == 0:
                return pv / n_months
            return pv * (r * (1 + r) ** n_months) / ((1 + r) ** n_months - 1)

        if st.button("Calcular"):
            # FINANCIAR:
            pv = max(valor_imovel - entrada, 0.0)
            parcela = annuity_payment(pv, taxa_fin, int(prazo_meses))
            # custo total aproximado (parcelas + entrada + custos)
            total_pago = parcela * prazo_meses + entrada + custos

            # valor futuro do imóvel (valorização)
            r_im = (valoriz / 100.0) / 12.0
            vf_imovel = valor_imovel * (1 + r_im) ** prazo_meses

            # ALUGAR:
            r_inv = (retorno_inv / 100.0) / 12.0
            # investe entrada + custos (em vez de pagar no começo)
            bal = entrada + custos
            aluguel_atual = aluguel
            r_igpm = (igpm / 100.0) / 12.0

            for m in range(int(prazo_meses)):
                # investir e pagar aluguel
                bal = bal * (1 + r_inv)
                bal = bal - aluguel_atual
                # reajuste aluguel
                aluguel_atual = aluguel_atual * (1 + r_igpm)

            # Também considera que quem financia paga "parcela" — diferença parcela vs aluguel vira investimento no cenário aluguel
            # (aproximação)
            bal2 = entrada + custos
            aluguel_atual = aluguel
            for m in range(int(prazo_meses)):
                bal2 = bal2 * (1 + r_inv)
                diff = max(parcela - aluguel_atual, 0.0)
                bal2 = bal2 + diff
                aluguel_atual = aluguel_atual * (1 + r_igpm)

            st.markdown("#### Resultado (estimativo)")
            a, b, c = st.columns(3)
            with a:
                st.metric("Parcela (aprox.)", fmt_money_brl(parcela))
            with b:
                st.metric("Total pago no financiamento", fmt_money_brl(total_pago))
            with c:
                st.metric("Valor futuro do imóvel", fmt_money_brl(vf_imovel))

            st.write("")
            st.markdown("#### Se você ALUGAR + INVESTIR (estimativa)")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Saldo investido (entrada+custos - aluguel)", fmt_money_brl(bal))
            with c2:
                st.metric("Saldo investido (investindo diferença parcela-aluguel)", fmt_money_brl(bal2))

            st.info(
                "Leitura: se o saldo investido ficar muito maior que a vantagem do imóvel, alugar tende a fazer mais sentido financeiramente — "
                "mas depende MUITO das premissas."
            )

        st.write("")
        st.caption("* Calculadora inspirada no conteúdo/idéia popularizada por Raul Sena (Investidor Sardinha). Crédito ao autor do método/tema. Implementação aqui é uma versão simplificada.")


# -------------------------------- NEWS --------------------------------
elif page == "📰 News":
    st.markdown("### 📰 Notícias do mercado")
    tema = st.selectbox(
        "Tema",
        ["economia brasil investimentos", "ibovespa bolsa ações", "selic juros copom", "bitcoin ethereum cripto", "dólar câmbio", "imóveis financiamento"],
    )
    q = tema.replace(" ", "+")
    items = get_google_news_items(q, limit=12)

    if not items:
        st.info("Sem notícias agora.")
    else:
        for it in items:
            ago = human_time_ago(it["published_dt"]) if it.get("published_dt") else ""
            meta = f"{it.get('source','')} • {ago}".strip(" •")
            st.markdown(
                f"""
<a class="news-item" href="{it['link']}" target="_blank">
  <div class="news-title">{it['title']}</div>
  <div class="news-meta">{meta}</div>
</a>
""",
                unsafe_allow_html=True,
            )


# -------------------------------- BEE TV --------------------------------
elif page == "🍿 Bee TV":
    st.markdown("### 🍿 Bee TV")
    st.caption("Puxa RSS do YouTube. Se bloquear, usa fallback (abre canal direto).")

    c1, c2 = st.columns([1, 1])
    with c1:
        qtd = st.slider("Quantos canais", 4, 10, 6)
    with c2:
        st.write("")
        if st.button("🎲 Sortear"):
            try:
                buscar_videos_aleatorios.clear()
                buscar_videos_rss.clear()
            except Exception:
                st.cache_data.clear()
            st.rerun()

    videos, modo = buscar_videos_aleatorios(n_canais=qtd)
    if modo == "fallback":
        st.warning("RSS falhou nessa rede. Mostrando fallback (canal).")

    cols = st.columns(3)
    for i, v in enumerate(videos):
        thumb = v["thumb"] or "https://i.imgur.com/8ZQZQZQ.png"
        ago = human_time_ago(v["published_dt"]) if v.get("published_dt") else "abrir no YouTube"
        with cols[i % 3]:
            st.markdown(
                f"""
<a href="{v['link']}" target="_blank" class="video-card">
  <img src="{thumb}" class="video-thumb">
  <div class="video-info">
    <div class="video-channel">{v['canal']}</div>
    <div class="video-title">{v['titulo']}</div>
    <div class="video-meta">{ago}</div>
  </div>
</a>
""",
                unsafe_allow_html=True,
            )


# -------------------------------- GASTOS --------------------------------
elif page == "📒 Gastos":
    st.markdown("### 📒 Gastos (em breve)")
    st.info("Aqui entra Open Finance + orçamento no futuro (automaticamente).")
    st.caption("Por enquanto, não vamos te obrigar a lançar manualmente — essa é a ideia mesmo: puxar oficial depois.")


# -------------------------------- TUTORIAL --------------------------------
elif page == "📱 Tutorial":
    st.markdown("### 📱 Tutorial: BTG (placeholder)")
    st.caption("Se você colocar imagens em assets/btg1.jpeg, btg2.jpeg, btg3.jpeg eu monto um wizard bonitão.")
    st.info("Quando você quiser, eu deixo o tutorial com animações e passos estilo app.")

else:
    st.info("Página não encontrada.")
