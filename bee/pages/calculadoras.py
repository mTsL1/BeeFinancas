import streamlit as st
import math
from ..formatters import fmt_money_brl


# =========================================================
# CSS: Cards de Resultado + Botões de Navegação
# =========================================================
def _apply_calc_css():
    st.markdown("""
        <style>
          /* --- CARD DE RESULTADO --- */
          .result-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-top: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            padding: 20px;
            text-align: center;
            margin-top: 20px;
            animation: fadeIn 0.5s;
          }
          .result-label {
            font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
            color: rgba(255,255,255,0.6); margin-bottom: 8px; font-weight: 700;
          }
          .result-value {
            font-size: 28px; font-weight: 800; color: #ffffff; line-height: 1.1;
          }
          .result-sub {
            margin-top: 8px; font-size: 13px; color: #ccc;
          }

          /* --- BOTÕES DE NAVEGAÇÃO (IGUAL CARTEIRA) --- */
          div[data-testid="column"] > div > div > div > button {
             width: 100% !important; height: 60px !important;
             border: 1px solid rgba(255,255,255,0.08) !important;
             background: rgba(255, 255, 255, 0.03) !important;
             border-radius: 12px !important; transition: all 0.2s ease !important;
             font-weight: 600 !important; font-size: 14px !important;
          }
          div[data-testid="column"] > div > div > div > button:hover {
             background: rgba(255, 255, 255, 0.08) !important;
             border-color: rgba(255,255,255,0.2) !important; transform: translateY(-2px);
          }

          /* Esconde decoração padrão do streamlit nos inputs pra ficar mais limpo */
          div[data-testid="stDecoration"] { display: none; }

          @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    """, unsafe_allow_html=True)


# =========================================================
# HELPER DE NAVEGAÇÃO
# =========================================================
def _nav_btn(label: str, tab_key: str, icon: str = ""):
    """Cria um botão que atualiza a aba ativa"""
    active = st.session_state.get("calc_aba", "juros") == tab_key
    caption = f"{icon}\n{label}"

    # Se estiver ativo, usamos primary (opcional, ou mantemos o estilo via CSS)
    if st.button(caption, type="primary" if active else "secondary", use_container_width=True,
                 key=f"btn_calc_{tab_key}"):
        st.session_state["calc_aba"] = tab_key
        st.rerun()


# =========================================================
# TELAS INDIVIDUAIS
# =========================================================

def _render_juros():
    st.markdown("#### 📈 Juros Compostos")
    st.caption("Simule o poder do tempo e dos aportes constantes.")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        vp = c1.number_input("Valor Inicial (R$)", value=1000.0, step=100.0)
        pmt = c2.number_input("Aporte Mensal (R$)", value=500.0, step=50.0)
        taxa = c3.number_input("Taxa Anual (%)", value=10.0, step=0.1)
        anos = st.slider("Período (Anos)", 1, 50, 10)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calcular", type="primary", use_container_width=True):
            r = (taxa / 100) / 12
            n = anos * 12
            fv = vp * (1 + r) ** n + pmt * (((1 + r) ** n - 1) / r)
            total_investido = vp + (pmt * n)
            total_juros = fv - total_investido

            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">MONTANTE FINAL</div>
                <div class="result-value">{fmt_money_brl(fv, 2)}</div>
                <div class="result-sub">
                    Investido: <b>{fmt_money_brl(total_investido, 2)}</b> | 
                    Juros: <b style="color:#4ade80;">{fmt_money_brl(total_juros, 2)}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)


