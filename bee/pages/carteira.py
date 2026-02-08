import math
import pandas as pd
import streamlit as st

# Mantendo seus imports originais
from bee.config import DB_FILE
from bee.safe_imports import px
from bee.formatters import fmt_money_brl
from bee.db import save_user_data_db, load_targets_db, save_targets_db
from bee.market_data import atualizar_precos_carteira_memory
from bee.dialogs import show_asset_details_popup

CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]


# =========================================================
# HELPERS
# =========================================================
def _ensure_wallet_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=CARTEIRA_COLS)
    df = df.copy()
    for c in CARTEIRA_COLS:
        if c not in df.columns:
            df[c] = "" if c in ["Tipo", "Ativo", "Nome", "Moeda", "Obs"] else 0.0
    return df[CARTEIRA_COLS].copy()


def _normalize_tipo(tipo: str) -> str:
    t = (tipo or "").strip()
    if not t:
        return "Ação/ETF"
    tl = t.lower()
    if "crip" in tl:
        return "Cripto"
    if "fixa" in tl or tl == "rf":
        return "Renda Fixa"
    if "ação" in tl or "acao" in tl or "etf" in tl:
        return "Ação/ETF"
    if t in ["Ação/ETF", "Cripto", "Renda Fixa", "Caixa"]:
        return t
    return "Ação/ETF"


def _classify_tipo_for_targets(df_calc: pd.DataFrame) -> pd.DataFrame:
    df = df_calc.copy()
    df["TipoBucket"] = df["Tipo"].astype(str).apply(_normalize_tipo)
    return df


