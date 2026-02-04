# Bee Finanças — Streamlit App (v33.0 FINAL - MULTI-USER & DB)
# Single-file / Portable / Login System included
# ---------------------------------------------------------------
# requirements.txt:
# streamlit, pandas, yfinance, plotly, feedparser, requests, pillow, deep-translator
# ---------------------------------------------------------------

import os
import math
import warnings
import sqlite3
import hashlib
import json
from datetime import datetime, timezone, timedelta
import urllib.parse

import streamlit as st
import pandas as pd
import feedparser
import requests
from PIL import Image

warnings.filterwarnings("ignore")

APP_VERSION = "v33.0 (MULTI-USER DB)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpeg")
DB_FILE = "bee_database.db"

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
# 2) DATABASE & AUTH HELPERS
# --------------------------------------------------------------------------------
def init_db():
    """Inicializa o banco de dados SQLite local."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabela de usuários
    c.execute('''
              CREATE TABLE IF NOT EXISTS users
              (
                  username
                  TEXT
                  PRIMARY
                  KEY,
                  password
                  TEXT,
                  name
                  TEXT
              )
              ''')
    # Tabela de dados (Carteira e Gastos em JSON para flexibilidade)
    c.execute('''
              CREATE TABLE IF NOT EXISTS user_data
              (
                  username
                  TEXT
                  PRIMARY
                  KEY,
                  carteira_json
                  TEXT,
                  gastos_json
                  TEXT
              )
              ''')
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def create_user(username, password, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)',
                  (username, hash_password(password), name))
        # Cria entrada vazia na tabela de dados
        c.execute('INSERT INTO user_data (username, carteira_json, gastos_json) VALUES (?, ?, ?)',
                  (username, "{}", "{}"))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT name FROM users WHERE username = ? AND password = ?',
              (username, hash_password(password)))
    data = c.fetchone()
    conn.close()
    return data[0] if data else None


def save_user_data_db(username, carteira_df, gastos_df):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Converter DataFrames para JSON string
    c_json = carteira_df.to_json(orient='records', date_format='iso') if not carteira_df.empty else "{}"
    g_json = gastos_df.to_json(orient='records', date_format='iso') if not gastos_df.empty else "{}"

    c.execute('''
              INSERT INTO user_data (username, carteira_json, gastos_json)
              VALUES (?, ?, ?) ON CONFLICT(username) 
        DO
              UPDATE SET carteira_json=excluded.carteira_json, gastos_json=excluded.gastos_json
              ''', (username, c_json, g_json))
    conn.commit()
    conn.close()


def load_user_data_db(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT carteira_json, gastos_json FROM user_data WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()

    c_df = pd.DataFrame(columns=["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"])
    g_df = pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"])

    if data:
        c_json, g_json = data
        try:
            if c_json and c_json != "{}":
                c_df = pd.read_json(c_json, orient='records')
            if g_json and g_json != "{}":
                g_df = pd.read_json(g_json, orient='records')
                # Converter data de volta para datetime
                if "Data" in g_df.columns:
                    g_df["Data"] = pd.to_datetime(g_df["Data"])
        except Exception:
            pass  # Retorna vazio se der erro

    return c_df, g_df


# --------------------------------------------------------------------------------
# 3) VISUAL HELPERS
# --------------------------------------------------------------------------------
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


def fmt_ptbr_number(x, decimals=2):
    try:
        if x is None:
            return "—"
        x = float(x)
        s = f"{x:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
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


def calculate_rsi(data, window=14):
    try:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except:
        return None


# --------------------------------------------------------------------------------
# 4) Data fetch
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

        roe = safe_get(["returnOnEquity"])
        margins = safe_get(["profitMargins"])
        beta = safe_get(["beta"])

        return {
            "currentPrice": current_price,
            "longName": safe_get(["longName", "shortName"], ticker),
            "sector": safe_get(["sector"]),
            "industry": safe_get(["industry"]),
            "summary": summary,
            "trailingPE": safe_get(["trailingPE", "forwardPE"], None),
            "dividendYield": safe_get(["dividendYield"], None),
            "marketCap": safe_get(["marketCap"], None),
            "roe": roe,
            "margins": margins,
            "beta": beta
        }
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def get_stock_history_plot(ticker: str, period="1y"):
    if yf is None or go is None:
        return None, None
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty:
            return None, None

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

        rsi_val = calculate_rsi(df)

        return fig, rsi_val
    except Exception:
        return None, None


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
# DIALOG FUNCTION (CUSTOM METRICS)
# --------------------------------------------------------------------------------
@st.dialog("🔍 Raio-X do Ativo")
def show_asset_details_popup(ativo_selecionado):
    tk_real = normalize_ticker(ativo_selecionado, "Ação", "BRL")

    with st.spinner(f"Carregando dados de {ativo_selecionado}..."):
        info = yf_info_extended(tk_real)
        fig, rsi = get_stock_history_plot(tk_real, period="6mo")

    if info:
        st.markdown(f"### {info.get('longName', ativo_selecionado)}")

        def mini_metric(label, value):
            return f"""
            <div style="text-align:center; background:rgba(255,255,255,0.03); border-radius:8px; padding:8px;">
                <div style="font-size:11px; color:#888; text-transform:uppercase; margin-bottom:4px;">{label}</div>
                <div style="font-size:20px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{value}</div>
            </div>
            """

        m1, m2, m3 = st.columns(3)

        with m1:
            val_fmt = fmt_money_brl(info.get("currentPrice"), 2)
            st.markdown(mini_metric("Preço", val_fmt), unsafe_allow_html=True)

        with m2:
            dy_val = info.get('dividendYield', 0)
            if dy_val is None: dy_val = 0
            fmt_dy = f"{dy_val * 100:.2f}%"
            st.markdown(mini_metric("DY (Yield)", fmt_dy), unsafe_allow_html=True)

        with m3:
            pe_val = info.get('trailingPE', 0)
            if pe_val is None: pe_val = 0
            fmt_pe = f"{pe_val:.2f}"
            st.markdown(mini_metric("P/L", fmt_pe), unsafe_allow_html=True)

        st.markdown("---")

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        if rsi:
            rsi_text = f"{rsi:.1f}"
            if rsi > 70:
                rsi_status = "⚠️ Sobrecomprado"
                rsi_color_code = "#FF3B30"
            elif rsi < 30:
                rsi_status = "💎 Sobrevendido"
                rsi_color_code = "#00C805"
            else:
                rsi_status = "Neutro"
                rsi_color_code = "#FFD700"

            st.markdown(
                f"<div style='text-align:center; padding:10px; border:1px solid #333; border-radius:10px; background:#111; margin-top:10px;'>"
                f"<span style='color:#ccc; font-size:13px'>RSI (14):</span> "
                f"<strong style='color:{rsi_color_code}; font-size:18px'>{rsi_text}</strong><br>"
                f"<span style='font-size:11px; color:#777'>{rsi_status}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.error("Não foi possível carregar os detalhes deste ativo.")


# --------------------------------------------------------------------------------
# 5) Streamlit config + CSS
# --------------------------------------------------------------------------------
logo_img = process_logo_transparency(LOGO_PATH)
page_icon = logo_img if logo_img else "🐝"
st.set_page_config(
    page_title="Bee Finanças",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializar DB
init_db()

# =========================
#  CSS NOVO (BEE THEME)
# =========================
st.markdown(
    """
