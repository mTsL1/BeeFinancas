import warnings
warnings.filterwarnings("ignore")

import streamlit as st

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

from bee.pages.home import render_home
from bee.pages.noticias import render_noticias
from bee.pages.analisar import render_analisar
from bee.pages.carteira import render_carteira
from bee.pages.controle import render_controle
from bee.pages.calculadoras import render_calculadoras

# ✅ Bee Academy
from bee.pages.academy import render_academy
from bee.academy.progress import init_academy_db


# -----------------------------------------------------------------------------
# 0) CSS/JS (APP-LIKE)
# -----------------------------------------------------------------------------
def apply_app_shell_css():
    """
    Remove 'cara de Streamlit' e melhora spacing/visual (mobile-first).
    Chamar o mais cedo possível (logo após apply_page_config).
    """
    st.markdown(
        """
<style>
/* =========================
   HIDE STREAMLIT CHROME
   ========================= */
#MainMenu { display:none !important; }
footer { display:none !important; }
header { display:none !important; }
.stDeployButton { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stStatusWidget"] { display:none !important; }

/* =========================
   GLOBAL LAYOUT
   ========================= */
html, body { overscroll-behavior: none; }
.block-container {
  padding-top: 0.8rem !important;
  padding-bottom: 0.6rem !important;
  padding-left: 0.9rem !important;
  padding-right: 0.9rem !important;
  max-width: 1200px;
}
@media (max-width: 768px) {
  .block-container {
    padding-top: 0.6rem !important;
    padding-left: 0.7rem !important;
    padding-right: 0.7rem !important;
  }
}

/* =========================
   SIDEBAR (APP FEEL)
   ========================= */
section[data-testid="stSidebar"] {
  border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 0.8rem !important;
}

/* =========================
   BUTTONS / INPUTS (TOUCH)
   ========================= */
.stButton button {
  border-radius: 14px !important;
  padding: 0.65rem 0.9rem !important;
  font-weight: 800 !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox div, .stNumberInput input {
  border-radius: 12px !important;
}
@media (max-width: 768px) {
  .stButton button { width: 100% !important; }
}

/* =========================
   METRICS (CONSISTENTE)
   ========================= */
[data-testid="stMetricValue"] {
  font-size: 26px !important;
  font-weight: 800 !important;
  line-height: 1.1 !important;
}
[data-testid="stMetricLabel"] {
  font-size: 13px !important;
  opacity: 0.75;
}
[data-testid="stMetric"] {
  background: rgba(255,255,255,0.03);
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.06);
}

/* =========================
   HEADERS - MENOS "GRITÃO"
   ========================= */
h1 { font-size: 1.65rem !important; }
h2 { font-size: 1.25rem !important; }
h3 { font-size: 1.05rem !important; }
@media (max-width: 768px) {
  h1 { font-size: 1.45rem !important; }
  h2 { font-size: 1.18rem !important; }
}

/* =========================
   APP FOOTER (SEU)
   ========================= */
.bee-footer {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  opacity: 0.7;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def mobile_menu_fab():
    """
    Botão flutuante no MOBILE pra abrir/fechar sidebar com 1 toque.
    """
    st.markdown(
        """
<style>
  @media (max-width: 768px) {
    .bee-fab-menu {
      position: fixed;
      bottom: 18px;
      right: 16px;
      z-index: 999999;
      background: rgba(255, 215, 0, 0.95);
      color: #111;
      border-radius: 999px;
      padding: 12px 16px;
      font-weight: 900;
      box-shadow: 0 10px 28px rgba(0,0,0,0.35);
      border: 1px solid rgba(0,0,0,0.18);
      cursor: pointer;
      user-select: none;
    }
    .bee-fab-menu:active { transform: scale(0.985); }
  }
  @media (min-width: 769px) {
    .bee-fab-menu { display: none; }
  }
</style>

<div class="bee-fab-menu" id="beeFabMenu">☰ Menu</div>

<script>
(function(){
  const doc = window.parent.document;

  function findToggle() {
    // Streamlit muda seletores com o tempo — tentamos alguns comuns.
    const selectors = [
      'button[aria-label="Toggle sidebar"]',
      'button[title="Toggle sidebar"]',
      'button[kind="headerNoPadding"]',
      'header button'
    ];
    for (const sel of selectors) {
      const b = doc.querySelector(sel);
      if (b) return b;
    }
    return null;
  }

  const fab = doc.getElementById('beeFabMenu') || document.getElementById('beeFabMenu');
  if (!fab) return;

  fab.addEventListener('click', () => {
    const btn = findToggle();
    if (btn) btn.click();
  });
})();
</script>
        """,
        unsafe_allow_html=True,
    )


def mobile_swipe_sidebar():
    """
    Swipe nas bordas:
    - borda esquerda -> direita = abre
    - borda direita -> esquerda = fecha
    """
    st.markdown(
        """
<script>
(function(){
  const doc = window.parent.document;

  function findToggle() {
    return (
      doc.querySelector('button[aria-label="Toggle sidebar"]') ||
      doc.querySelector('button[title="Toggle sidebar"]') ||
      doc.querySelector('button[kind="headerNoPadding"]') ||
      doc.querySelector('header button')
    );
  }

  let startX = 0, endX = 0;

  doc.addEventListener('touchstart', (e) => {
    if (!e.touches || e.touches.length === 0) return;
    startX = e.touches[0].clientX;
    endX = startX;
  }, { passive: true });

  doc.addEventListener('touchmove', (e) => {
    if (!e.touches || e.touches.length === 0) return;
    endX = e.touches[0].clientX;
  }, { passive: true });

  doc.addEventListener('touchend', () => {
    const diff = endX - startX;
    const edge = 22; // px
    const threshold = 85;

    // abre
    if (startX <= edge && diff >= threshold) {
      const btn = findToggle();
      if (btn) btn.click();
      return;
    }
    // fecha
    if (startX >= (window.innerWidth - edge) && diff <= -threshold) {
      const btn = findToggle();
      if (btn) btn.click();
      return;
    }
  }, { passive: true });
})();
</script>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# LOGIN (RESPONSIVO)
# -----------------------------------------------------------------------------
def render_login(logo_img):
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # Layout responsivo: no mobile, 1 coluna; no desktop, centraliza
    is_mobile = st.session_state.get("_is_mobile_hint", False)
    if is_mobile:
        cols = st.columns([1])
        center = cols[0]
    else:
        col1, col2, col3 = st.columns([1, 1.35, 1])
        center = col2

    with center:
        st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
        if logo_img:
            st.image(logo_img, width=150)
        else:
            st.markdown("# 🐝 Bee Finanças")
        st.markdown("</div>", unsafe_allow_html=True)

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

                    st.session_state["wallet_mode"] = not c_df.empty
                    st.session_state["gastos_mode"] = not g_df.empty

                    if "page" not in st.session_state or not st.session_state["page"]:
                        st.session_state["page"] = "🏠 Home"

                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        with tab_register:
            r_user = st.text_input("Escolha um Usuário", key="r_user")
            r_name = st.text_input("Seu Nome", key="r_name")
            r_pass = st.text_input("Escolha uma Senha", type="password", key="r_pass")

            if st.button("Criar Conta", use_container_width=True):
                if not r_user or not r_pass or not r_name:
                    st.warning("Preencha Usuário, Nome e Senha.")
                else:
                    if create_user(r_user, r_pass, r_name):
                        st.success("Conta criada! Faça login na aba 'Entrar'.")
                    else:
                        st.error("Usuário já existe.")

    st.stop()


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
def render_sidebar(logo_img):
    with st.sidebar:
        if logo_img:
            st.image(logo_img, width=260)
        else:
            st.markdown("## 🐝 Bee Finanças")

        st.markdown(
            f"<div style='font-size:12px; opacity:0.75; margin-bottom:10px'>Olá, <b>{st.session_state.get('user_name_display','')}</b></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<p class='menu-header'>Hub</p>", unsafe_allow_html=True)
        nav_btn("🏠 Home", "🏠 Home")
        nav_btn("📰 Notícias", "📰 Notícias")

        st.markdown("<p class='menu-header'>Tools</p>", unsafe_allow_html=True)
        nav_btn("🔍 Analisar", "🔍 Analisar")
        nav_btn("💼 Carteira", "💼 Carteira")
        nav_btn("💸 Controle", "💸 Controle")
        nav_btn("🧮 Calculadoras", "🧮 Calculadoras")

        st.markdown("<p class='menu-header'>Aprender</p>", unsafe_allow_html=True)
        nav_btn("🎓 Bee Academy", "🎓 Bee Academy")

        st.divider()
        sidebar_market_monitor()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        new_light = st.toggle("💡 Bee Light (mais amarelo)", value=st.session_state.get("bee_light", False))
        if new_light != st.session_state.get("bee_light", False):
            st.session_state["bee_light"] = new_light
            st.rerun()

        st.markdown("---")

        with st.expander("⚙️ Configurações da Conta"):
            old_p = st.text_input("Senha Atual", type="password", key="old_pass")
            new_p = st.text_input("Nova Senha", type="password", key="new_pass")
            if st.button("Alterar Senha", key="btn_change_pass"):
                if update_password_db(st.session_state["username"], old_p, new_p):
                    st.success("Senha alterada com sucesso!")
                else:
                    st.error("Senha atual incorreta ou inválida.")

        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state["user_logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        with st.expander("❌ Zona de Perigo"):
            st.caption("Ação irreversível. Apaga tudo.")
            if st.button("Deletar Minha Conta", type="primary", key="btn_delete_account"):
                delete_user_db(st.session_state["username"])
                st.session_state.clear()
                st.rerun()


# -----------------------------------------------------------------------------
# ROUTER
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    # 1) Config logo + theme
    logo_img = apply_page_config()

    # 2) CSS base do seu tema + shell (ocultar streamlit + mobile polish)
    apply_theme_css()
    apply_app_shell_css()

    # 3) State + DB
    init_session_state()
    init_db()
    init_academy_db()

    # 4) Bee Light (depois de state)
    if st.session_state.get("bee_light"):
        apply_bee_light_css()

    # 5) Dica simples pra detectar mobile (não perfeito, mas ajuda no login)
    # (Streamlit não dá user agent direto sem hack — então só usamos hint leve.)
    # Você pode remover isso sem impactar.
    if "_is_mobile_hint" not in st.session_state:
        st.session_state["_is_mobile_hint"] = False
        st.markdown(
            """
<script>
(function(){
  const w = window.innerWidth || 9999;
  const isMobile = w <= 768;
  const doc = window.parent.document;
  // hack leve: escreve num atributo do body que o Streamlit não bloqueia.
  doc.body.setAttribute('data-bee-mobile', isMobile ? '1' : '0');
})();
</script>
            """,
            unsafe_allow_html=True,
        )
        # não rerun aqui pra não dar loop

    # 6) Login
    if not st.session_state.get("user_logged_in", False):
        render_login(logo_img)

    # 7) App principal
    render_sidebar(logo_img)

    # sua top bar (mantive)
    top_bar()

    # mobile helpers
    mobile_menu_fab()
    mobile_swipe_sidebar()

    # pages
    route_pages()

    # footer
    try:
        from bee.config import APP_VERSION
        ver = APP_VERSION
    except Exception:
        ver = "v?"

    st.markdown(
        f"<div class='bee-footer'><div><b>Bee Finanças</b></div><div>{ver}</div></div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
