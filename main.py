import warnings
import logging
from datetime import datetime, timedelta, timezone  # <--- ADICIONEI timedelta e timezone AQUI
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
    # Inicializa estado de privacidade se não existir
    if "privacy_mode" not in st.session_state:
        st.session_state["privacy_mode"] = False

    st.markdown(
        """
        <style>
        .clock-box {
            display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
            padding: 10px 15px; border-radius: 12px;
            color: #FFD700; font-family: monospace; font-size: 16px; font-weight: bold;
            height: 46px; /* Mesma altura do botão */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Layout: Relógio | Espaço | Botão Olho
    c_clock, c_eye, _ = st.columns([2.5, 1, 6])  # Ajuste os pesos se quiser mover p/ direita

    with c_clock:
        # --- CORREÇÃO DE FUSO HORÁRIO (BRASIL UTC-3) ---
        fuso_horario = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso_horario).strftime("%d/%m/%Y %H:%M")

        st.markdown(f'<div class="clock-box">🕒 {agora}</div>', unsafe_allow_html=True)

    with c_eye:
        # Define ícone e texto
        is_hidden = st.session_state["privacy_mode"]
        icon = "🙈" if is_hidden else "👁️"
        # Botão Toggle
        if st.button(f"{icon}", use_container_width=True, help="Ocultar/Mostrar valores"):
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
        .floating-menu-container { position: fixed; top: 20px; right: 20px; z-index: 999999; }
        .floating-menu-container button {
            background-color: #FFD700 !important; color: #111 !important; border: none !important;
            border-radius: 8px !important; padding: 8px 16px !important; font-weight: 800 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        .floating-menu-container button:hover { opacity: 0.9; transform: scale(1.02); }
        .bee-footer { margin-top: 40px; padding: 20px; text-align: center; font-size: 11px; opacity: 0.4; }

        /* Ajuste fino para alinhar botão do olho com o relógio */
        div[data-testid="column"] button {
            min-height: 46px !important;
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# CONFIG POP-UP (⚙️)
# =============================================================================
@st.dialog("⚙️ Configurações")
def open_config_modal():
    st.session_state["open_config"] = False

    st.caption("🔒 Segurança da conta")

    with st.expander("🔒 Trocar senha", expanded=True):
        with st.form("form_change_pass"):
            old_pass = st.text_input("Senha atual", type="password")
            new_pass = st.text_input("Nova senha", type="password")
            new_pass2 = st.text_input("Confirmar nova senha", type="password")

            col_a, col_b = st.columns(2)
            with col_a:
                btn_change = st.form_submit_button("Salvar nova senha", type="primary", use_container_width=True)
            with col_b:
                btn_cancel = st.form_submit_button("Cancelar", use_container_width=True)

            if btn_cancel:
                st.rerun()

            if btn_change:
                if not old_pass or not new_pass:
                    st.warning("Preencha a senha atual e a nova senha.")
                elif new_pass != new_pass2:
                    st.error("A confirmação da senha não confere.")
                elif len(new_pass) < 4:
                    st.error("A nova senha está muito curta.")
                else:
                    ok = update_password_db(st.session_state.get("username", ""), old_pass, new_pass)
                    if ok:
                        st.success("Senha atualizada com sucesso ✅")
                    else:
                        st.error("Senha atual incorreta.")

    st.divider()
    st.caption("🗑️ Perigo")

    with st.expander("🗑️ Deletar conta", expanded=False):
        st.error("Isso apaga sua conta e seus dados. Essa ação não pode ser desfeita.")
        confirm = st.checkbox("Eu entendo e quero deletar minha conta", value=False)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Deletar agora", use_container_width=True, disabled=not confirm):
                try:
                    delete_user_db(st.session_state.get("username", ""))
                except Exception:
                    pass
                st.session_state.clear()
                st.success("Conta deletada. Até mais 👋")
                st.rerun()

        with col2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()


# =============================================================================
# MENU POP-UP (GRID STYLE)
# =============================================================================
@st.dialog("🐝 Menu Principal")
def open_menu_modal():
    def change_page(new_page):
        st.session_state["page"] = new_page
        keys_to_clear = ["ativo_selecionado", "popup_ativo", "show_details", "selected_ticker", "open_modal",
                         "editing_transaction"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown("<div style='margin-bottom: 10px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        if st.button("🏠\nHome", use_container_width=True): change_page("🏠 Home")
    with c2:
        if st.button("💼\nCarteira", use_container_width=True): change_page("💼 Carteira")
    with c3:
        if st.button("💸\nControle", use_container_width=True): change_page("💸 Controle")

    st.markdown("<div style='height: 5px'></div>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3, gap="small")
    with c4:
        if st.button("🔍\nAnalisar", use_container_width=True): change_page("🔍 Analisar")
    with c5:
        if st.button("📰\nNotícias", use_container_width=True): change_page("📰 Notícias")
    with c6:
        if st.button("🧮\nCalc", use_container_width=True): change_page("🧮 Calculadoras")

    st.markdown("<div style='height: 5px'></div>", unsafe_allow_html=True)

    c7, c8, c9 = st.columns(3, gap="small")
    with c7:
        if st.button("🎓\nAcademy", use_container_width=True): change_page("🎓 Bee Academy")
    with c8:
        if st.button("⚙️\nConfig", use_container_width=True):
            st.session_state["open_config"] = True
            st.rerun()
    with c9:
        if st.button("🚪\nSair", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def render_floating_menu_button():
    st.markdown('<div class="floating-menu-container">', unsafe_allow_html=True)
    if st.button("☰ Menu", key="btn_main_menu_float"):
        open_menu_modal()
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# LOGIN & ROUTER
# =============================================================================
def render_login(logo_img):
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    cols = st.columns([1, 6, 1])
    with cols[1]:
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
                if st.form_submit_button("Acessar Painel", type="primary", use_container_width=True):
                    name = login_user(l_user, l_pass)
                    if name:
                        st.session_state["user_logged_in"] = True
                        st.session_state["username"] = l_user
                        # Salva nome no state para usar no Home
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


def route_pages():
    page = st.session_state.get("page", "🏠 Home")
    if page == "🏠 Home":
        from bee.pages.home import render_home
        render_home()
    elif page == "📰 Notícias":
        from bee.pages.noticias import render_noticias
        render_noticias()
    elif page == "🔍 Analisar":
        from bee.pages.analisar import render_analisar
        render_analisar()
    elif page == "💼 Carteira":
        from bee.pages.carteira import render_carteira
        render_carteira()
    elif page == "💸 Controle":
        from bee.pages.controle import render_controle
        render_controle()
    elif page == "🧮 Calculadoras":
        from bee.pages.calculadoras import render_calculadoras
        render_calculadoras()
    elif page == "🎓 Bee Academy":
        from bee.pages.academy import render_academy
        render_academy()
    else:
        from bee.pages.home import render_home
        render_home()


def main():
    logo_img = apply_page_config()
    apply_theme_css()
    apply_app_shell_css()
    init_session_state()
    init_db()
    init_academy_db()

    # Garante que o modo privacidade existe no session_state
    if "privacy_mode" not in st.session_state:
        st.session_state["privacy_mode"] = False

    if not st.session_state.get("user_logged_in", False):
        render_login(logo_img)
        return

    if "carteira_df" not in st.session_state:
        c_df, g_df = cached_load_user_data(st.session_state["username"])
        st.session_state["carteira_df"] = c_df
        st.session_state["gastos_df"] = g_df

    # Renderiza a barra com Relógio e Botão de Privacidade
    render_top_bar_with_privacy()
    render_floating_menu_button()

    if st.session_state.get("open_config", False):
        open_config_modal()

    route_pages()

    st.markdown("<div class='bee-footer'>Bee Finanças • Modo Turbo</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()