def _render_aluguel():
    st.markdown("#### 🏠 Alugar vs Financiar")
    st.caption("Comparativo financeiro simples.")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        valor_imovel = c1.number_input("Valor do Imóvel", value=500000.0, step=10000.0)
        taxa_fin = c2.number_input("Taxa Financiamento (% a.a.)", value=9.5, step=0.1)
        taxa_inv = c2.number_input("Rendimento Investimento (% a.a.)", value=11.0, step=0.1)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Simular", type="primary", use_container_width=True):
            # Conta de padaria para estimativa
            custo_total_fin = valor_imovel * (1 + (taxa_fin / 100) * 1.5)

            # Cenário Investidor
            entrada = valor_imovel * 0.20
            pot_inv = entrada * (1 + (taxa_inv / 100)) ** 30

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div class="result-card" style="border-top-color:#f87171;">
                    <div class="result-label">CUSTO FINANCIAMENTO</div>
                    <div class="result-value">{fmt_money_brl(custo_total_fin, 2)}</div>
                    <div class="result-sub">Pago ao banco (aprox.)</div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div class="result-card" style="border-top-color:#4ade80;">
                    <div class="result-label">SE INVESTIR A ENTRADA</div>
                    <div class="result-value">{fmt_money_brl(pot_inv, 2)}</div>
                    <div class="result-sub">Em 30 anos (20% inicial)</div>
                </div>
                """, unsafe_allow_html=True)


def _render_milhao():
    st.markdown("#### 💰 Calculadora do Milhão")
    st.caption("Quanto tempo falta?")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        invest_mensal = c1.number_input("Aporte Mensal (R$)", value=2000.0, step=100.0)
        taxa_anual = c2.number_input("Taxa Real (% a.a.)", value=10.0, step=0.1)
        meta = 1_000_000

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calcular Tempo", type="primary", use_container_width=True):
            r = (taxa_anual / 100) / 12
            if invest_mensal <= 0 or r <= 0:
                st.warning("Insira valores maiores que zero.")
            else:
                n_meses = math.log((meta * r) / invest_mensal + 1) / math.log(1 + r)
                anos = n_meses / 12

                st.markdown(f"""
                <div class="result-card">
                    <div class="result-label">VOCÊ CHEGA LÁ EM</div>
                    <div class="result-value">{anos:.1f} ANOS</div>
                    <div class="result-sub">Aportando {fmt_money_brl(invest_mensal, 2)}/mês</div>
                </div>
                """, unsafe_allow_html=True)


def _render_renda_fixa():
    st.markdown("#### 🏦 Simulador Renda Fixa")
    st.caption("Rentabilidade bruta CDB/LCI.")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        val = c1.number_input("Valor (R$)", value=1000.0, step=100.0)
        cdi = c2.number_input("CDI/Selic (% a.a.)", value=13.0, step=0.1)
        pct_cdi = st.slider("% do CDI", 80, 150, 100)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calcular (1 Ano)", type="primary", use_container_width=True):
            taxa_eff = (cdi * (pct_cdi / 100)) / 100
            total_1y = val * (1 + taxa_eff)
            lucro = total_1y - val

            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">SALDO EM 1 ANO</div>
                <div class="result-value">{fmt_money_brl(total_1y, 2)}</div>
                <div class="result-sub">Rendimento: <b style="color:#4ade80;">+ {fmt_money_brl(lucro, 2)}</b></div>
            </div>
            """, unsafe_allow_html=True)


# =========================================================
# MAIN RENDER
# =========================================================
def render_calculadoras():
    _apply_calc_css()
    st.markdown("## 🧮 Calculadoras")

    # Inicializa estado da aba
    if "calc_aba" not in st.session_state:
        st.session_state["calc_aba"] = "juros"

    # --- MENU DE NAVEGAÇÃO (BOTÕES) ---
    n1, n2, n3, n4 = st.columns(4, gap="small")

    with n1:
        _nav_btn("Juros", "juros", "📈")
    with n2:
        _nav_btn("Imóvel", "aluguel", "🏠")
    with n3:
        _nav_btn("Milhão", "milhao", "💰")
    with n4:
        _nav_btn("Renda Fixa", "rf", "🏦")

    st.markdown("---")

    # --- CONTEÚDO ---
    aba = st.session_state["calc_aba"]

    if aba == "juros":
        _render_juros()
    elif aba == "aluguel":
        _render_aluguel()
    elif aba == "milhao":
        _render_milhao()
    elif aba == "rf":
        _render_renda_fixa()