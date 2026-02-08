import os
import streamlit as st
from PIL import Image

# Tenta importar do config, se falhar usa padrão
try:
    from .config import LOGO_PATH
except ImportError:
    LOGO_PATH = "logo.png"

# =============================================================================
# 1) OTIMIZAÇÃO DE PERFORMANCE (CACHE)
# =============================================================================
@st.cache_data(show_spinner=False)
def process_logo_transparency(image_path):
    """Carrega e processa a imagem uma única vez."""
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

# =============================================================================
# 2) CSS COMPLETO (VISUAL RICO + MENU GRID + NAV BUTTONS)
# =============================================================================
def apply_theme_css():
    st.markdown(
        """
<style>
/* =========================
   BEE THEME (v37 - GRID MENU & NAV)
   ========================= */

:root {
  --bee-yellow: #FFD700;
  --bee-black: #0B0F14;
  --bee-border: rgba(255,255,255,0.08);
  --bee-good: #00C805;
  --bee-bad: #FF3B30;
  --shadow-2: 0 8px 18px rgba(0,0,0,0.25);
}

/* ====== FUNDO ====== */
.stApp {
  background:
    radial-gradient(circle at 18% 18%, rgba(255,215,0,0.08), transparent 38%),
    radial-gradient(circle at 78% 82%, rgba(93,64,55,0.22), transparent 45%),
    linear-gradient(30deg, rgba(255,215,0,0.03) 12%, transparent 12.5%, transparent 87%, rgba(255,215,0,0.03) 87.5%, rgba(255,215,0,0.03)),
    var(--bee-black);
  background-size: auto, auto, 64px 64px, auto;
}

/* ====== TIPOGRAFIA ====== */
h1, h2, h3, h4 { color: var(--bee-yellow) !important; font-family: Inter, sans-serif; font-weight: 900; letter-spacing: -0.03em; }
div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

/* ====== SIDEBAR ====== */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #07090D 0%, #090C10 55%, #07090D 100%);
  border-right: 1px solid rgba(255,215,0,0.10);
}
section[data-testid="stSidebar"] img { filter: drop-shadow(0 10px 20px rgba(0,0,0,0.35)); }

/* ====== BUTTONS (GLOBAL) ====== */
.stButton button, .stDownloadButton button {
  border-radius: 12px !important;
  font-weight: 800 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)) !important;
  color: rgba(255,255,255,0.88) !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.22);
  transition: all .14s ease;
  width: auto !important; /* Compacto */
  padding: 0.3rem 1.2rem !important;
  min-height: 0px !important;
  display: inline-flex !important;
  justify-content: center;
  align-items: center;
}
.stButton button:hover {
  transform: translateY(-1px);
  border-color: rgba(255,215,0,0.35) !important;
}

/* Exceções: Login e Sidebar full width */
div[data-testid="stForm"] .stButton button, section[data-testid="stSidebar"] .stButton button {
    width: 100% !important;
    justify-content: flex-start !important;
}

/* ====== CARDS & METRICS ====== */
.bee-card, div[data-testid="stMetric"], .news-card-box {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 16px;
  backdrop-filter: blur(6px);
  box-shadow: var(--shadow-2);
}
div[data-testid="stMetric"] label { color: rgba(255,215,0,0.75) !important; font-weight: 800 !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #fff !important; font-weight: 900 !important; }

/* ====== INPUTS ====== */
.stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox > div > div {
  background: rgba(18,23,30,0.92) !important;
  color: #fff !important;
  border: 1px solid rgba(255,215,0,0.16) !important;
  border-radius: 12px !important;
}

/* ====== DATAFRAME ====== */
div[data-testid="stDataFrame"] { border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); }

/* ====== FOOTER ====== */
.bee-footer { margin-top: 18px; opacity: .62; font-size: 12px; display: flex; justify-content: center; color: rgba(255,255,255,0.60); }

/* ============================================================
   NOVO MENU (GRID STYLE - QUADRADOS)
   ============================================================ */
div[data-testid="stDialog"] .stButton button {
    width: 100% !important;
    height: 85px !important; /* Altura fixa para quadrado */
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 6px !important;
    background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    white-space: pre-wrap !important; /* Permite quebra de linha no texto */
    line-height: 1.2 !important;
}

div[data-testid="stDialog"] .stButton button:hover {
    background: rgba(255,215,0,0.15) !important;
    border-color: #FFD700 !important;
    color: #FFD700 !important;
    transform: translateY(-2px) !important;
}

/* ============================================================
   BOTÕES DE NAVEGAÇÃO (CARTEIRA/CONTROLE)
   ============================================================ */
/* Botão Ativo (Amarelo) */
.nav-tab-active button {
    background: #FFD700 !important;
    color: #0B0F14 !important;
    border-color: #FFD700 !important;
    font-weight: 900 !important;
    box-shadow: 0 0 15px rgba(255,215,0,0.3) !important;
}
/* Botão Inativo (Transparente) */
.nav-tab-inactive button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    opacity: 0.7;
}
.nav-tab-inactive button:hover {
    border-color: rgba(255,215,0,0.5) !important;
    opacity: 1;
}
</style>
""",
        unsafe_allow_html=True,
    )

def apply_bee_light_css():
    st.markdown(
        """
        <style>
        .stApp { background: #F0F2F6; color: #111; }
        /* Adicione aqui ajustes para light mode se precisar */
        </style>
        """,
        unsafe_allow_html=True,
    )