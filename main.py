import warnings

warnings.filterwarnings("ignore")

import streamlit as st

# =============================================================================
# IMPORTS DO SEU PROJETO
# =============================================================================
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
from bee.components import nav_btn, sidebar_market_monitor, top_bar

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
# 0) OTIMIZAÇÃO DE PERFORMANCE (CACHE)
# =============================================================================
# Isso impede que o app trave recarregando o banco de dados toda hora
@st.cache_data(ttl=300)  # Cache dura 5 minutos ou até limpar
def cached_load_user_data(username):
    return load_user_data_db(username)


# =============================================================================
# 1) CSS CORRETIVO (LAYOUT APP + BOTÃO FLUTUANTE AJUSTADO)
# =============================================================================
def apply_app_shell_css():
    st.markdown(
        """
        <style>
        /* LIMPEZA GERAL */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

        /* Header invisível mas não bloqueante */
        header[data-testid="stHeader"] {
            opacity: 0;
            pointer-events: none;
            height: 0px;
        }

        /* Esconde Sidebar Nativa */
        section[data-testid="stSidebar"] { display: none !important; }

        /* Ajuste do Corpo */
        .block-container {
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100%;
        }

        /* --- BOTÃO FLUTUANTE (POSIÇÃO CORRIGIDA) --- */
        .floating-menu-container {
            position: fixed;
            top: 70px;  /* DESCEMOS MAIS PARA NÃO FICAR NO TOPO ABSOLUTO */
            right: 20px;
            z-index: 999999;
        }

        /* Estilo do Botão */
        .floating-menu-container button {
            background-color: rgba(14, 17, 23, 0.95) !important;
            color: #FFD700 !important;
            border: 1px solid rgba(255, 215, 0, 0.4) !important;
            border-radius: 12px !important; /* Mais quadrado, estilo app */
            padding: 10px 18px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.6) !important;
            backdrop-filter: blur(10px);
            transition: all 0.2s ease;
        }
        .floating-menu-container button:active {
            transform: scale(0.92);
            background-color: #FFD700 !important;
            color: #000 !important;
        }

        /* Footer */
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
# 2) MENU DE NAVEGAÇÃO ORGANIZADO (MODAL)
# =============================================================================
@st.dialog("🐝 Menu Principal")
def open_menu_modal():
    # --- SEÇÃO 1: HUB ---
    st.caption("🏠 HUB")
    c1, c2 = st.columns(2)
    if c1.button("Home", use_container_width=True):
        st.session_state["page"] = "🏠 Home"
        st.rerun()
    if c2.button("Notícias", use_container_width=True):
        st.session_state["page"] = "📰 Notícias"
        st.rerun()

    # --- SEÇÃO 2: FERRAMENTAS ---
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.caption("🛠️ FERRAMENTAS")
    c3, c4 = st.columns(2)
    if c3.button("Carteira", use_container_width=True):
        st.session_state["page"] = "💼 Carteira"
        st.rerun()
    if c4.button("Controle", use_container_width=True):
        st.session_state["page"] = "💸 Controle"
        st.rerun()

    c5, c6 = st.columns(2)
    if c5.button("Analisar", use_container_width=True):
        st.session_state["page"] = "🔍 Analisar"
        st.rerun()
    if c6.button("Calculadoras", use_container_width=True):
        st.session_state["page"] = "🧮 Calculadoras"
        st.rerun()

    # --- SEÇÃO 3: EDUCAÇÃO ---
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.caption("🎓 APRENDER")
    if st.button("Bee Academy", use_container_width=True):
        st.session_state["page"] = "🎓 Bee Academy"
        st.rerun()

    st.divider()

    # --- SEÇÃO 4: CONFIGURAÇÕES E CONTA (EXPANDER) ---
    with st.expander(f"⚙️ Configurações ({st.session_state.get('user_name_display')})"):
        # Dark/Light Mode
        c_mode = st.toggle("💡 Modo Claro", value=st.session_state.get("bee_light", False))
        if c_mode != st.session_state.get("bee_light", False):
            st.session_state["bee_light"] = c_mode
            st.rerun()

        st.markdown("---")

        # Mudar Senha
        st.caption("Segurança")
        pass_old = st.text_input("Senha Atual", type="password", key="menu_old_p")
        pass_new = st.text_input("Nova Senha", type="password", key="menu_new_p")
        if st.button("Atualizar Senha", key="btn_save_pass"):
            if update_password_db(st.session_state["username"], pass_old, pass_new):
                st.success("Senha alterada!")
            else:
                st.error("Senha atual incorreta.")

        # Deletar Conta (Zona Perigo)
        st.markdown("---")
        st.caption("Zona de Perigo")
        if st.button("❌ Excluir Minha Conta", type="primary"):
            delete_user_db(st.session_state["username"])
            st.session_state.clear()
            st.rerun()

    # Botão Sair Principal
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("Sair da Conta (Logout)", use_container_width=True):
        st.session_state.clear()
        st.rerun()


def render_floating_menu_button():
    # Container CSS injetado
    st.markdown('<div class="floating-menu-container">', unsafe_allow_html=True)
    # Botão com key única
    if st.button("☰ Menu", key="btn_main_menu_float"):
        open_menu_modal()
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 3) LOGIN E REGISTRO
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
# 4) ROTEADOR
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

    # Login
    if not st.session_state.get("user_logged_in", False):
        render_login(logo_img)
        return

    # --- LÓGICA DE DADOS (COM CACHE PARA FICAR RÁPIDO) ---
    # Só carregamos se ainda não estiver no session_state
    if "carteira_df" not in st.session_state or st.session_state["carteira_df"] is None:
        try:
            # Usando a função cacheada que criamos lá em cima
            c_df, g_df = cached_load_user_data(st.session_state["username"])
            st.session_state["carteira_df"] = c_df
            st.session_state["gastos_df"] = g_df
            st.session_state["wallet_mode"] = not c_df.empty
            st.session_state["gastos_mode"] = not g_df.empty
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    # Renderiza Menu Flutuante
    render_floating_menu_button()

    # Barra Topo
    top_bar()

    # Página
    route_pages()

    # Footer
    st.markdown("<div class='bee-footer'>Bee Finanças App • v2.1</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()