import warnings
import logging
from datetime import datetime

# -----------------------------------------------------------------------------
# 0) FILTROS DE SILENCIAMENTO
# -----------------------------------------------------------------------------
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

import streamlit as st

# =============================================================================
# IMPORTS DO SEU PROJETO
# =============================================================================
# Mantemos os imports para garantir que o resto funcione, mas não usaremos yf na home
from bee.safe_imports import yf, go, px, dtparser, GoogleTranslator
from bee.theme import apply_page_config, apply_theme_css, apply_bee_light_css
from bee.state import init_session_state
from bee.db import (
    init_db,
    login_user,
    create_user,
    load_user_data_db,
    update_password_db,
    delete_user_db
)

# Páginas
from bee.pages.home import render_home
from bee.pages.noticias import render_noticias
from bee.pages.analisar import render_analisar
from bee.pages.carteira import render_carteira
from bee.pages.controle import render_controle
from bee.pages.calculadoras import render_calculadoras
from bee.pages.academy import render_academy
from bee.academy.progress import init_academy_db


# =============================================================================
# 1) OTIMIZAÇÃO DE PERFORMANCE (CACHE DE DADOS DO USUÁRIO)
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def cached_load_user_data(username):
    """Carrega dados do banco com cache de 5 minutos."""
    return load_user_data_db(username)


# =============================================================================
# 2) BARRA SUPERIOR SIMPLES (SÓ RELÓGIO - ZERO LAG)
# =============================================================================
def render_top_bar_simple():
    """
    Renderiza apenas o relógio.
    Não faz NENHUMA conexão externa (Yahoo), por isso é instantâneo.
    """

    # CSS para a barra ficar bonita e simples
    st.markdown("""
        <style>
        .top-bar-simple {
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            padding: 8px 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            width: fit-content; /* Ocupa só o espaço necessário */
        }
        .clock-text { 
            font-weight: bold; 
            opacity: 0.9; 
            color: #FFD700; /* Dourado Bee */
            font-family: monospace;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""
    <div class="top-bar-simple">
        <div class="clock-text">🕒 {agora}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =============================================================================
# 3) CSS (VISUAL)
# =============================================================================
def apply_app_shell_css():
    st.markdown(
        """
        <style>
        /* --- LIMPEZA --- */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }
        header[data-testid="stHeader"] { opacity: 0; pointer-events: none; height: 0px; }
        section[data-testid="stSidebar"] { display: none !important; }

        .block-container {
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100%;
            padding-bottom: 4rem !important;
        }

        /* --- BOTÃO FLUTUANTE --- */
        .floating-menu-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 999999;
        }
        .floating-menu-container button {
            background-color: #FFD700 !important;
            color: #111 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 16px !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        .floating-menu-container button:hover {
            opacity: 0.9;
            transform: scale(1.02);
        }

        .bee-footer {
            margin-top: 40px;
            padding: 20px;
            text-align: center;
            font-size: 11px;
            opacity: 0.4;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 4) MENU POP-UP
# =============================================================================
@st.dialog("🐝 Menu Principal")
def open_menu_modal():
    st.caption("🏠 HUB")
    c1, c2 = st.columns(2)
    if c1.button("Home", use_container_width=True):
        st.session_state["page"] = "🏠 Home";
        st.rerun()
    if c2.button("Notícias", use_container_width=True):
        st.session_state["page"] = "📰 Notícias";
        st.rerun()

    st.caption("🛠️ FERRAMENTAS")
    c3, c4 = st.columns(2)
    if c3.button("Carteira", use_container_width=True):
        st.session_state["page"] = "💼 Carteira";
        st.rerun()
    if c4.button("Controle", use_container_width=True):
        st.session_state["page"] = "💸 Controle";
        st.rerun()

    c5, c6 = st.columns(2)
    if c5.button("Analisar", use_container_width=True):
        st.session_state["page"] = "🔍 Analisar";
        st.rerun()
    if c6.button("Calculadoras", use_container_width=True):
        st.session_state["page"] = "🧮 Calculadoras";
        st.rerun()

    st.caption("🎓 APRENDER")
    if st.button("Bee Academy", use_container_width=True):
        st.session_state["page"] = "🎓 Bee Academy";
        st.rerun()

    st.divider()

    with st.expander(f"⚙️ Configurações"):
        c_mode = st.toggle("💡 Modo Claro", value=st.session_state.get("bee_light", False))
        if c_mode != st.session_state.get("bee_light", False):
            st.session_state["bee_light"] = c_mode;
            st.rerun()

        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state.clear();
            st.rerun()


