# Bee Finanças — Streamlit App (v27.0 FINAL - LAYOUT FIX)
# Single-file / Portable
# ---------------------------------------------------------------
# requirements.txt:
# streamlit, pandas, yfinance, plotly, feedparser, requests, pillow, deep-translator
# ---------------------------------------------------------------

import os
import math
import warnings
from datetime import datetime, timezone
import urllib.parse

import streamlit as st
import pandas as pd
import feedparser
import requests
from PIL import Image

warnings.filterwarnings("ignore")

APP_VERSION = "v27.0 (FINAL)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")

# --------------------------------------------------------------------------------
# 1) IMPORTS (optional)
# --------------------------------------------------------------------------------
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
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None


# --------------------------------------------------------------------------------
# 2) Helpers
# --------------------------------------------------------------------------------
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
    except Exception:
        return None


def fmt_ptbr_number(x, decimals=2):
    """Formata número em padrão pt-BR: milhar '.' e decimal ','."""
    try:
        if x is None:
            return "—"
        x = float(x)
        s = f"{x:,.{decimals}f}"  # 1,234.56
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,56
        return s
    except Exception:
        return "—"


def fmt_money_brl(x, decimals=2):
    return f"R$ {fmt_ptbr_number(x, decimals)}"


def fmt_money_usd(x, decimals=0):
    return f"$ {fmt_ptbr_number(x, decimals)}".replace("$ ", "US$ ")


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
    except Exception:
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
    try:
        if not x:
            return "—"
        x = float(x)
        if x >= 1e12:
            return f"{x / 1e12:.2f} T"
        if x >= 1e9:
            return f"{x / 1e9:.2f} B"
        if x >= 1e6:
            return f"{x / 1e6:.2f} M"
        return f"{x:,.0f}"
    except Exception:
        return "—"


# --------------------------------------------------------------------------------
# 3) Data fetch
# --------------------------------------------------------------------------------
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
                if ("Close", t) in data.columns:
                    s = data[("Close", t)]
                elif (t, "Close") in data.columns:
                    s = data[(t, "Close")]
            else:
                # single ticker
                if "Close" in data.columns:
                    s = data["Close"]

            if s is None:
                continue

            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 2:
                last = float(s.iloc[-1])
                prev = float(s.iloc[-2])
                var_pct = ((last - prev) / prev) * 100 if prev else 0.0
                out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var_pct})
        except Exception:
            pass
    return pd.DataFrame(out)


@st.cache_data(ttl=15)
def binance_24h(symbol: str) -> dict:
    """
    Binance public endpoint: returns lastPrice and priceChangePercent.
    symbol ex: BTCBRL, BTCUSDT
    """
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, params={"symbol": symbol}, timeout=3)
        if r.status_code != 200:
            return {}
        j = r.json()
        return {
            "last": float(j.get("lastPrice", 0) or 0),
            "var_pct": float(j.get("priceChangePercent", 0) or 0),
        }
    except Exception:
        return {}


@st.cache_data(ttl=1200)
def yf_info_extended(ticker: str) -> dict:
    if yf is None or not ticker:
        return {}
    try:
        tk = yf.Ticker(ticker)
        current_price = 0.0
        try:
            if hasattr(tk, "fast_info") and tk.fast_info:
                current_price = float(tk.fast_info.last_price or 0.0)
            else:
                h = tk.history(period="1d")
                if not h.empty:
                    current_price = float(h["Close"].iloc[-1])
        except Exception:
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
            except Exception:
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
    except Exception:
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
    except Exception:
        return None


@st.cache_data(ttl=900)
def get_google_news_items(query: str, limit: int = 8) -> list[dict]:
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
                p_dt = dtparser.parse(e.published) if dtparser else datetime.now()
            except Exception:
                p_dt = datetime.now()
            title = getattr(e, "title", "Notícia").rsplit(" - ", 1)[0]
            source = getattr(e, "source", {}).get("title") or "News"
            items.append({"title": title, "link": e.link, "source": source, "published_dt": p_dt})
        return items
    except Exception:
        return []


