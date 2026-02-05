import warnings
warnings.filterwarnings("ignore")

import streamlit as st

from bee.safe_imports import yf, go, px, dtparser, GoogleTranslator
from bee.theme import apply_page_config, apply_theme_css, apply_bee_light_css
from bee.state import init_session_state
from bee.db import init_db, login_user, create_user, load_user_data_db, update_password_db, delete_user_db
from bee.components import nav_btn, sidebar_market_monitor, top_bar
from bee.pages.home import render_home
from bee.pages.noticias import render_noticias
from bee.pages.analisar import render_analisar
from bee.pages.carteira import render_carteira
from bee.pages.controle import render_controle
from bee.pages.calculadoras import render_calculadoras


def render_login(logo_img):
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

                    c_df, g_df = load_user_data_db(l_user)
                    st.session_state["carteira_df"] = c_df
                    st.session_state["gastos_df"] = g_df
                    if not c_df.empty:
                        st.session_state["wallet_mode"] = True
                    if not g_df.empty:
                        st.session_state["gastos_mode"] = True
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

    st.stop()


def render_sidebar(logo_img):
    with st.sidebar:
        if logo_img:
            st.image(logo_img, width=280)
        else:
            st.markdown("## 🐝 Bee Finanças")

        st.markdown(
            f"<div style='font-size:12px; color:gray; margin-bottom:10px'>Olá, <b>{st.session_state['user_name_display']}</b></div>",
            unsafe_allow_html=True
        )

        st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
        nav_btn("🏠 Home", "🏠 Home")
        nav_btn("📰 Notícias", "📰 Notícias")

        st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
        nav_btn("🔍 Analisar", "🔍 Analisar")
        nav_btn("💼 Carteira", "💼 Carteira")
        nav_btn("💸 Controle", "💸 Controle")
        nav_btn("🧮 Calculadoras", "🧮 Calculadoras")

        st.divider()

        sidebar_market_monitor()

        # Bee Light toggle
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        new_light = st.toggle("💡 Bee Light (mais amarelo)", value=st.session_state["bee_light"])
        if new_light != st.session_state["bee_light"]:
            st.session_state["bee_light"] = new_light
            st.rerun()

        st.markdown("---")

        # Configurações da conta
        with st.expander("⚙️ Configurações da Conta"):
            old_p = st.text_input("Senha Atual", type="password")
            new_p = st.text_input("Nova Senha", type="password")
            if st.button("Alterar Senha"):
                if update_password_db(st.session_state["username"], old_p, new_p):
                    st.success("Senha alterada com sucesso!")
                else:
                    st.error("Senha atual incorreta.")

        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state["user_logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

        # Danger zone delete
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        with st.expander("❌ Zona de Perigo"):
            st.caption("Ação irreversível. Todos os seus dados serão apagados permanentemente.")
            if st.button("Deletar Minha Conta", type="primary"):
                delete_user_db(st.session_state["username"])
                st.session_state.clear()
                st.rerun()


def route_pages():
    page = st.session_state["page"]
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
    else:
        render_home()


def main():
    # 1) Page config + theme (tem que ser antes de qualquer st.* visual)
    logo_img = apply_page_config()
    apply_theme_css()

    # 2) State + DB
    init_session_state()
    init_db()

    # 3) Bee light override
    if st.session_state.get("bee_light"):
        apply_bee_light_css()

    # 4) Login
    if not st.session_state["user_logged_in"]:
        render_login(logo_img)

    # 5) Sidebar + top bar + pages
    render_sidebar(logo_img)
    top_bar()

    route_pages()

    # Footer
    from bee.config import APP_VERSION
    st.markdown(
        f"""
<div class="bee-footer">
  <div>Bee Finanças</div>
  <div>{APP_VERSION}</div>
</div>
""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