def _compact_brl(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return "R$ 0"
    av = abs(v)
    if av >= 1_000_000_000:
        return f"R$ {v / 1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"R$ {v / 1_000_000:.2f}M"
    if av >= 1_000:
        return f"R$ {v / 1_000:.0f}k"
    return fmt_money_brl(v, 2)


# =========================================================
# UI / CSS (ESTILO PREMIUM)
# =========================================================
def _apply_wallet_css():
    st.markdown(
        """
        <style>
          /* --- KPI CARDS (Glassmorphism & Centralizados) --- */
          .kpi-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 25px;
          }

          .kpi-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-top: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;     
            justify-content: center; 
            text-align: center;
            min-height: 100px;
            backdrop-filter: blur(10px);
          }

          .kpi-label {
            font-size: 11px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: rgba(255,255,255,0.6);
            margin-bottom: 8px;
            font-weight: 600;
          }

          .kpi-value {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
          }

          .kpi-sub {
            margin-top: 8px;
            font-size: 13px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 5px;
          }
          .kpi-sub.pos { color: #4ade80; background: rgba(74, 222, 128, 0.12); border: 1px solid rgba(74, 222, 128, 0.2); }
          .kpi-sub.neg { color: #f87171; background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.2); }

          /* --- BOTÕES DE NAVEGAÇÃO UNIFORMES --- */
          /* Força os botões dentro das colunas de navegação a terem o mesmo tamanho e estilo */
          div[data-testid="column"] > div > div > div > button {
             width: 100% !important;
             height: 60px !important;
             border: 1px solid rgba(255,255,255,0.08) !important;
             background: rgba(255, 255, 255, 0.03) !important;
             border-radius: 12px !important;
             transition: all 0.2s ease !important;
             font-weight: 600 !important;
             font-size: 16px !important;
          }

          div[data-testid="column"] > div > div > div > button:hover {
             background: rgba(255, 255, 255, 0.08) !important;
             border-color: rgba(255,255,255,0.2) !important;
             transform: translateY(-2px);
          }

          div[data-testid="column"] > div > div > div > button:focus {
             border-color: #ffd700 !important;
             box-shadow: 0 0 10px rgba(255, 215, 0, 0.15) !important;
          }

          /* --- AJUSTES GERAIS --- */
          div[data-testid="stDataFrame"] { width: 100% !important; }

          /* Responsividade para telas pequenas */
          @media (max-width: 768px){
            .kpi-container { grid-template-columns: 1fr; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# MODALS
# =========================================================
@st.dialog("➕ Adicionar novo ativo")
def _dialog_add_asset(username: str):
    df = _ensure_wallet_columns(
        st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS))
    )
    st.caption("Preencha os dados do ativo.")

    c1, c2, c3 = st.columns([1.2, 1.2, 0.8])
    f_tipo = c1.selectbox(
        "Tipo", ["Ação/ETF", "Cripto", "Renda Fixa", "Caixa"], key="dlg_tipo"
    )
    f_ativo = (
        c2.text_input("Ticker", placeholder="PETR4", key="dlg_ativo")
        .upper()
        .strip()
    )
    f_moeda = c3.selectbox("Moeda", ["BRL", "USD"], key="dlg_moeda")

    c4, c5 = st.columns(2)
    f_qtd = c4.number_input("Quantidade", min_value=0.0, step=1.0, key="dlg_qtd")
    f_preco = c5.number_input(
        "Preço médio", min_value=0.0, step=0.01, format="%.2f", key="dlg_preco"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    c6, c7 = st.columns([1, 1])
    if c6.button("Cancelar", use_container_width=True):
        st.rerun()
    if c7.button("Salvar Ativo", type="primary", use_container_width=True):
        if f_ativo and f_qtd > 0:
            new_asset = {
                "Tipo": _normalize_tipo(f_tipo),
                "Ativo": f_ativo,
                "Nome": f_ativo,
                "Qtd": float(f_qtd),
                "Preco_Medio": float(f_preco),
                "Moeda": f_moeda,
                "Obs": "",
            }
            df_new = pd.concat([df, pd.DataFrame([new_asset])], ignore_index=True)
            st.session_state["carteira_df"] = _ensure_wallet_columns(df_new)
            st.session_state["wallet_mode"] = True
            save_user_data_db(
                username,
                st.session_state["carteira_df"],
                st.session_state.get("gastos_df", pd.DataFrame()),
            )
            st.toast("Ativo adicionado com sucesso!", icon="✅")
            st.rerun()
        else:
            st.warning("Preencha ticker e quantidade.")


# =========================================================
# RENDERERS
# =========================================================
def _render_targets_and_rebalance(df_calc: pd.DataFrame):
    st.markdown("### 🎯 Alocação e Rebalanceamento")
    username = st.session_state["username"]
    targets = load_targets_db(username, DB_FILE)
    keys = ["Ação/ETF", "Renda Fixa", "Cripto", "Caixa"]

    # Inputs de metas mais compactos
    cols = st.columns(4)
    new_targets = {}
    for i, k in enumerate(keys):
        with cols[i]:
            new_targets[k] = st.number_input(
                f"{k} (%)",
                0.0, 100.0, float(targets.get(k, 0.0)), 1.0,
                key=f"target_{k}",
            )

    if st.button("💾 Atualizar Metas", type="primary", use_container_width=True):
        final_targets = {k: round(float(v), 2) for k, v in new_targets.items()}
        save_targets_db(username, final_targets, DB_FILE)
        st.toast("Metas atualizadas!", icon="✅")
        st.rerun()

    dfb = _classify_tipo_for_targets(df_calc)
    total = float(dfb["Total_BRL"].sum()) if not dfb.empty else 0.0
    if total <= 0:
        return

    st.markdown("---")

    cur_val = dfb.groupby("TipoBucket")["Total_BRL"].sum().to_dict()
    cur_pct = {k: (float(cur_val.get(k, 0.0)) / total * 100.0) for k in keys}

    view = pd.DataFrame([
        {
            "Classe": k,
            "Atual %": round(cur_pct.get(k, 0.0), 2),
            "Alvo %": round(float(new_targets.get(k, 0.0)), 2),
            "Desvio %": round(cur_pct.get(k, 0.0) - float(new_targets.get(k, 0.0)), 2)
        }
        for k in keys
    ])

    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Desvio %": st.column_config.NumberColumn(format="%.2f %%")
        }
    )

    st.markdown("#### 🤖 Sugestão de Aporte")
    c_ap, c_btn = st.columns([2, 1])
    aporte = c_ap.number_input("Valor do Aporte (R$)", 0.0, step=100.0, value=1000.0)

    if aporte > 0:
        new_total = total + float(aporte)
        desired_val = {k: (float(new_targets.get(k, 0.0)) / 100.0) * new_total for k in keys}
        need = {k: max(0.0, desired_val.get(k, 0.0) - float(cur_val.get(k, 0.0))) for k in keys}
        sum_pos = float(sum(need.values()))
        if sum_pos > 0:
            recs = [
                {"Classe": k, "Sugerido (R$)": round(float(aporte) * (v / sum_pos), 2)}
                for k, v in need.items() if v > 0
            ]
            st.dataframe(
                pd.DataFrame(recs).sort_values("Sugerido (R$)", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Sugerido (R$)": st.column_config.NumberColumn(format="R$ %.2f")
                }
            )


def _render_monitor_fixed(df_calc: pd.DataFrame):
    st.markdown("### 📊 Monitor de Ativos")
    cols = ["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL", "Var_Dia_Pct"]
    live_df = df_calc[cols].copy()

    for col in cols[1:]:
        live_df[col] = pd.to_numeric(live_df[col], errors="coerce").fillna(0.0)

    live_df = live_df.sort_values("PnL_Pct", ascending=False).reset_index(drop=True)
    live_df = live_df.rename(
        columns={
            "Preco_Atual_BRL": "Cotação",
            "PnL_Pct": "Rentab %",
            "Total_BRL": "Total",
            "Var_Dia_Pct": "24h %",
            "Preco_Medio": "PM"
        }
    )

    selection = st.dataframe(
        live_df[["Ativo", "Qtd", "PM", "Cotação", "24h %", "Rentab %", "Total"]],
        column_config={
            "Qtd": st.column_config.NumberColumn(format="%.4f"),
            "PM": st.column_config.NumberColumn(format="R$ %.2f"),
            "Cotação": st.column_config.NumberColumn(format="R$ %.2f"),
            "24h %": st.column_config.NumberColumn(format="%.2f %%"),
            "Rentab %": st.column_config.NumberColumn(format="%.2f %%"),
            "Total": st.column_config.NumberColumn(format="R$ %.2f"),
        },
        hide_index=True,
        use_container_width=True,
        height=420,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selection and selection.selection.rows:
        idx = selection.selection.rows[0]
        ativo = str(live_df.iloc[idx]["Ativo"])
        if st.button(f"🔍 Ver Detalhes: {ativo}", use_container_width=True):
            show_asset_details_popup(ativo)


def _render_treemap_and_insights(df_calc: pd.DataFrame):
    if px is None:
        return

    st.markdown("### 🗺️ Visão Geral")
    left, right = st.columns([1.2, 1.0], gap="large")

    with left:
        st.markdown("**Mapa de Calor**")
        try:
            df_tree = df_calc[df_calc["Tipo"].astype(str).apply(_normalize_tipo) != "Renda Fixa"].copy()
            if not df_tree.empty:
                df_tree["_Val"] = df_tree["Total_BRL"].apply(lambda x: math.sqrt(max(0, float(x))))
                fig = px.treemap(
                    df_tree,
                    path=[px.Constant("Carteira"), "Tipo", "Ativo"],
                    values="_Val",
                    color="Var_Dia_Pct",
                    color_continuous_scale=["#ff3b30", "#1f1f1f", "#00c805"],
                    color_continuous_midpoint=0,
                )
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Adicione renda variável para ver o mapa.")
        except Exception:
            st.error("Erro ao gerar mapa.")

    with right:
        st.markdown("**Destaques**")
        df_i = df_calc.copy()
        for c in ["Total_BRL", "Var_Dia_Pct"]:
            df_i[c] = pd.to_numeric(df_i[c], errors="coerce").fillna(0.0)

        total = float(df_i["Total_BRL"].sum())

        if total > 0:
            top = df_i.sort_values("Total_BRL", ascending=False).iloc[0]
            st.metric("🏆 Maior Posição", f"{top['Ativo']}", f"{top['Total_BRL'] / total * 100:.1f}% da carteira")

            top3_pct = df_i.sort_values('Total_BRL', ascending=False).head(3)['Total_BRL'].sum() / total * 100
            st.metric("📦 Concentração Top 3", f"{top3_pct:.1f}%", "Risco de concentração")

        st.markdown("**Top Variação (Dia)**")
        df_day = df_i.sort_values("Var_Dia_Pct", ascending=False)

        col_high, col_low = st.columns(2)
        with col_high:
            st.caption("Maiores Altas")
            st.dataframe(
                df_day.head(3)[["Ativo", "Var_Dia_Pct"]].rename(columns={"Var_Dia_Pct": "%"}),
                hide_index=True, use_container_width=True,
                column_config={"%": st.column_config.NumberColumn(format="%.2f %%")}
            )
        with col_low:
            st.caption("Maiores Baixas")
            st.dataframe(
                df_day.tail(3).sort_values("Var_Dia_Pct")[["Ativo", "Var_Dia_Pct"]].rename(
                    columns={"Var_Dia_Pct": "%"}),
                hide_index=True, use_container_width=True,
                column_config={"%": st.column_config.NumberColumn(format="%.2f %%")}
            )


def _render_manage(username: str):
    st.markdown("### 🧰 Gerenciamento de Dados")
    st.info("Edite os valores diretamente na tabela abaixo.")

    df_edit = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))
    edited = st.data_editor(
        df_edit[["Tipo", "Ativo", "Qtd", "Preco_Medio", "Moeda", "Obs"]],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_carteira",
        height=500
    )

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
            edited["Tipo"] = edited["Tipo"].astype(str).apply(_normalize_tipo)
            if "Nome" not in edited.columns:
                edited["Nome"] = edited["Ativo"]
            st.session_state["carteira_df"] = _ensure_wallet_columns(edited)
            save_user_data_db(username, st.session_state["carteira_df"],
                              st.session_state.get("gastos_df", pd.DataFrame()))
            st.toast("Carteira salva com sucesso!", icon="✅")
            st.rerun()


# =========================================================
# MAIN PAGE
# =========================================================
def render_carteira():
    # 1. Aplica o CSS Global da Carteira
    _apply_wallet_css()

    st.markdown("## 💼 Minha Carteira")

    username = st.session_state.get("username", "")
    df = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))

    # --- TELA DE BOAS VINDAS (SE VAZIO) ---
    if df.empty and not st.session_state.get("wallet_mode", False):
        st.info("Você ainda não tem uma carteira configurada.")
        c1, c2 = st.columns(2)
        with c1:
            st.file_uploader("📂 Importar CSV", key="up_start")
        with c2:
            if st.button("✨ Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                st.rerun()
        return

    st.session_state["carteira_df"] = df

    # --- CÁLCULOS ---
    if df.empty:
        df_calc, kpi = pd.DataFrame(), {}
    else:
        with st.spinner("Atualizando cotações..."):
            df_calc, kpi = atualizar_precos_carteira_memory(df)

    total_brl = float(kpi.get("total_brl", 0.0))
    pnl_brl = float(kpi.get("pnl_brl", 0.0))
    pnl_pct = float(kpi.get("pnl_pct", 0.0))

    # --- KPIs (NOVO DESIGN) ---
    sign_cls = "pos" if pnl_pct >= 0 else "neg"
    sign_icon = "▲" if pnl_pct >= 0 else "▼"

    # HTML puro para os cards superiores
    st.markdown(
        f"""
        <div class="kpi-container">
          <div class="kpi-card">
            <div class="kpi-label">PATRIMÔNIO TOTAL</div>
            <div class="kpi-value">{_compact_brl(total_brl)}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">LUCRO / PREJUÍZO</div>
            <div class="kpi-value">{_compact_brl(pnl_brl)}</div>
            <div class="kpi-sub {sign_cls}">{sign_icon} {pnl_pct:+.2f}%</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">TOTAL DE ATIVOS</div>
            <div class="kpi-value">{len(df_calc)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- MENU DE NAVEGAÇÃO (BOTÕES UNIFORMES) ---
    if "carteira_aba" not in st.session_state:
        st.session_state["carteira_aba"] = "visao_geral"

    # Layout de 3 colunas para os botões do menu
    nav1, nav2, nav3 = st.columns(3, gap="small")

    with nav1:
        if st.button("📍 Dashboard", use_container_width=True, key="nav_dash"):
            st.session_state["carteira_aba"] = "visao_geral"
            st.rerun()

    with nav2:
        if st.button("🎯 Metas e Rebalance", use_container_width=True, key="nav_metas"):
            st.session_state["carteira_aba"] = "alvos"
            st.rerun()

    with nav3:
        if st.button("🧰 Gerenciar Carteira", use_container_width=True, key="nav_edit"):
            st.session_state["carteira_aba"] = "gerenciar"
            st.rerun()

    st.markdown("---")

    # --- CONTEÚDO DAS ABAS ---
    aba = st.session_state["carteira_aba"]

    if aba == "visao_geral":
        # Botão de ação principal
        c_add, _ = st.columns([1, 2])
        with c_add:
            if st.button("➕ Adicionar Novo Ativo", type="secondary", use_container_width=True):
                _dialog_add_asset(username)

        st.markdown("<br>", unsafe_allow_html=True)

        if not df_calc.empty:
            _render_monitor_fixed(df_calc)
            st.markdown("---")
            _render_treemap_and_insights(df_calc)
        else:
            st.info("Sua carteira está vazia. Adicione ativos para começar.")

    elif aba == "alvos":
        if not df_calc.empty:
            _render_targets_and_rebalance(df_calc)
        else:
            st.warning("Adicione ativos antes de definir metas.")

    elif aba == "gerenciar":
        _render_manage(username)