<style>
/* =========================
   BEE THEME (v32) — CSS ONLY
   Paleta: Amarelo / Preto / Marrom / Branco
   ========================= */

:root{
  --bee-yellow: #FFD700;
  --bee-yellow-soft: rgba(255,215,0,0.12);
  --bee-black: #0B0F14;
  --bee-black-2: #090C10;
  --bee-surface: rgba(255,255,255,0.035);
  --bee-surface-2: rgba(255,255,255,0.02);
  --bee-border: rgba(255,255,255,0.08);
  --bee-border-2: rgba(255,255,255,0.12);
  --bee-white: #FFFFFF;
  --bee-muted: rgba(255,255,255,0.65);
  --bee-muted-2: rgba(255,255,255,0.45);
  --bee-brown: #5D4037;
  --bee-brown-soft: rgba(93,64,55,0.25);
  --bee-good: #00C805;
  --bee-bad: #FF3B30;

  --r-sm: 12px;
  --r-md: 16px;
  --r-lg: 18px;
  --shadow-1: 0 12px 28px rgba(0,0,0,0.35);
  --shadow-2: 0 8px 18px rgba(0,0,0,0.25);
}

/* ====== FUNDO (colmeia sutil) ====== */
.stApp{
  background:
    radial-gradient(circle at 18% 18%, rgba(255,215,0,0.08), transparent 38%),
    radial-gradient(circle at 78% 82%, rgba(93,64,55,0.22), transparent 45%),
    radial-gradient(circle at 55% 35%, rgba(255,255,255,0.03), transparent 40%),
    linear-gradient(30deg, rgba(255,215,0,0.03) 12%, transparent 12.5%, transparent 87%, rgba(255,215,0,0.03) 87.5%, rgba(255,215,0,0.03)),
    linear-gradient(150deg, rgba(255,215,0,0.03) 12%, transparent 12.5%, transparent 87%, rgba(255,215,0,0.03) 87.5%, rgba(255,215,0,0.03)),
    linear-gradient(90deg, rgba(255,215,0,0.02) 2%, transparent 2.5%, transparent 97%, rgba(255,215,0,0.02) 97.5%, rgba(255,215,0,0.02)),
    var(--bee-black);
  background-size: auto, auto, auto, 64px 64px, 64px 64px, 64px 64px, auto;
  background-position: center, center, center, 0 0, 0 0, 0 0, center;
}

