import os
import streamlit as st
from PIL import Image
from .config import LOGO_PATH

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

def apply_page_config():
    logo_img = process_logo_transparency(LOGO_PATH)
    page_icon = logo_img if logo_img else "🐝"
    st.set_page_config(
        page_title="Bee Finanças",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    return logo_img

def apply_theme_css():
    # CSS COMPLETO (igual ao teu)
    st.markdown(
        """
<style>
/* =========================
   BEE THEME (v34 - EXTENDED CSS)
   Paleta: Amarelo / Preto / Marrom / Branco
   ========================= */

:root {
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

/* ====== FUNDO (BACKGROUND) ====== */
.stApp {
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
h1, h2, h3, h4 {
  color: var(--bee-yellow) !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  font-weight: 900;
  letter-spacing: -0.03em;
}

p, span, div {
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

/* Espaçamentos verticais ajustados */
div[data-testid="stVerticalBlock"] {
  gap: 0.40rem !important;
}

/* ====== SIDEBAR ====== */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #07090D 0%, #090C10 55%, #07090D 100%);
  border-right: 1px solid rgba(255,215,0,0.10);
}

section[data-testid="stSidebar"] img {
  display: block;
  margin: 6px auto 10px auto;
  object-fit: contain;
  max-width: 100%;
  filter: drop-shadow(0 10px 20px rgba(0,0,0,0.35));
}

.menu-header {
  font-size: 10px;
  text-transform: uppercase;
  color: rgba(255,215,0,0.45);
  font-weight: 900;
  letter-spacing: 1.1px;
  margin-top: 10px;
  margin-bottom: 6px;
  padding-left: 4px;
}

/* ====== NAV BUTTONS ====== */
.navbtn button {
  width: 100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.045) 0%, rgba(255,255,255,0.018) 100%) !important;
  color: rgba(255,255,255,0.78) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  padding: 0.42rem 0.85rem !important;
  font-weight: 900 !important;
  font-size: 13px !important;
  text-align: left !important;
  transition: all .14s ease;
  height: 40px !important;
  display: flex !important;
  align-items: center !important;
  box-shadow: 0 8px 18px rgba(0,0,0,0.20);
}

.navbtn button:hover {
  background: linear-gradient(90deg, rgba(255,215,0,0.14) 0%, rgba(93,64,55,0.16) 100%) !important;
  border-color: rgba(255,215,0,0.35) !important;
  transform: translateX(3px);
}

.navbtn button:focus {
  outline: none !important;
}

/* ====== DIVIDER / HR ====== */
hr, .stDivider {
  border-color: rgba(255,255,255,0.08) !important;
}

/* ====== CARDS (bee-card) ====== */
.bee-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 16px;
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-2);
  position: relative;
  overflow: hidden;
}

.bee-card::before {
  content: "";
  position: absolute;
  inset: -2px;
  background: radial-gradient(circle at 20% 0%, rgba(255,215,0,0.16), transparent 40%),
              radial-gradient(circle at 90% 100%, rgba(93,64,55,0.22), transparent 42%);
  opacity: .55;
  pointer-events: none;
}

.card-title {
  color: rgba(255,215,0,0.85);
  font-weight: 900;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.kpi {
  color: #fff;
  font-weight: 950;
  font-size: 26px;
  line-height: 1.05;
  text-shadow: 0 10px 25px rgba(0,0,0,0.35);
}

.sub {
  color: rgba(255,255,255,0.60);
  font-size: 12px;
  margin-top: 6px;
}

.kpi-compact .kpi {
  font-size: 22px !important;
}

.kpi-small .kpi {
  font-size: 20px !important;
}

/* ====== NEWS CARDS ====== */
a.news-card-link {
  text-decoration: none;
  display: block;
  margin-bottom: 10px;
}

.news-card-box {
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 14px 14px;
  transition: all .14s ease;
  box-shadow: 0 10px 22px rgba(0,0,0,0.25);
}

.news-card-box:hover {
  border-color: rgba(255,215,0,0.45);
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(0,0,0,0.32);
}

.nc-title {
  color: #fff;
  font-weight: 950;
  font-size: 14px;
  line-height: 1.35;
  margin-bottom: 6px;
}

.nc-meta {
  color: rgba(255,255,255,0.60);
  font-size: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.nc-badge {
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
.ticker-pill {
  background: linear-gradient(90deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
  border-radius: 12px;
  padding: 9px 10px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 10px 18px rgba(0,0,0,0.22);
}

.tp-up {
  border-left: 4px solid var(--bee-good);
}

.tp-down {
  border-left: 4px solid var(--bee-bad);
}

.tp-name {
  font-weight: 950;
  font-size: 12px;
  color: rgba(255,255,255,0.80);
}

.tp-price {
  font-weight: 950;
  font-size: 12px;
  color: #FFF;
}

.tp-pct {
  font-size: 11px;
  font-weight: 950;
}

/* ====== INPUTS / SELECT / DATE ====== */
.stTextInput input, .stNumberInput input, .stDateInput input {
  background: rgba(18,23,30,0.92) !important;
  color: #fff !important;
  border: 1px solid rgba(255,215,0,0.16) !important;
  border-radius: 12px !important;
}

.stSelectbox > div > div {
  background: rgba(18,23,30,0.92) !important;
  border: 1px solid rgba(255,215,0,0.16) !important;
  border-radius: 12px !important;
}

/* ====== BUTTONS (global) ====== */
.stButton button, .stDownloadButton button {
  border-radius: 12px !important;
  font-weight: 950 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)) !important;
  color: rgba(255,255,255,0.88) !important;
  box-shadow: 0 10px 18px rgba(0,0,0,0.22);
  transition: all .14s ease;
}

.stButton button:hover, .stDownloadButton button:hover {
  transform: translateY(-1px);
  border-color: rgba(255,215,0,0.28) !important;
}

/* botão amarelo (Custom Class) */
.yellowbtn button {
  background: linear-gradient(180deg, var(--bee-yellow), #FFC400) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 12px !important;
  box-shadow: 0 16px 30px rgba(255,215,0,0.18);
}

.yellowbtn button:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 36px rgba(255,215,0,0.22);
}

/* ====== METRICS ====== */
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 12px 12px;
  box-shadow: 0 12px 22px rgba(0,0,0,0.22);
}

div[data-testid="stMetric"] label {
  color: rgba(255,215,0,0.75) !important;
  font-weight: 900 !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: #fff !important;
  font-weight: 950 !important;
}

/* ====== TABS ====== */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
}

.stTabs [data-baseweb="tab"] {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  padding: 10px 14px;
  color: rgba(255,255,255,0.75);
  font-weight: 950;
}

.stTabs [aria-selected="true"] {
  background: rgba(255,215,0,0.16);
  border-color: rgba(255,215,0,0.28);
  color: #fff;
}

/* ====== EXPANDER ====== */
details {
  border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  background: rgba(255,255,255,0.02) !important;
  box-shadow: 0 10px 20px rgba(0,0,0,0.20);
}

details summary {
  color: rgba(255,255,255,0.86) !important;
  font-weight: 950 !important;
}

/* ====== PROGRESS BAR ====== */
div[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #FFC400, var(--bee-yellow)) !important;
}

/* ====== DATAFRAME / TABLE CONTAINER ====== */
div[data-testid="stDataFrame"], div[data-testid="stTable"] {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 12px 22px rgba(0,0,0,0.20);
}

/* ====== LINK BUTTON ====== */
a[data-testid="stLinkButton"] {
  border-radius: 12px !important;
}

/* ====== FOOTER ====== */
.bee-footer {
  margin-top: 18px;
  opacity: .62;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  color: rgba(255,255,255,0.60);
}
</style>
""",
        unsafe_allow_html=True,
    )

def apply_bee_light_css():
    st.markdown(
        """
        <style>
        /* ====== BEE LIGHT MODE (Tema Claro/Amarelo) ====== */
        .stApp {
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

        section[data-testid="stSidebar"] {
          border-right: 1px solid rgba(255,215,0,0.22) !important;
        }

        .bee-card {
          border: 1px solid rgba(255,215,0,0.14) !important;
        }

        .card-title {
          color: rgba(255,215,0,0.95) !important;
        }

        .news-card-box {
          border: 1px solid rgba(255,215,0,0.16) !important;
        }

        .news-card-box:hover {
          border-color: rgba(255,215,0,0.55) !important;
        }

        .navbtn button {
          border-color: rgba(255,215,0,0.14) !important;
        }

        .navbtn button:hover {
          border-color: rgba(255,215,0,0.45) !important;
        }

        .stTextInput input, .stNumberInput input, .stDateInput input {
          border: 1px solid rgba(255,215,0,0.24) !important;
          box-shadow: 0 0 0 1px rgba(255,215,0,0.06) inset;
        }

        .stSelectbox > div > div {
          border: 1px solid rgba(255,215,0,0.24) !important;
        }

        .stTabs [aria-selected="true"] {
          background: rgba(255,215,0,0.22) !important;
          border-color: rgba(255,215,0,0.40) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
