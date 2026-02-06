import math
import pandas as pd
import streamlit as st

from bee.config import DB_FILE
from bee.safe_imports import px
from bee.formatters import fmt_money_brl
from bee.db import save_user_data_db, load_targets_db, save_targets_db
from bee.market_data import atualizar_precos_carteira_memory
from bee.dialogs import show_asset_details_popup

CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]


# =========================================================
# Helpers
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
        return f"R$ {v/1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"R$ {v/1_000_000:.2f}M"
    if av >= 1_000:
        return f"R$ {v/1_000:.2f}k"
    return fmt_money_brl(v, 2)


def _apply_wallet_css():
    st.markdown(
        """
        <style>
          .bee-wallet-kpis [data-testid="stMetricValue"]{
            font-size: 26px !important;
            font-weight: 800 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
          }
          .bee-wallet-kpis [data-testid="stMetricLabel"]{
            font-size: 13px !important;
            opacity: .85;
          }

          .bee-section-gap { margin-top: 8px; }

          /* deixa tudo mais “encaixado” */
          .bee-tight h3 { margin-bottom: 6px !important; }
          .bee-tight p { margin-top: 4px !important; margin-bottom: 6px !important; }

          /* melhora scroll horizontal do dataframe */
          div[data-testid="stDataFrame"]{
            width: 100% !important;
          }

          @media (max-width: 768px){
            .bee-wallet-kpis [data-testid="stMetricValue"]{ font-size: 22px !important; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# POPUP - Quick Add Asset
# =========================================================
@st.dialog("➕ Adicionar novo ativo")
def _dialog_add_asset(username: str):
    df = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))

    st.caption("Adicione um ativo rápido.")

    c1, c2, c3 = st.columns([1.1, 1.2, 1])
    f_tipo = c1.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa", "Caixa"], key="dlg_tipo")
    f_ativo = c2.text_input("Ticker", placeholder="Ex: PETR4 / IVVB11 / BTC", key="dlg_ativo").upper().strip()
    f_moeda = c3.selectbox("Moeda", ["BRL", "USD"], key="dlg_moeda")

    c4, c5 = st.columns(2)
    f_qtd = c4.number_input("Quantidade", min_value=0.0, step=1.0, key="dlg_qtd")
    f_preco = c5.number_input("Preço médio", min_value=0.0, step=0.01, format="%.2f", key="dlg_preco")

    c6, c7 = st.columns([1, 1])
    with c6:
        if st.button("Cancelar", use_container_width=True, key="dlg_cancel"):
            st.rerun()
    with c7:
        if st.button("Adicionar", type="primary", use_container_width=True, key="dlg_add"):
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
                st.toast("Ativo adicionado!", icon="✅")
                st.rerun()
            else:
                st.warning("Preencha o ticker e quantidade > 0.")


# =========================================================
# Targets & rebalance
# =========================================================
def _render_targets_and_rebalance(df_calc: pd.DataFrame):
    st.markdown("### 🎯 Alocação alvo + Rebalance (por aporte)")
    username = st.session_state["username"]

    targets = load_targets_db(username, DB_FILE)
    keys = ["Ação/ETF", "Renda Fixa", "Cripto", "Caixa"]

    cols = st.columns(4)
    new_targets = {}
    for i, k in enumerate(keys):
        with cols[i]:
            new_targets[k] = st.number_input(
                f"Alvo {k} (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(targets.get(k, 0.0)),
                step=1.0,
                key=f"target_{k}",
            )

    s = float(sum(new_targets.values()))
    if s > 0 and abs(s - 100) > 0.01:
        st.caption(f"⚠️ Soma em {s:.1f}%. Ideal = 100%.")

    if st.button("Salvar alvos", type="primary", use_container_width=True, key="btn_save_targets"):
        if s <= 0:
            st.error("Defina pelo menos um alvo maior que 0.")
        else:
            final_targets = {k: round(float(v), 2) for k, v in new_targets.items()}
            save_targets_db(username, final_targets, DB_FILE)
            st.toast("Alvos salvos!", icon="✅")
            st.rerun()

    dfb = _classify_tipo_for_targets(df_calc)
    total = float(dfb["Total_BRL"].sum()) if not dfb.empty else 0.0
    if total <= 0:
        st.info("Sem saldo para calcular alocação.")
        return

    cur_val = dfb.groupby("TipoBucket")["Total_BRL"].sum().to_dict()
    cur_pct = {k: (float(cur_val.get(k, 0.0)) / total * 100.0) for k in keys}

    view = pd.DataFrame(
        [{
            "Classe": k,
            "Atual %": round(cur_pct.get(k, 0.0), 2),
            "Alvo %": round(float(new_targets.get(k, 0.0)), 2),
            "Dif (pp)": round(cur_pct.get(k, 0.0) - float(new_targets.get(k, 0.0)), 2),
        } for k in keys]
    )
    st.dataframe(view, use_container_width=True, hide_index=True)

    st.markdown("#### 🤖 Sugestão de aporte por classe")
    aporte = st.number_input(
        "Quanto vai aportar agora? (R$)",
        min_value=0.0,
        step=100.0,
        value=1000.0,
        key="aporte_rebalance",
    )
    if aporte <= 0:
        return

    new_total = total + float(aporte)
    soma_alvos = sum([float(new_targets.get(k, 0)) for k in keys])
    if soma_alvos <= 0:
        st.info("Defina seus alvos acima para ver a sugestão.")
        return

    desired_val = {k: (float(new_targets.get(k, 0.0)) / 100.0) * new_total for k in keys}
    need = {k: desired_val.get(k, 0.0) - float(cur_val.get(k, 0.0)) for k in keys}
    pos = {k: max(0.0, v) for k, v in need.items()}
    sum_pos = float(sum(pos.values()))

    if sum_pos <= 0:
        st.success("Sua carteira já está balanceada ou acima dos alvos. 🙂")
        return

    recs = []
    for k in keys:
        amt = float(aporte) * (pos.get(k, 0.0) / sum_pos) if sum_pos else 0.0
        if amt >= 1:
            recs.append({"Classe": k, "Aportar (R$)": round(amt, 2)})

    if recs:
        st.dataframe(
            pd.DataFrame(recs).sort_values("Aportar (R$)", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# Monitor: TODOS os ativos, tamanho fixo + scroll
# =========================================================
def _render_monitor_fixed(df_calc: pd.DataFrame):
    st.markdown("### 🔴 Monitor de Rentabilidade")
    st.caption("Toque/clique na linha para abrir o pop-up com detalhes do ativo")

    TABLE_HEIGHT = 420  # altura fixa => scroll vertical

    cols = ["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL", "Var_Dia_Pct"]
    live_df = df_calc[cols].copy()

    for col in ["Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL", "Var_Dia_Pct"]:
        live_df[col] = pd.to_numeric(live_df[col], errors="coerce").fillna(0.0)

    # ordena por rentabilidade e NÃO corta linhas
    live_df = live_df.sort_values("PnL_Pct", ascending=False).reset_index(drop=True)

    live_df = live_df.rename(
        columns={
            "Preco_Atual_BRL": "Preco_Atual",
            "PnL_Pct": "Rentab_Pct",
            "Total_BRL": "Total",
            "Var_Dia_Pct": "Dia_Pct",
        }
    )

    selection = st.dataframe(
        live_df[["Ativo", "Qtd", "Preco_Medio", "Preco_Atual", "Dia_Pct", "Rentab_Pct", "Total"]],
        column_config={
            "Qtd": st.column_config.NumberColumn("Qtd", format="%.4f"),
            "Preco_Medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
            "Preco_Atual": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
            "Dia_Pct": st.column_config.NumberColumn("Dia %", format="%.2f %%"),
            "Rentab_Pct": st.column_config.NumberColumn("Rentab. %", format="%.2f %%"),
            "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
        },
        hide_index=True,
        use_container_width=True,
        height=TABLE_HEIGHT,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selection and selection.selection.rows:
        idx_sel = selection.selection.rows[0]
        ativo = str(live_df.iloc[idx_sel]["Ativo"])
        show_asset_details_popup(ativo)


# =========================================================
# Treemap + Insights compactos (mesma altura)
# =========================================================
def _render_treemap_and_insights(df_calc: pd.DataFrame):
    st.markdown('<div class="bee-tight">', unsafe_allow_html=True)
    st.markdown("### 🧭 Mapa da carteira + Insights")
    st.caption("Mapa com cores: verde = subiu hoje, vermelho = caiu hoje. (Renda Fixa não aparece aqui.)")
    st.markdown("</div>", unsafe_allow_html=True)

    if px is None:
        st.info("Plotly não disponível no momento.")
        return

    H_MAP = 340
    H_TABLE = 210

    left, right = st.columns([1.05, 1.0], gap="large")

    # ---------------- LEFT: MAPA ----------------
    with left:
        st.markdown("#### Mapa (peso visual)")
        try:
            df_tree = df_calc.copy()
            df_tree["Tipo"] = df_tree["Tipo"].astype(str).apply(_normalize_tipo)
            df_tree = df_tree[df_tree["Tipo"] != "Renda Fixa"].copy()

            if df_tree.empty:
                st.info("Sem Ação/ETF/Cripto/Caixa para mostrar no mapa.")
            else:
                df_tree["_TreeValue"] = df_tree["Total_BRL"].apply(lambda x: math.sqrt(max(0.0, float(x))))
                if "Var_Dia_Pct" not in df_tree.columns:
                    df_tree["Var_Dia_Pct"] = 0.0
                df_tree["Var_Dia_Pct"] = pd.to_numeric(df_tree["Var_Dia_Pct"], errors="coerce").fillna(0.0)

                fig_tree = px.treemap(
                    df_tree,
                    path=[px.Constant("Carteira"), "Tipo", "Ativo"],
                    values="_TreeValue",
                    color="Var_Dia_Pct",
                    color_continuous_scale=["#ff3b30", "#1f1f1f", "#00c805"],
                    color_continuous_midpoint=0,
                )
                fig_tree.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=H_MAP,
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_tree, use_container_width=True)

        except Exception:
            st.info("Treemap indisponível no momento.")

    # ---------------- RIGHT: INSIGHTS (compacto) ----------------
    with right:
        st.markdown("#### 📌 Insights rápidos")

        df_i = df_calc.copy()
        for col in ["Total_BRL", "Var_Dia_Pct", "PnL_Pct"]:
            if col not in df_i.columns:
                df_i[col] = 0.0
            df_i[col] = pd.to_numeric(df_i[col], errors="coerce").fillna(0.0)

        total = float(df_i["Total_BRL"].sum()) if not df_i.empty else 0.0

        k1, k2 = st.columns(2)
        with k1:
            if not df_i.empty and total > 0:
                top_pos = df_i.sort_values("Total_BRL", ascending=False).iloc[0]
                pct = float(top_pos["Total_BRL"]) / total * 100.0
                k1.metric("Maior posição", str(top_pos.get("Ativo", "")), f"{pct:.1f}%")
            else:
                k1.metric("Maior posição", "—", "—")
        with k2:
            if not df_i.empty and total > 0:
                top3 = df_i.sort_values("Total_BRL", ascending=False).head(3)
                conc = float(top3["Total_BRL"].sum()) / total * 100.0
                k2.metric("Top 3", f"{conc:.1f}%", "concentração")
            else:
                k2.metric("Top 3", "—", "—")

        df_day = df_i[["Ativo", "Var_Dia_Pct"]].copy()
        df_day = df_day.sort_values("Var_Dia_Pct", ascending=False)

        top_up = df_day.head(5).copy()
        top_down = df_day.tail(5).sort_values("Var_Dia_Pct").copy()

        a, b = st.columns(2)
        with a:
            st.markdown("**🟢 Top altas**")
            st.dataframe(
                top_up.rename(columns={"Var_Dia_Pct": "Dia %"}),
                use_container_width=True,
                hide_index=True,
                height=H_TABLE,
                column_config={"Dia %": st.column_config.NumberColumn("Dia %", format="%.2f %%")},
            )
        with b:
            st.markdown("**🔴 Top baixas**")
            st.dataframe(
                top_down.rename(columns={"Var_Dia_Pct": "Dia %"}),
                use_container_width=True,
                hide_index=True,
                height=H_TABLE,
                column_config={"Dia %": st.column_config.NumberColumn("Dia %", format="%.2f %%")},
            )


# =========================================================
# Manage
# =========================================================
def _render_manage(username: str):
    st.markdown("### 🧰 Gerenciar carteira")

    df_edit = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))
    edit_cols = ["Tipo", "Ativo", "Qtd", "Preco_Medio", "Moeda", "Obs"]

    edited_df = st.data_editor(
        df_edit[edit_cols],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação/ETF", "Cripto", "Renda Fixa", "Caixa"]),
            "Moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
            "Qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.01, format="%.4f"),
            "Preco_Medio": st.column_config.NumberColumn("Preço Médio", min_value=0.0, step=0.01, format="R$ %.2f"),
        },
        key="editor_carteira",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Salvar edições", type="primary", use_container_width=True):
            if "Nome" not in edited_df.columns:
                edited_df["Nome"] = edited_df["Ativo"]
            if "Obs" not in edited_df.columns:
                edited_df["Obs"] = ""

            edited_df["Tipo"] = edited_df["Tipo"].astype(str).apply(_normalize_tipo)

            for c in CARTEIRA_COLS:
                if c not in edited_df.columns:
                    edited_df[c] = "" if c not in ["Qtd", "Preco_Medio"] else 0.0
            edited_df = edited_df[CARTEIRA_COLS].copy()

            st.session_state["carteira_df"] = edited_df
            save_user_data_db(
                username,
                st.session_state["carteira_df"],
                st.session_state.get("gastos_df", pd.DataFrame()),
            )
            st.toast("Carteira salva!", icon="✅")
            st.rerun()

    with c2:
        df_export = st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS))
        st.download_button(
            "⬇️ Backup Local (CSV)",
            df_export.to_csv(index=False).encode("utf-8"),
            "minha_carteira.csv",
            "text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("### 🧹 Limpar carteira")
    st.caption("Isso apaga sua carteira (não tem volta).")
    if st.button("Limpar Carteira", use_container_width=True):
        st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
        st.session_state["wallet_mode"] = False
        save_user_data_db(
            username,
            st.session_state["carteira_df"],
            st.session_state.get("gastos_df", pd.DataFrame()),
        )
        st.rerun()


# =========================================================
# Main page
# =========================================================
def render_carteira():
    st.markdown("## 💼 Carteira")
    _apply_wallet_css()

    username = st.session_state.get("username", "")
    df = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))

    wallet_active = (not df.empty) or bool(st.session_state.get("wallet_mode", False))

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("Importar CSV", type=["csv"], key="uploader_start_wallet")
            if uploaded_file:
                uploaded_file.seek(0)
                try:
                    df_loaded = pd.read_csv(uploaded_file)
                except Exception:
                    uploaded_file.seek(0)
                    df_loaded = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

                if df_loaded is not None and not df_loaded.empty:
                    for col in CARTEIRA_COLS:
                        if col not in df_loaded.columns:
                            df_loaded[col] = 0.0 if col in ["Qtd", "Preco_Medio"] else ""
                    df_loaded = df_loaded[CARTEIRA_COLS].copy()
                    df_loaded["Tipo"] = df_loaded["Tipo"].astype(str).apply(_normalize_tipo)

                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    save_user_data_db(
                        username,
                        st.session_state["carteira_df"],
                        st.session_state.get("gastos_df", pd.DataFrame()),
                    )
                    st.rerun()
                else:
                    st.error("Arquivo inválido ou vazio.")

        with c2:
            st.success("Começar do zero")
            if st.button("Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                save_user_data_db(
                    username,
                    st.session_state["carteira_df"],
                    st.session_state.get("gastos_df", pd.DataFrame()),
                )
                st.rerun()
        return

    st.session_state["carteira_df"] = df

    if df.empty:
        df_calc = pd.DataFrame()
        kpi = {"total_brl": 0.0, "pnl_brl": 0.0, "pnl_pct": 0.0}
    else:
        with st.spinner("Sincronizando preços..."):
            df_calc, kpi = atualizar_precos_carteira_memory(df)

    st.markdown('<div class="bee-wallet-kpis">', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("TOTAL (R$)", _compact_brl(float(kpi.get("total_brl", 0.0))))
    with k2:
        pnl_brl = float(kpi.get("pnl_brl", 0.0))
        st.metric("RESULTADO (R$)", _compact_brl(pnl_brl), f"{float(kpi.get('pnl_pct', 0.0)):+.2f}%")
    with k3:
        st.metric("ATIVOS", f"{len(df_calc) if isinstance(df_calc, pd.DataFrame) else 0}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    tab_overview, tab_targets, tab_manage = st.tabs(["📍 Visão geral", "🎯 Alvos & Rebalance", "🧰 Gerenciar"])

    with tab_overview:
        cA, cB = st.columns([1, 1])
        with cA:
            if st.button("➕ Novo ativo", type="primary", use_container_width=True, key="btn_open_add_asset"):
                _dialog_add_asset(username)
        with cB:
            st.caption("Monitor com TODOS os ativos (scroll), ordenado por Rentab. %")

        if df_calc is None or df_calc.empty:
            st.info("Adicione ativos para ver o monitor e o mapa.")
        else:
            _render_monitor_fixed(df_calc)

            st.markdown("<div class='bee-section-gap'></div>", unsafe_allow_html=True)
            st.markdown("---")

            _render_treemap_and_insights(df_calc)

    with tab_targets:
        if df_calc is None or df_calc.empty:
            st.info("Adicione ativos para usar Alvos & Rebalance.")
        else:
            _render_targets_and_rebalance(df_calc)

    with tab_manage:
        _render_manage(username)