# --------------------------------------------------------------------------------
# 4) Streamlit config + CSS
# --------------------------------------------------------------------------------
logo_img = process_logo_transparency(LOGO_PATH)
page_icon = logo_img if logo_img else "🐝"
st.set_page_config(
    page_title="Bee Finanças",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* --- FUNDO --- */
.stApp{
  background:
    radial-gradient(circle at 15% 15%, rgba(255, 215, 0, 0.05), transparent 35%),
    radial-gradient(circle at 85% 85%, rgba(89, 0, 179, 0.10), transparent 35%),
    #0B0F14;
}
h1, h2, h3, h4{
  color:#FFD700 !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  font-weight: 900;
  letter-spacing:-0.03em;
}

/* --- SIDEBAR --- */
section[data-testid="stSidebar"]{
  background:#090C10;
  border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] img{
  display:block;
  margin: 0 auto 10px auto;
  object-fit:contain;
  max-width:100%;
}
.menu-header{
  font-size:10px;
  text-transform:uppercase;
  color:#444;
  font-weight:900;
  letter-spacing:1px;
  margin-top: 10px;
  margin-bottom: 6px;
  padding-left: 4px;
}

/* reduzir espaçamento geral no sidebar */
div[data-testid="stSidebarUserContent"] .stButton{ margin-bottom: 4px !important; }
div[data-testid="stVerticalBlock"] { gap: 0.18rem !important; }

/* NAV BUTTONS compactos */
.navbtn button{
  width:100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.035) 0%, rgba(255,255,255,0.015) 100%) !important;
  color:#CFCFCF !important;
  border:1px solid rgba(255,255,255,0.06) !important;
  border-radius:10px !important;
  padding: 0.40rem 0.8rem !important;
  margin: 0px !important;
  font-weight:800 !important;
  font-size: 13px !important;
  text-align:left !important;
  transition: all .15s ease;
  height: 38px !important;
  display:flex !important;
  align-items:center !important;
}
.navbtn button:hover{
  background: linear-gradient(90deg, rgba(255,215,0,0.10) 0%, rgba(255,215,0,0.03) 100%) !important;
  border-left: 3px solid #FFD700 !important;
  transform: translateX(2px);
}

/* CARDS */
.bee-card{
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(4px);
}
.card-title{
  color:#FFD700;
  font-weight:900;
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:1px;
  margin-bottom: 6px;
}
.kpi{
  color:#fff;
  font-weight: 900;
  font-size: 24px;
  line-height: 1.05;
}
.sub{
  color:#7A7A7A;
  font-size:12px;
  margin-top: 6px;
}

/* KPI compact */
.kpi-compact .kpi{ font-size: 22px !important; }
.kpi-small .kpi{ font-size: 20px !important; }

