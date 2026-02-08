import warnings
import logging
from datetime import datetime, timedelta, timezone
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# -----------------------------------------------------------------------------
warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from bee.theme import apply_page_config, apply_theme_css
from bee.state import init_session_state
from bee.db import (
    init_db,
    login_user,
    create_user,
    load_user_data_db,
    update_password_db,
    delete_user_db,
)
from bee.academy.progress import init_academy_db


# =============================================================================
# CACHE & HELPERS
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def cached_load_user_data(username):
    return load_user_data_db(username)


def render_top_bar_with_privacy():
    if "privacy_mode" not in st.session_state:
        st.session_state["privacy_mode"] = False

    st.markdown("""
        <style>
        .clock-box {
            display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            padding: 8px 12px; border-radius: 10px;
            color: #FFD700; font-family: monospace; font-size: 15px; font-weight: bold;
            height: 44px;
        }
        </style>
    """, unsafe_allow_html=True)

    c_clock, c_eye, _ = st.columns([2.2, 0.8, 6])

    with c_clock:
        fuso_horario = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso_horario).strftime("%d/%m %H:%M")
        st.markdown(f'<div class="clock-box">🕒 {agora}</div>', unsafe_allow_html=True)

    with c_eye:
        is_hidden = st.session_state["privacy_mode"]
        icon = "🙈" if is_hidden else "👁️"
        if st.button(f"{icon}", use_container_width=True, help="Privacidade"):
            st.session_state["privacy_mode"] = not is_hidden
            st.rerun()

    st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)