def render_floating_menu_button():
    st.markdown('<div class="floating-menu-container">', unsafe_allow_html=True)

    # O clique aqui roda só este pedacinho de código
    if st.button("☰ Menu", key="btn_main_menu_float"):
        open_menu_modal()  # Abre o pop-up

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 5) LOGIN
# =============================================================================
def render_login(logo_img):
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    cols = st.columns([1, 6, 1])
    center = cols[1]

    with center:
        st.markdown("<div style='text-align:center; margin-bottom: 20px;'>", unsafe_allow_html=True)
        if logo_img:
            st.image(logo_img, width=140)
        else:
            st.markdown("<h1>🐝 Bee Finanças</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            with st.form("login_form"):
                l_user = st.text_input("Usuário")
                l_pass = st.text_input("Senha", type="password")
                btn_login = st.form_submit_button("Acessar Painel", type="primary", use_container_width=True)

                if btn_login:
                    name = login_user(l_user, l_pass)
                    if name:
                        st.session_state["user_logged_in"] = True
                        st.session_state["username"] = l_user
                        st.session_state["user_name_display"] = name
                        try:
                            c_df, g_df = cached_load_user_data(l_user)
                            st.session_state["carteira_df"] = c_df
                            st.session_state["gastos_df"] = g_df
                            st.session_state["wallet_mode"] = not c_df.empty
                            st.session_state["gastos_mode"] = not g_df.empty
                        except Exception:
                            pass
                        st.session_state["page"] = "🏠 Home"
                        st.rerun()
                    else:
                        st.error("Dados incorretos.")

        with tab_register:
            with st.form("register_form"):
                r_user = st.text_input("Novo Usuário")
                r_name = st.text_input("Seu Nome")
                r_pass = st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    if create_user(r_user, r_pass, r_name):
                        st.success("Conta criada! Faça login.")
                    else:
                        st.error("Usuário já existe.")
    st.stop()


# =============================================================================
# 6) ROTEADOR
# =============================================================================
def route_pages():
    page = st.session_state.get("page", "🏠 Home")
    if page == "🏠 Home":
        render_home()
    elif page == "📰 Notícias":
        render_noticias()
    elif page == "🔍 Analisar":
        render_analisar()
    elif page == "💼 Carteira":
        render_carteira()
    elif page == "💸 Controle":
        render_controle()
    elif page == "🧮 Calculadoras":
        render_calculadoras()
    elif page == "🎓 Bee Academy":
        render_academy()
    else:
        render_home()


# =============================================================================
# MAIN
# =============================================================================
def main():
    logo_img = apply_page_config()
    apply_theme_css()
    apply_app_shell_css()
    init_session_state()
    init_db()
    init_academy_db()

    if st.session_state.get("bee_light"):
        apply_bee_light_css()

    if not st.session_state.get("user_logged_in", False):
        render_login(logo_img)
        return

    # Garante dados carregados
    if "carteira_df" not in st.session_state:
        c_df, g_df = cached_load_user_data(st.session_state["username"])
        st.session_state["carteira_df"] = c_df
        st.session_state["gastos_df"] = g_df

    # Renderiza a NOVA Barra Simples (Só Relógio, Sem travamentos)
    render_top_bar_simple()

    # Renderiza Botão Menu
    render_floating_menu_button()

    # Renderiza Página
    route_pages()

    st.markdown("<div class='bee-footer'>Bee Finanças • Modo Turbo</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()