/* ====== TIPOGRAFIA ====== */
h1, h2, h3, h4{
  color: var(--bee-yellow) !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  font-weight: 900;
  letter-spacing:-0.03em;
}
p, span, div { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }

div[data-testid="stVerticalBlock"] { gap: 0.40rem !important; }

/* ====== SIDEBAR ====== */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, #07090D 0%, #090C10 55%, #07090D 100%);
  border-right: 1px solid rgba(255,215,0,0.10);
}
section[data-testid="stSidebar"] img{
  display:block;
  margin: 6px auto 10px auto;
  object-fit:contain;
  max-width:100%;
  filter: drop-shadow(0 10px 20px rgba(0,0,0,0.35));
}

.menu-header{
  font-size:10px;
  text-transform:uppercase;
  color: rgba(255,215,0,0.45);
  font-weight: 900;
  letter-spacing:1.1px;
  margin-top: 10px;
  margin-bottom: 6px;
  padding-left: 4px;
}

/* ====== NAV BUTTONS ====== */
.navbtn button{
  width:100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.045) 0%, rgba(255,255,255,0.018) 100%) !important;
  color: rgba(255,255,255,0.78) !important;
  border:1px solid rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  padding: 0.42rem 0.85rem !important;
  font-weight: 900 !important;
  font-size: 13px !important;
  text-align:left !important;
  transition: all .14s ease;
  height: 40px !important;
  display:flex !important;
  align-items:center !important;
  box-shadow: 0 8px 18px rgba(0,0,0,0.20);
}
.navbtn button:hover{
  background: linear-gradient(90deg, rgba(255,215,0,0.14) 0%, rgba(93,64,55,0.16) 100%) !important;
  border-color: rgba(255,215,0,0.35) !important;
  transform: translateX(3px);
}
.navbtn button:focus{ outline: none !important; }

/* ====== DIVIDER / HR ====== */
hr, .stDivider{
  border-color: rgba(255,255,255,0.08) !important;
}

/* ====== CARDS (bee-card) ====== */
.bee-card{
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-2);
  position: relative;
  overflow: hidden;
}
.bee-card::before{
  content:"";
  position:absolute;
  inset:-2px;
  background: radial-gradient(circle at 20% 0%, rgba(255,215,0,0.16), transparent 40%),
              radial-gradient(circle at 90% 100%, rgba(93,64,55,0.22), transparent 42%);
  opacity: .55;
  pointer-events:none;
}
.card-title{
  color: rgba(255,215,0,0.85);
  font-weight: 900;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}
.kpi{
  color: #fff;
  font-weight: 950;
  font-size: 26px;
  line-height: 1.05;
  text-shadow: 0 10px 25px rgba(0,0,0,0.35);
}
.sub{
  color: rgba(255,255,255,0.60);
  font-size: 12px;
  margin-top: 6px;
}
.kpi-compact .kpi{ font-size: 22px !important; }
.kpi-small .kpi{ font-size: 20px !important; }

/* ====== NEWS CARDS ====== */
a.news-card-link{ text-decoration:none; display:block; margin-bottom:10px; }
.news-card-box{
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 14px 14px;
  transition: all .14s ease;
  box-shadow: 0 10px 22px rgba(0,0,0,0.25);
}
.news-card-box:hover{
  border-color: rgba(255,215,0,0.45);
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(0,0,0,0.32);
}
.nc-title{
  color:#fff;
  font-weight: 950;
  font-size: 14px;
  line-height: 1.35;
  margin-bottom: 6px;
}
.nc-meta{
  color: rgba(255,255,255,0.60);
  font-size: 12px;
  display:flex;
  gap:8px;
  align-items:center;
}
.nc-badge{
  background: rgba(255,215,0,0.14);
  color: var(--bee-yellow);
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  border: 1px solid rgba(255,215,0,0.20);
}