def apply_app_shell_css():
    st.markdown(
        """
        <style>
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }
        header[data-testid="stHeader"] { opacity: 0; pointer-events: none; height: 0px; }
        section[data-testid="stSidebar"] { display: none !important; }

        .block-container { padding-top: 1rem !important; max-width: 100%; }

        /* Botão Flutuante Menu */
        .floating-menu-container { position: fixed; top: 15px; right: 15px; z-index: 999999; }
        .floating-menu-container button {
            background: #FFD700 !important; color: #000 !important; border: none !important;
            border-radius: 8px !important; font-weight: 800 !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
        }
        .floating-menu-container button:hover { transform: scale(1.05); }

        .bee-footer { margin-top: 50px; text-align: center; font-size: 10px; opacity: 0.3; }

        /* Ajuste botões gerais da barra superior */
        div[data-testid="column"] button { min-height: 44px !important; border-radius: 10px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# CONFIG POP-UP
# =============================================================================
@st.dialog("⚙️ Configurações")
def open_config_modal():
    st.session_state["open_config"] = False
    st.caption("🔒 Segurança")

    with st.expander("Trocar senha", expanded=True):
        with st.form("form_change_pass"):
            old = st.text_input("Senha atual", type="password")
            new = st.text_input("Nova senha", type="password")
            new2 = st.text_input("Confirmar", type="password")

            if st.form_submit_button("Atualizar Senha", type="primary", use_container_width=True):
                if new != new2:
                    st.error("Senhas não conferem.")
                elif len(new) < 4:
                    st.error("Senha muito curta.")
                elif update_password_db(st.session_state.get("username", ""), old, new):
                    st.success("Sucesso! ✅")
                else:
                    st.error("Senha atual incorreta.")

    st.divider()
    if st.button("Sair da Conta", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# =============================================================================
# MENU POP-UP
# =============================================================================
@st.dialog("🐝 Navegação")
def open_menu_modal():
    def go(pg):
        st.session_state["page"] = pg
        for k in ["ativo_selecionado", "popup_ativo", "show_details", "selected_ticker", "open_modal"]:
            if k in st.session_state: del st.session_state[k]
        st.rerun()

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        if st.button("🏠\nHome", use_container_width=True): go("🏠 Home")
    with c2:
        if st.button("💼\nCarteira", use_container_width=True): go("💼 Carteira")
    with c3:
        if st.button("💸\nControle", use_container_width=True): go("💸 Controle")

    st.write("")
    c4, c5, c6 = st.columns(3, gap="small")
    with c4:
        if st.button("🔍\nAnalisar", use_container_width=True): go("🔍 Analisar")
    with c5:
        if st.button("📰\nNotícias", use_container_width=True): go("📰 Notícias")
    with c6:
        if st.button("🧮\nCalc", use_container_width=True): go("🧮 Calculadoras")

    st.write("")
    c7, c8 = st.columns([1, 1], gap="small")
    with c7:
        if st.button("🎓\nAcademy", use_container_width=True): go("🎓 Bee Academy")
    with c8:
        if st.button("⚙️\nConfig", use_container_width=True):
            st.session_state["open_config"] = True
            st.rerun()


def render_floating_menu_button():
    st.markdown('<div class="floating-menu-container">', unsafe_allow_html=True)
    if st.button("☰", key="btn_main_menu_float", help="Menu Principal"):
        open_menu_modal()
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# TELA DE LOGIN (CORRIGIDA - OLHO TRANSPARENTE)
# =============================================================================
def render_login(logo_img):
    st.markdown("""
    <style>
        /* --- CORREÇÃO DEFINITIVA DO OLHO DA SENHA --- */
        /* Alvo: Botões dentro do input que tenham "password" no título (Show/Hide) */
        div[data-baseweb="input"] > div > button[title*="password"] {
            background: transparent !important;  /* Remove o fundo amarelo */
            border: none !important;             /* Remove borda */
            box-shadow: none !important;         /* Remove sombra */
            color: rgba(255, 255, 255, 0.6) !important; /* Cor do ícone discreta */
            margin: 0 !important;
            height: auto !important;
            transform: none !important; /* Impede que ele cresça no hover */
        }
        /* Hover do ícone do olho */
        div[data-baseweb="input"] > div > button[title*="password"]:hover {
            background: transparent !important;
            color: rgba(255, 255, 255, 1.0) !important; /* Fica branco ao passar o mouse */
            box-shadow: none !important;
        }

        /* --- Botões PRINCIPAIS do Formulário (Entrar/Criar) --- */
        /* Usamos um seletor mais específico para pegar só o botão de submit */
        div[data-testid="stForm"] > div > div > button[kind="primaryFormSubmit"] {
            background: linear-gradient(135deg, #FFD700 0%, #FFB300 100%) !important;
            color: #000 !important;
            border: none !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            height: 48px !important;
            border-radius: 12px !important;
            margin-top: 10px !important;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2) !important;
        }
        div[data-testid="stForm"] > div > div > button[kind="primaryFormSubmit"]:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4) !important;
        }

        /* Títulos Centralizados */
        .login-title {
            text-align: center; font-size: 32px; font-weight: 900;
            background: -webkit-linear-gradient(45deg, #FFD700, #ffae00);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }
        .login-sub {
            text-align: center; font-size: 14px; opacity: 0.6; margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Layout Responsivo
    col_l, col_main, col_r = st.columns([1, 1.2, 1])

    with col_main:
        st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)

        # LOGO CENTRALIZADA
        if logo_img:
            c_img_l, c_img_c, c_img_r = st.columns([1, 2, 1])
            with c_img_c:
                st.image(logo_img, use_container_width=True)

        st.markdown('<div class="login-title">Bee Finanças</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sua central de inteligência financeira</div>', unsafe_allow_html=True)

        # Card Nativo
        with st.container(border=True):
            tab_entrar, tab_criar = st.tabs(["Acessar Conta", "Criar Nova"])

            with tab_entrar:
                with st.form("login_form"):
                    st.text_input("Usuário", key="l_u", placeholder="Digite seu usuário")
                    st.text_input("Senha", type="password", key="l_p", placeholder="••••••")

                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        u = st.session_state.l_u
                        p = st.session_state.l_p
                        name = login_user(u, p)
                        if name:
                            st.session_state.user_logged_in = True
                            st.session_state.username = u
                            st.session_state.user_name_display = name
                            try:
                                c, g = cached_load_user_data(u)
                                st.session_state.carteira_df = c
                                st.session_state.gastos_df = g
                            except:
                                pass
                            st.session_state.page = "🏠 Home"
                            st.rerun()
                        else:
                            st.error("Dados incorretos.")

            with tab_criar:
                with st.form("register_form"):
                    new_u = st.text_input("Novo Usuário", placeholder="Ex: mateus_bee")
                    new_n = st.text_input("Seu Nome", placeholder="Ex: Mateus")
                    new_p = st.text_input("Senha", type="password")

                    if st.form_submit_button("CRIAR CONTA", use_container_width=True):
                        if len(new_p) < 4:
                            st.warning("Senha muito curta.")
                        elif create_user(new_u, new_p, new_n):
                            st.success("Conta criada! Faça login.")
                        else:
                            st.error("Usuário já existe.")

    st.stop()


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def route_pages():
    pg = st.session_state.get("page", "🏠 Home")
    if pg == "🏠 Home":
        from bee.pages.home import render_home;
        render_home()
    elif pg == "💼 Carteira":
        from bee.pages.carteira import render_carteira;
        render_carteira()
    elif pg == "💸 Controle":
        from bee.pages.controle import render_controle;
        render_controle()
    elif pg == "🔍 Analisar":
        from bee.pages.analisar import render_analisar;
        render_analisar()
    elif pg == "📰 Notícias":
        from bee.pages.noticias import render_noticias;
        render_noticias()
    elif pg == "🧮 Calculadoras":
        from bee.pages.calculadoras import render_calculadoras;
        render_calculadoras()
    elif pg == "🎓 Bee Academy":
        from bee.pages.academy import render_academy;
        render_academy()
    else:
        from bee.pages.home import render_home;
        render_home()


def main():
    logo_img = apply_page_config()
    apply_theme_css()
    apply_app_shell_css()
    init_session_state()
    init_db()
    init_academy_db()

    if "privacy_mode" not in st.session_state: st.session_state["privacy_mode"] = False

    if not st.session_state.get("user_logged_in", False):
        render_login(logo_img)
        return

    if "carteira_df" not in st.session_state:
        c_df, g_df = cached_load_user_data(st.session_state["username"])
        st.session_state["carteira_df"] = c_df
        st.session_state["gastos_df"] = g_df

    render_top_bar_with_privacy()
    render_floating_menu_button()

    if st.session_state.get("open_config", False):
        open_config_modal()

    route_pages()

    st.markdown("<div class='bee-footer'>Bee Finanças • Modo Turbo</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()