/* NEWS CARDS */
a.news-card-link{ text-decoration:none; display:block; margin-bottom:10px; }
.news-card-box{
  background:#141A22;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 14px 14px;
  transition: all .15s ease;
}
.news-card-box:hover{
  border-color:#FFD700;
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(0,0,0,0.25);
}
.nc-title{
  color:#fff;
  font-weight: 900;
  font-size: 14px;
  line-height: 1.35;
  margin-bottom: 6px;
}
.nc-meta{
  color:#9A9A9A;
  font-size: 12px;
  display:flex;
  gap:8px;
  align-items:center;
}
.nc-badge{
  background: rgba(255,215,0,0.14);
  color:#FFD700;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

/* MARKET MONITOR */
.ticker-pill{
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
  padding: 8px 10px;
  margin-bottom: 6px;
  display:flex;
  justify-content: space-between;
  align-items:center;
  border-left: 3px solid #555;
}
.tp-up{ border-left-color:#00C805; }
.tp-down{ border-left-color:#FF3B30; }
.tp-name{ font-weight:900; font-size:12px; color:#D7D7D7; }
.tp-price{ font-weight:900; font-size:12px; color:#FFF; }
.tp-pct{ font-size:11px; font-weight:900; }

/* INPUTS */
.stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input{
  background:#12171E !important;
  color:#fff !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
}

/* botão amarelo */
.yellowbtn button{
  background:#FFD700 !important;
  color:#000 !important;
  border:none !important;
  font-weight: 900 !important;
  border-radius: 12px !important;
}
.yellowbtn button:hover{
  transform: translateY(-1px);
  box-shadow: 0 10px 25px rgba(255,215,0,0.22);
}

/* footer */
.bee-footer{
  margin-top: 18px;
  opacity: .55;
  font-size: 12px;
  display:flex;
  justify-content: space-between;
}
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------
# 5) Data model
# --------------------------------------------------------------------------------
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


def smart_load_csv(uploaded_file, sep_priority=","):
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=sep_priority)
        if len(df.columns) > 1:
            return df
    except Exception:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";" if sep_priority == "," else ",")
        if len(df.columns) > 1:
            return df
    except Exception:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
        return df
    except Exception:
        pass
    return None


def atualizar_precos_carteira_memory(df):
    df = df.copy()
    if df.empty:
        return df, {"total_brl": 0, "pnl_brl": 0, "pnl_pct": 0}

    # câmbio via yahoo (fallback simples)
    usdbrl = 5.80
    if yf is not None:
        try:
            fx = yf_last_and_prev_close(["BRL=X"])
            if not fx.empty:
                usdbrl = float(fx.iloc[0]["last"])
        except Exception:
            pass

    df["Ticker_YF"] = df.apply(
        lambda r: normalize_ticker(str(r["Ativo"]), "Ação", str(r.get("Moeda", "BRL")).upper()),
        axis=1,
    )

    df["Preco_Atual"] = 0.0
    is_rf = df["Tipo"].astype(str).str.contains("Renda Fixa|RF", case=False, na=False)
    df.loc[is_rf, "Preco_Atual"] = df.loc[is_rf, "Preco_Medio"]

    tickers = df.loc[~is_rf, "Ticker_YF"].unique().tolist()
    px_map = {}
    if tickers and yf is not None:
        px_df = yf_last_and_prev_close(tickers)
        for _, r in px_df.iterrows():
            px_map[r["ticker"]] = float(r["last"])

    for i, row in df.iterrows():
        if bool(is_rf.iloc[i]):
            continue
        df.at[i, "Preco_Atual"] = float(px_map.get(row["Ticker_YF"], 0.0))

    for c in ["Qtd", "Preco_Medio"]:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
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

    total = float(df["Total_BRL"].sum())
    pnl = float(df["PnL_BRL"].sum())
    custo = float(df["Custo_BRL"].sum())
    pnl_pct = (pnl / custo * 100) if custo > 0 else 0.0

    return df, {"total_brl": total, "pnl_brl": pnl, "pnl_pct": pnl_pct}


# --------------------------------------------------------------------------------
# 6) UI helpers
# --------------------------------------------------------------------------------
def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def kpi_card(title, value, sub="", color=None, compact=False, small=False):
    extra = ""
    if compact:
        extra = "kpi-compact"
    if small:
        extra = "kpi-small"
    st.markdown(
        f"""
<div class="bee-card {extra}" style="{f'border-top: 3px solid {color};' if color else ''}">
  <div class="card-title">{title}</div>
  <div class="kpi">{value}</div>
  <div class="sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def investidor10_link(ativo: str) -> str:
    # melhor esforço: tenta ações / fiis / etfs
    a = (ativo or "").strip().upper().replace(".SA", "")
    # ações BR: normalmente tem número
    if any(ch.isdigit() for ch in a):
        return f"https://investidor10.com.br/acoes/{a.lower()}/"
    return f"https://investidor10.com.br/"


# --------------------------------------------------------------------------------
# 7) Sidebar
# --------------------------------------------------------------------------------
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

    st.divider()

    # MARKET MONITOR (sem SELIC)
    try:
        st.markdown(
            "<div style='font-size:12px; color:#666; font-weight:900; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>",
            unsafe_allow_html=True,
        )

        # IBOV + USD/BRL via Yahoo
        ibov_val = ibov_pct = None
        usd_val = usd_pct = None
        if yf is not None:
            snap = yf_last_and_prev_close(["^BVSP", "BRL=X"])
            if not snap.empty:
                ib = snap[snap["ticker"] == "^BVSP"]
                fx = snap[snap["ticker"] == "BRL=X"]
                if not ib.empty:
                    ibov_val = float(ib.iloc[0]["last"])
                    ibov_pct = float(ib.iloc[0]["var_pct"])
                if not fx.empty:
                    usd_val = float(fx.iloc[0]["last"])
                    usd_pct = float(fx.iloc[0]["var_pct"])

        # BTC via Binance (mais confiável p/ BRL)
        btcusd = binance_24h("BTCUSDT")
        btcbrl = binance_24h("BTCBRL")


        def pill(name, price_text, pct):
            cor = "tp-up" if (pct is not None and pct >= 0) else "tp-down"
            color = "#00C805" if (pct is not None and pct >= 0) else "#FF3B30"
            pct_txt = f"{pct:+.2f}%" if pct is not None else "—"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>{name}</span>
  <div style='display:flex; align-items:center; gap:10px;'>
    <span class='tp-price'>{price_text}</span>
    <span class='tp-pct' style='color:{color};'>{pct_txt}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )


        if ibov_val is not None:
            pill("IBOV", f"{fmt_ptbr_number(ibov_val, 0)}", ibov_pct)
        else:
            pill("IBOV", "—", None)

        if usd_val is not None:
            pill("USD/BRL", f"{fmt_money_brl(usd_val, 2)}", usd_pct)
        else:
            pill("USD/BRL", "—", None)

        if btcusd:
            pill("BTC (US$)", fmt_money_usd(btcusd["last"], 0), btcusd.get("var_pct"))
        else:
            pill("BTC (US$)", "—", None)

        if btcbrl:
            # compacta (R$ muito grande)
            pill("BTC (R$)", f"R$ {fmt_ptbr_number(btcbrl['last'], 0)}" if btcbrl.get('last') else "—",
                 btcbrl.get("var_pct"))
        else:
            pill("BTC (R$)", "—", None)

    except Exception:
        pass

# --------------------------------------------------------------------------------
# 8) Top bar (Clock + Refresh)
# --------------------------------------------------------------------------------
c_spacer, c_info = st.columns([6, 2.5])

with c_spacer:
    st.write("")  # spacer

with c_info:
    # Cria duas sub-colunas: uma pro relogio (maior) e outra pro botao (menor)
    # gap="small" aproxima os dois elementos
    c_clock, c_btn = st.columns([2.5, 1], gap="small")

    with c_clock:
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        # Visual do relogio estilo "pill" alinhado
        st.markdown(
            f"""
            <div style='
                display: flex; 
                justify-content: center; 
                align-items: center;
                height: 38px;
                border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 8px; 
                color: #BDBDBD; 
                font-size: 13px; 
                background: rgba(255,255,255,0.03);
                font-weight: 600;
            '>
                🕒 {now_str}
            </div>
            """,
            unsafe_allow_html=True
        )

    with c_btn:
        # Botao simples, ocupando a largura da coluninha
        if st.button("↻", key="top_refresh", help="Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.markdown("<hr style='border-color:rgba(255,255,255,0.06); margin-top:10px'>", unsafe_allow_html=True)

page = st.session_state["page"]

# --------------------------------------------------------------------------------
# 9) Pages
# --------------------------------------------------------------------------------
if page == "🏠 Home":
    st.markdown("## 📌 Visão do Mercado")

    # KPIs horizontais
    ibov_val = ibov_pct = None
    usd_val = usd_pct = None
    if yf is not None:
        snap = yf_last_and_prev_close(["^BVSP", "BRL=X"])
        if not snap.empty:
            ib = snap[snap["ticker"] == "^BVSP"]
            fx = snap[snap["ticker"] == "BRL=X"]
            if not ib.empty:
                ibov_val = float(ib.iloc[0]["last"])
                ibov_pct = float(ib.iloc[0]["var_pct"])
            if not fx.empty:
                usd_val = float(fx.iloc[0]["last"])
                usd_pct = float(fx.iloc[0]["var_pct"])

    btcusd = binance_24h("BTCUSDT")
    btcbrl = binance_24h("BTCBRL")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        val = fmt_ptbr_number(ibov_val, 0) if ibov_val is not None else "—"
        sub = f"{ibov_pct:+.2f}% (dia)" if ibov_pct is not None else ""
        kpi_card("IBOV", val, sub, color="#FFD700", compact=True)
    with c2:
        val = fmt_money_brl(usd_val, 2) if usd_val is not None else "—"
        sub = f"{usd_pct:+.2f}% (dia)" if usd_pct is not None else ""
        kpi_card("USD/BRL", val, sub, color="#FFD700", compact=True)
    with c3:
        if btcusd:
            val = fmt_money_usd(btcusd["last"], 0)
            sub = f"{btcusd.get('var_pct', 0):+.2f}% (24h)"
        else:
            val, sub = "—", ""
        kpi_card("BTC (US$)", val, sub, color="#FFD700", compact=True)
    with c4:
        if btcbrl:
            # muito grande -> small
            val = f"R$ {fmt_ptbr_number(btcbrl['last'], 0)}"
            sub = f"{btcbrl.get('var_pct', 0):+.2f}% (24h)"
        else:
            val, sub = "—", ""
        kpi_card("BTC (R$)", val, sub, color="#FFD700", small=True)

    st.write("")
    st.markdown("### ⚡ Acesso Rápido")

    # label não pode ser vazio: coloca "Ticker" e esconde
    quick_ticker = st.text_input(
        "Ticker",
        placeholder="Ex: PETR4, VALE3, IVVB11...",
        label_visibility="collapsed",
    ).upper().strip()

    if quick_ticker:
        tk_norm = normalize_ticker(quick_ticker, "Ação", "BRL")
        c_info, c_btn = st.columns([3, 1])
        with c_info:
            if yf is not None:
                hist = yf_last_and_prev_close([tk_norm])
                if not hist.empty:
                    last = float(hist.iloc[0]["last"])
                    var = float(hist.iloc[0]["var_pct"])
                    cor_txt = "#00C805" if var >= 0 else "#FF3B30"
                    st.markdown(
                        f"""
<div style="margin-top:6px; margin-bottom:6px;">
  <span style="font-size:26px; font-weight:900; color:#fff;">{tk_norm.replace('.SA', '')}</span>
  <span style="font-size:22px; font-weight:900; color:{cor_txt}; margin-left:10px;">{fmt_ptbr_number(last, 2)} ({var:+.2f}%)</span>
</div>
""",
                        unsafe_allow_html=True,
                    )
        with c_btn:
            link = investidor10_link(quick_ticker)
            st.link_button("Abrir no Investidor10", link, use_container_width=True)

        if px is not None and yf is not None:
            try:
                chart_data = yf.Ticker(tk_norm).history(period="1mo")
                if not chart_data.empty:
                    fig_mini = px.line(chart_data, y="Close")
                    fig_mini.update_layout(
                        xaxis_visible=False,
                        yaxis_visible=False,
                        margin=dict(l=0, r=0, t=5, b=5),
                        height=70,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_mini, use_container_width=True, config={"displayModeBar": False})
            except Exception:
                pass

    st.write("")
    st.markdown("### 📰 Notícias")
    news = get_google_news_items("investimentos brasil", limit=6)
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
        st.info("Sem notícias agora.")

elif page == "📰 Notícias":
    st.markdown("## 📰 Notícias")
    q = st.text_input("Buscar", value="investimentos brasil", label_visibility="collapsed")
    items = get_google_news_items(q, limit=12)
    if items:
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
    else:
        st.info("Sem notícias agora.")

elif page == "🔍 Analisar":
    st.markdown("## 🔍 Analisar")
    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input("Ativo", placeholder="WEGE3 / PETR4 / IVVB11 / AAPL",
                               label_visibility="collapsed").upper().strip()
    with c_p:
        periodo = st.selectbox("Zoom", ["1mo", "6mo", "1y", "5y", "max"], index=2)

    if ticker:
        tk_real = normalize_ticker(ticker, "Ação", "BRL")
        info = yf_info_extended(tk_real)
        if info:
            st.markdown(f"### {info.get('longName', ticker)}")

            m1, m2, m3, m4 = st.columns(4)
            cur_price = info.get("currentPrice", 0.0)

            with m1:
                st.metric("Preço", fmt_money_brl(cur_price, 2) if cur_price else "—")

            val_dy = info.get("dividendYield")
            with m2:
                if val_dy and val_dy < 2:
                    st.metric("DY", f"{val_dy * 100:.2f}%")
                elif val_dy:
                    st.metric("DY", f"{val_dy:.2f}%")
                else:
                    st.metric("DY", "—")

            val_pe = info.get("trailingPE")
            with m3:
                st.metric("P/L", f"{val_pe:.2f}" if val_pe else "—")

            with m4:
                st.metric("Market Cap", format_market_cap(info.get("marketCap")))

            st.markdown("---")
            fig = get_stock_history_plot(tk_real, period=periodo)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Sem gráfico.")

            with st.expander("Resumo (PT-BR)"):
                st.write(info.get("summary", "—"))
        else:
            st.error("Ativo não encontrado.")

elif page == "💼 Carteira":
    st.markdown("## 💼 Carteira (Cofre Local)")
    wallet_active = (not st.session_state["carteira_df"].empty) or st.session_state["wallet_mode"]

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("Carregar minha_carteira.csv", type=["csv"], key="uploader_start")
            if uploaded_file:
                df_loaded = smart_load_csv(uploaded_file)
                if df_loaded is not None:
                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            st.success("Começar do zero")
            if st.button("Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                st.rerun()
    else:
        df = st.session_state["carteira_df"]

        with st.expander("➕ Adicionar Ativo", expanded=True):
            f1, f2, f3 = st.columns([1, 1, 1])
            with f1:
                tipo = st.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa"])
                ativo = st.text_input("Ticker/Nome", label_visibility="collapsed",
                                      placeholder="Ex: ABEV3 / IVVB11 / BTC").upper().strip()
            with f2:
                qtd = st.number_input("Qtd", min_value=0.0, step=0.01)
                preco = st.number_input("Preço Médio", min_value=0.0, step=0.01)
            with f3:
                moeda = st.selectbox("Moeda", ["BRL", "USD"])
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<div class='yellowbtn'>", unsafe_allow_html=True)
                add = st.button("Adicionar", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if add:
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

        with st.expander("🗑️ Remover", expanded=False):
            if not df.empty:
                ativos_disponiveis = df["Ativo"].unique().tolist()
                ativo_rm = st.selectbox("Selecione", ativos_disponiveis)
                if st.button(f"Excluir {ativo_rm}"):
                    df = df[df["Ativo"] != ativo_rm]
                    st.session_state["carteira_df"] = df
                    st.rerun()

        if not df.empty:
            with st.spinner("Atualizando preços..."):
                df_calc, kpi = atualizar_precos_carteira_memory(df)

            k1, k2, k3 = st.columns(3)
            with k1:
                kpi_card("TOTAL", fmt_money_brl(kpi["total_brl"], 2), "Patrimônio", compact=True)
            with k2:
                color = "#00C805" if kpi["pnl_brl"] >= 0 else "#FF3B30"
                kpi_card("RESULTADO", fmt_money_brl(kpi["pnl_brl"], 2), f"{kpi['pnl_pct']:+.2f}%", color=color,
                         compact=True)
            with k3:
                kpi_card("ATIVOS", f"{len(df_calc)}", "Diversificação", compact=True)

            st.write("")
            show_df = df_calc[["Tipo", "Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "Total_BRL", "PnL_Pct"]].copy()

            st.dataframe(
                show_df.style.format(
                    {
                        "Qtd": "{:.4f}",
                        "Preco_Medio": "R$ {:.2f}",
                        "Preco_Atual_BRL": "R$ {:.2f}",
                        "Total_BRL": "R$ {:.2f}",
                        "PnL_Pct": "{:+.2f}%",
                    }
                ),
                use_container_width=True,
                height=420,
            )

        st.write("---")
        st.download_button(
            "⬇️ Baixar CSV",
            df.to_csv(index=False).encode("utf-8"),
            "minha_carteira.csv",
            "text/csv",
            type="primary",
        )
        if st.button("Sair"):
            st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
            st.session_state["wallet_mode"] = False
            st.rerun()

elif page == "💸 Controle":
    st.markdown("## 💸 Controle de Gastos")
    gastos_active = (not st.session_state["gastos_df"].empty) or st.session_state["gastos_mode"]

    if not gastos_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_gastos = st.file_uploader("Carregar meus_gastos.csv", type=["csv"], key="uploader_gastos")
            if uploaded_gastos:
                df_g = smart_load_csv(uploaded_gastos)
                if df_g is not None:
                    st.session_state["gastos_df"] = df_g
                    st.session_state["gastos_mode"] = True
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            if st.button("Criar Planilha de Gastos", use_container_width=True):
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
        idx_mes = meses_disp.index(mes_atual_str) if mes_atual_str in meses_disp else (len(meses_disp) - 1)

        col_sel, _ = st.columns([1, 3])
        with col_sel:
            mes_selecionado = st.selectbox("Mês", meses_disp, index=idx_mes)

        mask_mes = df_g["Data"].dt.strftime("%Y-%m") == mes_selecionado
        df_filtered = df_g[mask_mes]

        total_ent = float(df_filtered[df_filtered["Tipo"] == "Entrada"]["Valor"].sum())
        total_sai = float(df_filtered[df_filtered["Tipo"] == "Saída"]["Valor"].sum())
        saldo = total_ent - total_sai

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Receitas", fmt_money_brl(total_ent, 2))
        with k2:
            st.metric("Despesas", fmt_money_brl(total_sai, 2))
        with k3:
            st.metric("Saldo", fmt_money_brl(saldo, 2))

        st.write("---")

        with st.expander("➕ Nova Transação", expanded=True):
            with st.form("form_gastos", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                d_data = c1.date_input("Data", value=today)
                default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Outros"]
                existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
                all_cats = sorted(list(set(default_cats + existing_cats)))
                all_cats.append("➕ Nova (Digitar abaixo)")

                d_cat_select = c2.selectbox("Categoria", all_cats)
                d_cat_input = c2.text_input("Nova Categoria", placeholder="Ex: Pet")
                d_desc = c3.text_input("Descrição", placeholder="Ex: Supermercado")
                d_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"])

                c5, c6 = st.columns(2)
                d_val = c5.number_input("Valor (R$)", min_value=0.0, step=10.0)
                d_pag = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])

                if st.form_submit_button("Salvar"):
                    final_cat = d_cat_input if (
                                d_cat_select == "➕ Nova (Digitar abaixo)" and d_cat_input) else d_cat_select
                    if final_cat == "➕ Nova (Digitar abaixo)":
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

        c_chart, c_table = st.columns([1, 2])
        with c_chart:
            if px is not None and (not df_filtered.empty) and total_sai > 0:
                df_pie = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
                fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.6)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=260, paper_bgcolor="rgba(0,0,0,0)",
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            elif df_filtered.empty:
                st.info("Sem dados no mês.")

        with c_table:
            st.markdown("##### Extrato")
            df_g_edited = st.data_editor(
                df_g,
                num_rows="dynamic",
                column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                },
                use_container_width=True,
                height=340,
            )
            if st.button("Salvar alterações"):
                st.session_state["gastos_df"] = df_g_edited
                st.rerun()

        st.write("---")
        st.download_button(
            "⬇️ Baixar meus_gastos.csv",
            df_g.to_csv(index=False).encode("utf-8"),
            "meus_gastos.csv",
            "text/csv",
            type="primary",
        )
        if st.button("Sair"):
            st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
            st.session_state["gastos_mode"] = False
            st.rerun()

elif page == "🧮 Calculadoras":
    st.markdown("## 🧮 Calculadoras")
    tabs = st.tabs(["Juros", "Alugar/Financiar", "Milhão", "Renda Fixa"])

    with tabs[0]:
        vp = st.number_input("Valor inicial", 1000.0)
        pmt = st.number_input("Aporte mensal", 500.0)
        taxa = st.number_input("Taxa anual (%)", 10.0)
        anos = st.slider("Anos", 1, 50, 10)
        if st.button("Calcular"):
            r = (taxa / 100) / 12
            n = anos * 12
            total = vp * (1 + r) ** n + pmt * (((1 + r) ** n - 1) / r) if r > 0 else vp + pmt * n
            st.success(f"Total: {fmt_money_brl(total, 2)}")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            valor_imovel = st.number_input("Valor do imóvel", 500000.0)
            aluguel = st.number_input("Aluguel mensal", 2500.0)
        with c2:
            taxa_fin = st.number_input("Taxa financiamento (% a.a.)", 9.5)
            taxa_inv = st.number_input("Rentabilidade invest (% a.a.)", 11.0)

        if st.button("Simular"):
            custo_fin = valor_imovel * (1 + (taxa_fin / 100) * 1.5)
            pot_inv = (valor_imovel * 0.20) * (1 + (taxa_inv / 100)) ** 30
            st.warning(f"Custo financiamento (estimado): {fmt_money_brl(custo_fin, 2)}")
            st.success(f"Potencial investindo 20% por 30 anos: {fmt_money_brl(pot_inv, 2)}")

    with tabs[2]:
        c1, c2 = st.columns(2)
        invest_mensal = c1.number_input("Aporte mensal", 2000.0)
        taxa_anual = c2.number_input("Rentabilidade anual (%)", 10.0)
        if st.button("Tempo p/ 1 milhão"):
            r = (taxa_anual / 100) / 12
            if invest_mensal <= 0 or r <= 0:
                st.info("Informe aporte e taxa > 0.")
            else:
                n = math.log((1_000_000 * r) / invest_mensal + 1) / math.log(1 + r)
                st.success(f"Tempo: {n / 12:.1f} anos")

    with tabs[3]:
        val = st.number_input("Valor (R$)", 1000.0)
        cdi = st.number_input("CDI (% a.a.)", 13.0)
        if st.button("Retorno 1 ano"):
            total = val * (1 + cdi / 100)
            st.info(f"1 ano: {fmt_money_brl(total, 2)}")

# --------------------------------------------------------------------------------
# 10) Footer (versão)
# --------------------------------------------------------------------------------
st.markdown(
    f"""
<div class="bee-footer">
  <div>Bee Finanças</div>
  <div>{APP_VERSION}</div>
</div>
""",
    unsafe_allow_html=True,
)