/* ====== MARKET MONITOR PILLS ====== */
.ticker-pill{
  background: linear-gradient(90deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  border-radius: 12px;
  padding: 9px 10px;
  margin-bottom: 8px;
  display:flex;
  justify-content: space-between;
  align-items:center;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 10px 18px rgba(0,0,0,0.22);
}
.tp-up{ border-left: 4px solid var(--bee-good); }
.tp-down{ border-left: 4px solid var(--bee-bad); }
.tp-name{ font-weight: 950; font-size: 12px; color: rgba(255,255,255,0.80); }
.tp-price{ font-weight: 950; font-size: 12px; color: #FFF; }
.tp-pct{ font-size: 11px; font-weight: 950; }

/* ====== INPUTS / SELECT / DATE ====== */
.stTextInput input, .stNumberInput input, .stDateInput input{
  background: rgba(18,23,30,0.92) !important;
  color: #fff !important;
  border: 1px solid rgba(255,215,0,0.16) !important;
  border-radius: 12px !important;
}
.stSelectbox > div > div{
  background: rgba(18,23,30,0.92) !important;
  border: 1px solid rgba(255,215,0,0.16) !important;
  border-radius: 12px !important;
}

/* ====== BUTTONS (global) ====== */
.stButton button, .stDownloadButton button{
  border-radius: 12px !important;
  font-weight: 950 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)) !important;
  color: rgba(255,255,255,0.88) !important;
  box-shadow: 0 10px 18px rgba(0,0,0,0.22);
  transition: all .14s ease;
}
.stButton button:hover, .stDownloadButton button:hover{
  transform: translateY(-1px);
  border-color: rgba(255,215,0,0.28) !important;
}

/* botão amarelo */
.yellowbtn button{
  background: linear-gradient(180deg, var(--bee-yellow), #FFC400) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 12px !important;
  box-shadow: 0 16px 30px rgba(255,215,0,0.18);
}
.yellowbtn button:hover{
  transform: translateY(-1px);
  box-shadow: 0 18px 36px rgba(255,215,0,0.22);
}

/* ====== METRICS ====== */
div[data-testid="stMetric"]{
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 12px 12px;
  box-shadow: 0 12px 22px rgba(0,0,0,0.22);
}
div[data-testid="stMetric"] label{
  color: rgba(255,215,0,0.75) !important;
  font-weight: 900 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{
  color: #fff !important;
  font-weight: 950 !important;
}

/* ====== TABS ====== */
.stTabs [data-baseweb="tab-list"]{
  gap: 8px;
}
.stTabs [data-baseweb="tab"]{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  padding: 10px 14px;
  color: rgba(255,255,255,0.75);
  font-weight: 950;
}
.stTabs [aria-selected="true"]{
  background: rgba(255,215,0,0.16);
  border-color: rgba(255,215,0,0.28);
  color: #fff;
}

/* ====== EXPANDER ====== */
details{
  border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  background: rgba(255,255,255,0.02) !important;
  box-shadow: 0 10px 20px rgba(0,0,0,0.20);
}
details summary{
  color: rgba(255,255,255,0.86) !important;
  font-weight: 950 !important;
}

/* ====== PROGRESS BAR ====== */
div[data-testid="stProgress"] > div > div{
  background: linear-gradient(90deg, #FFC400, var(--bee-yellow)) !important;
}

/* ====== DATAFRAME / TABLE CONTAINER ====== */
div[data-testid="stDataFrame"], div[data-testid="stTable"]{
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 12px 22px rgba(0,0,0,0.20);
}

/* ====== LINK BUTTON ====== */
a[data-testid="stLinkButton"]{
  border-radius: 12px !important;
}

/* ====== FOOTER ====== */
.bee-footer{
  margin-top: 18px;
  opacity: .62;
  font-size: 12px;
  display:flex;
  justify-content: space-between;
  color: rgba(255,255,255,0.60);
}
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------
# 6) Data model & Session State
# --------------------------------------------------------------------------------
if "user_logged_in" not in st.session_state:
    st.session_state["user_logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_name_display" not in st.session_state:
    st.session_state["user_name_display"] = ""

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
if "patrimonio_meta" not in st.session_state:
    st.session_state["patrimonio_meta"] = 100000.0
if "gasto_meta" not in st.session_state:
    st.session_state["gasto_meta"] = 3000.0
if "bee_light" not in st.session_state:
    st.session_state["bee_light"] = False

# Bee Light CSS override (layout only)
if st.session_state.get("bee_light"):
    st.markdown(
        """
        <style>
        .stApp{
          background:
            radial-gradient(circle at 18% 18%, rgba(255,215,0,0.18), transparent 40%),
            radial-gradient(circle at 78% 82%, rgba(255,215,0,0.12), transparent 48%),
            radial-gradient(circle at 55% 35%, rgba(255,255,255,0.04), transparent 45%),
            linear-gradient(30deg, rgba(255,215,0,0.05) 12%, transparent 12.5%, transparent 87%, rgba(255,215,0,0.05) 87.5%, rgba(255,215,0,0.05)),
            linear-gradient(150deg, rgba(255,215,0,0.05) 12%, transparent 12.5%, transparent 87%, rgba(255,215,0,0.05) 87.5%, rgba(255,215,0,0.05)),
            linear-gradient(90deg, rgba(255,215,0,0.03) 2%, transparent 2.5%, transparent 97%, rgba(255,215,0,0.03) 97.5%, rgba(255,215,0,0.03)),
            #0B0F14;
          background-size: auto, auto, auto, 64px 64px, 64px 64px, 64px 64px, auto;
        }
        section[data-testid="stSidebar"]{ border-right: 1px solid rgba(255,215,0,0.22) !important; }
        .bee-card{ border: 1px solid rgba(255,215,0,0.14) !important; }
        .card-title{ color: rgba(255,215,0,0.95) !important; }
        .news-card-box{ border: 1px solid rgba(255,215,0,0.16) !important; }
        .news-card-box:hover{ border-color: rgba(255,215,0,0.55) !important; }
        .navbtn button{ border-color: rgba(255,215,0,0.14) !important; }
        .navbtn button:hover{ border-color: rgba(255,215,0,0.45) !important; }
        .stTextInput input, .stNumberInput input, .stDateInput input{
          border: 1px solid rgba(255,215,0,0.24) !important;
          box-shadow: 0 0 0 1px rgba(255,215,0,0.06) inset;
        }
        .stSelectbox > div > div{ border: 1px solid rgba(255,215,0,0.24) !important; }
        .stTabs [aria-selected="true"]{ background: rgba(255,215,0,0.22) !important; border-color: rgba(255,215,0,0.40) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def smart_load_csv(uploaded_file, sep_priority=","):
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=sep_priority)
        if len(df.columns) > 1: return df
    except Exception:
        pass
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";" if sep_priority == "," else ",")
        if len(df.columns) > 1: return df
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

    usdbrl = 5.80
    if yf is not None:
        try:
            fx = yf_last_and_prev_close(["BRL=X"])
            if not fx.empty: usdbrl = float(fx.iloc[0]["last"])
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
        if bool(is_rf.iloc[i]): continue
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


def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def kpi_card(title, value, sub="", color=None, compact=False, small=False):
    extra = ""
    if compact: extra = "kpi-compact"
    if small: extra = "kpi-small"
    st.markdown(
        f"""
<div class="bee-card {extra}" style="{f'border-top: 3px solid {color};' if color else ''}">
  <div class="card-title">{title}</div>
  <div class="kpi">{value}</div>
  <div class="sub">{sub}</div>
</div>
""", unsafe_allow_html=True)


def investidor10_link(ativo: str) -> str:
    a = (ativo or "").strip().upper().replace(".SA", "")
    if any(ch.isdigit() for ch in a):
        return f"https://investidor10.com.br/acoes/{a.lower()}/"
    return f"https://investidor10.com.br/"


# --------------------------------------------------------------------------------
# LOGIN SYSTEM INTERFACE
# --------------------------------------------------------------------------------
if not st.session_state["user_logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if logo_img:
            st.image(logo_img, width=150)
        else:
            st.markdown("# 🐝 Bee Finanças")

        st.markdown("### Acesso Seguro")

        tab_login, tab_register = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            l_user = st.text_input("Usuário", key="l_user")
            l_pass = st.text_input("Senha", type="password", key="l_pass")
            if st.button("Entrar", type="primary", use_container_width=True):
                name = login_user(l_user, l_pass)
                if name:
                    st.session_state["user_logged_in"] = True
                    st.session_state["username"] = l_user
                    st.session_state["user_name_display"] = name
                    # Carregar dados do usuário
                    c_df, g_df = load_user_data_db(l_user)
                    st.session_state["carteira_df"] = c_df
                    st.session_state["gastos_df"] = g_df
                    if not c_df.empty: st.session_state["wallet_mode"] = True
                    if not g_df.empty: st.session_state["gastos_mode"] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        with tab_register:
            r_user = st.text_input("Escolha um Usuário", key="r_user")
            r_name = st.text_input("Seu Nome", key="r_name")
            r_pass = st.text_input("Escolha uma Senha", type="password", key="r_pass")
            if st.button("Criar Conta", use_container_width=True):
                if r_user and r_pass:
                    if create_user(r_user, r_pass, r_name):
                        st.success("Conta criada! Faça login na aba 'Entrar'.")
                    else:
                        st.error("Usuário já existe.")
                else:
                    st.warning("Preencha todos os campos.")

    st.stop()  # PARA A EXECUÇÃO AQUI SE NÃO ESTIVER LOGADO

# --------------------------------------------------------------------------------
# MAIN APP (Só executa se logado)
# --------------------------------------------------------------------------------

# SIDEBAR
with st.sidebar:
    if logo_img:
        st.image(logo_img, width=280)
    else:
        st.markdown("## 🐝 Bee Finanças")

    st.markdown(
        f"<div style='font-size:12px; color:gray; margin-bottom:10px'>Olá, <b>{st.session_state['user_name_display']}</b></div>",
        unsafe_allow_html=True)

    st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
    nav_btn("🏠 Home", "🏠 Home")
    nav_btn("📰 Notícias", "📰 Notícias")

    st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
    nav_btn("🔍 Analisar", "🔍 Analisar")
    nav_btn("💼 Carteira", "💼 Carteira")
    nav_btn("💸 Controle", "💸 Controle")
    nav_btn("🧮 Calculadoras", "🧮 Calculadoras")

    st.divider()

    try:
        st.markdown(
            "<div style='font-size:12px; color:#666; font-weight:900; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>",
            unsafe_allow_html=True,
        )

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
            pill("BTC (R$)", f"R$ {fmt_ptbr_number(btcbrl['last'], 0)}" if btcbrl.get('last') else "—",
                 btcbrl.get("var_pct"))
        else:
            pill("BTC (R$)", "—", None)

        # NEW: Bee Light toggle
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.session_state["bee_light"] = st.toggle(
            "💡 Bee Light (mais amarelo)",
            value=st.session_state["bee_light"]
        )

        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state["user_logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

    except Exception:
        pass

# TOP BAR
c_spacer, c_info = st.columns([6, 2.5])
with c_spacer:
    st.write("")
with c_info:
    c_clock, c_btn = st.columns([2.5, 1], gap="small")
    with c_clock:
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
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
        if st.button("↻", key="top_refresh", help="Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.markdown("<hr style='border-color:rgba(255,255,255,0.06); margin-top:10px'>", unsafe_allow_html=True)

page = st.session_state["page"]

# --------------------------------------------------------------------------------
# PAGES
# --------------------------------------------------------------------------------
if page == "🏠 Home":
    st.markdown(f"## 📌 Visão do Mercado (Olá, {st.session_state['user_name_display']})")

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
            val = f"R$ {fmt_ptbr_number(btcbrl['last'], 0)}"
            sub = f"{btcbrl.get('var_pct', 0):+.2f}% (24h)"
        else:
            val, sub = "—", ""
        kpi_card("BTC (R$)", val, sub, color="#FFD700", small=True)

    st.write("")
    st.markdown("### ⚡ Acesso Rápido")

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
    st.markdown("## 🔍 Analisar Pro")
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
            f1, f2, f3 = st.columns(3)
            with f1:
                roe_val = info.get('roe')
                st.metric("ROE (Rentab.)", f"{roe_val * 100:.2f}%" if roe_val else "—")
            with f2:
                mg_val = info.get('margins')
                st.metric("Margem Líq.", f"{mg_val * 100:.2f}%" if mg_val else "—")
            with f3:
                beta_val = info.get('beta')
                st.metric("Beta (Volat.)", f"{beta_val:.2f}" if beta_val else "—")

            st.markdown("---")
            fig, rsi = get_stock_history_plot(tk_real, period=periodo)

            if rsi:
                rsi_text = f"{rsi:.1f}"
                if rsi > 70:
                    rsi_status = "⚠️ Sobrecomprado (Cara?)"
                    rsi_color_code = "#FF3B30"
                elif rsi < 30:
                    rsi_status = "💎 Sobrevendido (Barata?)"
                    rsi_color_code = "#00C805"
                else:
                    rsi_status = "Neutro"
                    rsi_color_code = "#FFD700"

                st.markdown(
                    f"**RSI (IFR 14):** <span style='color:{rsi_color_code}; font-weight:bold; font-size:18px'>{rsi_text}</span> — {rsi_status}",
                    unsafe_allow_html=True)
                st.caption(
                    "RSI acima de 70 indica alta forte (risco correção). Abaixo de 30 indica baixa forte (oportunidade?).")

            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Sem gráfico disponível.")

            with st.expander("Resumo da Empresa"):
                st.write(info.get("summary", "—"))
        else:
            st.error("Ativo não encontrado.")

elif page == "💼 Carteira":
    st.markdown("## 💼 Carteira 2.0 (Multi-User)")
    wallet_active = (not st.session_state["carteira_df"].empty) or st.session_state["wallet_mode"]

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("Importar CSV", type=["csv"], key="uploader_start")
            if uploaded_file:
                df_loaded = smart_load_csv(uploaded_file)
                if df_loaded is not None:
                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    # Auto-save no DB
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                      st.session_state["gastos_df"])
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            st.success("Começar do zero")
            if st.button("Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                  st.session_state["gastos_df"])
                st.rerun()
    else:
        df = st.session_state["carteira_df"]

        if not df.empty:
            with st.spinner("Sincronizando preços..."):
                df_calc, kpi = atualizar_precos_carteira_memory(df)

            total_patrimonio = kpi["total_brl"]
            c_meta, c_set = st.columns([4, 1])
            with c_set:
                nova_meta = st.number_input("Sua Meta (R$)", value=st.session_state["patrimonio_meta"], step=10000.0,
                                            label_visibility="collapsed")
                st.session_state["patrimonio_meta"] = nova_meta

            with c_meta:
                progresso = min(total_patrimonio / nova_meta, 1.0) if nova_meta > 0 else 0
                st.progress(progresso)
                st.caption(f"Meta: {fmt_money_brl(nova_meta, 0)} ({(progresso * 100):.1f}%)")

            k1, k2, k3 = st.columns(3)
            with k1:
                kpi_card("TOTAL", fmt_money_brl(kpi["total_brl"], 2), "Patrimônio", compact=True)
            with k2:
                color = "#00C805" if kpi["pnl_brl"] >= 0 else "#FF3B30"
                kpi_card("RESULTADO", fmt_money_brl(kpi["pnl_brl"], 2), f"{kpi['pnl_pct']:+.2f}%", color=color,
                         compact=True)
            with k3:
                kpi_card("ATIVOS", f"{len(df_calc)}", "Diversificação", compact=True)

            if px and not df_calc.empty:
                g1, g2 = st.columns([1, 2])
                with g1:
                    # Usando Treemap ao inves de Pie
                    fig_tree = px.treemap(
                        df_calc,
                        path=[px.Constant("Carteira"), 'Tipo', 'Ativo'],
                        values='Total_BRL',
                        color='PnL_Pct',
                        color_continuous_scale=['#FF3B30', '#111111', '#00C805'],
                        color_continuous_midpoint=0
                    )
                    fig_tree.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_tree, use_container_width=True)

                with g2:
                    st.markdown("#### 🔴 Monitor de Rentabilidade")
                    st.caption("Clique na linha para abrir o Pop-up com detalhes")

                    live_df = df_calc[["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL"]].copy()

                    selection = st.dataframe(
                        live_df,
                        column_config={
                            "Ativo": "Ativo",
                            "Qtd": st.column_config.NumberColumn("Qtd", format="%.2f"),
                            "Preco_Medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                            "Preco_Atual_BRL": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
                            "PnL_Pct": st.column_config.NumberColumn("Rentab. %", format="%.2f %%"),
                            "Total_BRL": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=250,
                        on_select="rerun",
                        selection_mode="single-row"
                    )

                    if selection and selection.selection.rows:
                        idx_sel = selection.selection.rows[0]
                        ativo_selecionado = live_df.iloc[idx_sel]["Ativo"]
                        show_asset_details_popup(ativo_selecionado)

        st.write("---")
        with st.expander("📝 Adicionar / Editar Ativos", expanded=False):
            st.caption("Edite os valores na tabela abaixo para atualizar sua carteira.")

            edit_cols = ["Tipo", "Ativo", "Qtd", "Preco_Medio", "Moeda", "Obs"]
            edited_df = st.data_editor(
                df[edit_cols],
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.01, format="%.4f"),
                    "Preco_Medio": st.column_config.NumberColumn("Preço Médio", min_value=0.0, step=0.01,
                                                                 format="R$ %.2f"),
                    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação/ETF", "Cripto", "Renda Fixa"]),
                    "Moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
                },
                key="editor_carteira"
            )

            if st.button("💾 Salvar na Nuvem (DB)", type="primary"):
                st.session_state["carteira_df"] = edited_df
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                  st.session_state["gastos_df"])
                st.toast("Carteira salva com sucesso!", icon="✅")
                st.rerun()

        st.write("")
        st.download_button(
            "⬇️ Backup Local (CSV)",
            df.to_csv(index=False).encode("utf-8"),
            "minha_carteira.csv",
            "text/csv"
        )
        if st.button("Limpar Carteira"):
            st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
            st.session_state["wallet_mode"] = False
            save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                              st.session_state["gastos_df"])
            st.rerun()

elif page == "💸 Controle":
    st.markdown("## 💸 Controle de Gastos 2.0")
    gastos_active = (not st.session_state["gastos_df"].empty) or st.session_state["gastos_mode"]

    if not gastos_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_gastos = st.file_uploader("Importar CSV", type=["csv"], key="uploader_gastos")
            if uploaded_gastos:
                df_g = smart_load_csv(uploaded_gastos)
                if df_g is not None:
                    st.session_state["gastos_df"] = df_g
                    st.session_state["gastos_mode"] = True
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                      st.session_state["gastos_df"])
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            if st.button("Criar Planilha de Gastos", use_container_width=True):
                st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
                st.session_state["gastos_mode"] = True
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                  st.session_state["gastos_df"])
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

        col_sel, col_meta = st.columns([2, 2])
        with col_sel:
            mes_selecionado = st.selectbox("📅 Mês", meses_disp, index=idx_mes)
        with col_meta:
            nova_meta_gasto = st.number_input("💰 Orçamento Mensal (R$)", value=st.session_state["gasto_meta"],
                                              step=100.0)
            st.session_state["gasto_meta"] = nova_meta_gasto

        mask_mes = df_g["Data"].dt.strftime("%Y-%m") == mes_selecionado
        df_filtered = df_g[mask_mes]

        total_ent = float(df_filtered[df_filtered["Tipo"] == "Entrada"]["Valor"].sum())
        total_sai = float(df_filtered[df_filtered["Tipo"] == "Saída"]["Valor"].sum())
        saldo = total_ent - total_sai

        percent_gasto = min(total_sai / nova_meta_gasto, 1.0) if nova_meta_gasto > 0 else 0
        cor_barra = "green"
        if percent_gasto > 0.75: cor_barra = "orange"
        if percent_gasto > 0.95: cor_barra = "red"

        st.markdown(f"**Orçamento usado:** {percent_gasto * 100:.1f}% de {fmt_money_brl(nova_meta_gasto, 0)}")
        st.progress(percent_gasto)

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("Receitas", fmt_money_brl(total_ent, 2))
        with k2:
            st.metric("Despesas", fmt_money_brl(total_sai, 2))
        with k3:
            st.metric("Saldo", fmt_money_brl(saldo, 2))

        st.markdown("### 📊 Análise Visual")
        if px is not None and not df_filtered.empty and total_sai > 0:
            tab_g1, tab_g2 = st.tabs(["Por Categoria", "Evolução Diária"])

            with tab_g1:
                df_pie = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
                fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.5,
                             color_discrete_sequence=px.colors.sequential.Magma)
                fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

            with tab_g2:
                df_daily = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Data")["Valor"].sum().reset_index()
                fig_bar = px.bar(df_daily, x="Data", y="Valor", color="Valor", color_continuous_scale="Reds")
                fig_bar.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True)
        elif df_filtered.empty:
            st.info("Nenhum lançamento neste mês.")

        st.write("---")

        with st.expander("➕ Nova Transação", expanded=False):
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
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                                      st.session_state["gastos_df"])
                    st.toast("Transação salva!", icon="💸")
                    st.rerun()

        st.markdown("##### Extrato Detalhado")
        df_g_edited = st.data_editor(
            df_g,
            num_rows="dynamic",
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
            },
            use_container_width=True,
            height=340,
            key="editor_gastos"
        )
        if st.button("💾 Salvar na Nuvem (DB)", key="save_gastos"):
            st.session_state["gastos_df"] = df_g_edited
            save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                              st.session_state["gastos_df"])
            st.toast("Extrato atualizado!", icon="✅")
            st.rerun()

        st.write("---")

        st.download_button(
            "⬇️ Backup Local (CSV)",
            df_g.to_csv(index=False).encode("utf-8"),
            "meus_gastos.csv",
            "text/csv"
        )

        if st.button("Limpar Gastos"):
            st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
            st.session_state["gastos_mode"] = False
            save_user_data_db(st.session_state["username"], st.session_state["carteira_df"],
                              st.session_state["gastos_df"])
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
# FOOTER
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