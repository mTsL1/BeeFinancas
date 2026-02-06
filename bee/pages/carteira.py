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


def _ensure_wallet_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=CARTEIRA_COLS)
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
    # fallback: se já veio certinho
    if t in ["Ação/ETF", "Cripto", "Renda Fixa", "Caixa"]:
        return t
    return "Ação/ETF"


def _classify_tipo_for_targets(df_calc: pd.DataFrame) -> pd.DataFrame:
    # garante que "Tipo" caia nos buckets: Ação/ETF, Cripto, Renda Fixa, Caixa
    df = df_calc.copy()
    df["TipoBucket"] = df["Tipo"].astype(str).apply(_normalize_tipo)
    return df


def _render_targets_and_rebalance(df_calc: pd.DataFrame):
    st.markdown("### 🎯 Alocação alvo + Rebalance (por aporte)")
    username = st.session_state["username"]

    # === CORREÇÃO: Ordem dos argumentos (username, db_file) ===
    targets = load_targets_db(username, DB_FILE)

    # UI: editar metas
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
            )

    s = float(sum(new_targets.values()))

    # Aviso visual se a soma não for 100% (mas não bloqueia, só avisa)
    if s > 0 and abs(s - 100) > 0.01:
        st.caption(f"⚠️ A soma está em {s:.1f}%. O ideal é fechar em 100%.")

    if st.button("Salvar alvos", type="primary", use_container_width=True):
        if s <= 0:
            st.error("Defina pelo menos um alvo maior que 0.")
        else:
            # Normaliza para 100% se passar ou faltar um pouco, para evitar matemática quebrada
            final_targets = {k: round(float(v), 2) for k, v in new_targets.items()}

            # === CORREÇÃO: Ordem dos argumentos (username, targets, db_file) ===
            save_targets_db(username, final_targets, DB_FILE)
            st.toast("Alvos salvos com sucesso!", icon="✅")
            st.rerun()

    # calcula atual vs alvo
    dfb = _classify_tipo_for_targets(df_calc)
    total = float(dfb["Total_BRL"].sum()) if not dfb.empty else 0.0
    if total <= 0:
        # Se não tem saldo, não mostra rebalanceamento
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

    # rebalance por aporte
    st.markdown("#### 🤖 Sugestão de aporte por classe")
    aporte = st.number_input("Quanto vai aportar agora? (R$)", min_value=0.0, step=100.0, value=1000.0)
    if aporte <= 0:
        return

    new_total = total + float(aporte)

    # Se os alvos forem todos zero, não sugere nada
    soma_alvos = sum([float(new_targets.get(k, 0)) for k in keys])
    if soma_alvos <= 0:
        st.info("Defina seus alvos acima para ver a sugestão.")
        return

    # Calcula quanto deveria ter em cada classe
    desired_val = {k: (float(new_targets.get(k, 0.0)) / 100.0) * new_total for k in keys}

    # Calcula a diferença (o que falta)
    need = {k: desired_val.get(k, 0.0) - float(cur_val.get(k, 0.0)) for k in keys}

    # Pega apenas quem precisa receber dinheiro (need > 0)
    pos = {k: max(0.0, v) for k, v in need.items()}
    sum_pos = float(sum(pos.values()))

    if sum_pos <= 0:
        st.info("Sua carteira já está balanceada ou acima dos alvos. Pode aportar onde preferir! 🙂")
        return

    recs = []
    for k in keys:
        # Distribui o aporte proporcionalmente à "fome" de cada classe
        amt = float(aporte) * (pos.get(k, 0.0) / sum_pos) if sum_pos else 0.0
        if amt >= 1:
            recs.append({"Classe": k, "Aportar (R$)": round(amt, 2)})

    if recs:
        st.dataframe(pd.DataFrame(recs).sort_values("Aportar (R$)", ascending=False),
                     use_container_width=True, hide_index=True)


def render_carteira():
    st.markdown("## 💼 Carteira")

    username = st.session_state["username"]
    df = _ensure_wallet_columns(st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)))

    wallet_active = (not df.empty) or bool(st.session_state.get("wallet_mode", False))

    # START: carteira vazia
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
                    # tenta padronizar colunas
                    for col in CARTEIRA_COLS:
                        if col not in df_loaded.columns:
                            if col in ["Qtd", "Preco_Medio"]:
                                df_loaded[col] = 0.0
                            else:
                                df_loaded[col] = ""
                    df_loaded = df_loaded[CARTEIRA_COLS].copy()
                    df_loaded["Tipo"] = df_loaded["Tipo"].astype(str).apply(_normalize_tipo)

                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    save_user_data_db(username, st.session_state["carteira_df"],
                                      st.session_state.get("gastos_df", pd.DataFrame()))
                    st.rerun()
                else:
                    st.error("Arquivo inválido ou vazio.")

        with c2:
            st.success("Começar do zero")
            if st.button("Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                save_user_data_db(username, st.session_state["carteira_df"],
                                  st.session_state.get("gastos_df", pd.DataFrame()))
                st.rerun()

        return

    # carteira ativa
    st.session_state["carteira_df"] = df

    if df.empty:
        st.info("Sua carteira está vazia. Use o formulário rápido abaixo para adicionar ativos.")
    else:
        with st.spinner("Sincronizando preços..."):
            df_calc, kpi = atualizar_precos_carteira_memory(df)

        # KPIs
        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric("TOTAL (R$)", fmt_money_brl(kpi.get("total_brl", 0.0), 2))
        with k2:
            pnl_brl = float(kpi.get("pnl_brl", 0.0))
            st.metric("RESULTADO (R$)", fmt_money_brl(pnl_brl, 2), f"{float(kpi.get('pnl_pct', 0.0)):+.2f}%")
        with k3:
            st.metric("ATIVOS", f"{len(df_calc)}")

        # Alocação alvo + rebalance
        st.markdown("---")
        _render_targets_and_rebalance(df_calc)

        st.markdown("---")

        # Treemap + tabela com seleção
        if px is not None and not df_calc.empty:
            g1, g2 = st.columns([1, 2])

            with g1:
                st.markdown("#### 🧭 Mapa da carteira")
                try:
                    fig_tree = px.treemap(
                        df_calc,
                        path=[px.Constant("Carteira"), "Tipo", "Ativo"],
                        values="Total_BRL",
                        color="PnL_Pct",
                        color_continuous_scale=["#FF3B30", "#111111", "#00C805"],
                        color_continuous_midpoint=0,
                    )
                    fig_tree.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=280, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_tree, use_container_width=True)
                except Exception:
                    st.info("Treemap indisponível no momento.")

            with g2:
                st.markdown("#### 🔴 Monitor de Rentabilidade")
                st.caption("Clique na linha para abrir o pop-up com detalhes do ativo")

                live_df = df_calc[["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL"]].copy()

                selection = st.dataframe(
                    live_df,
                    column_config={
                        "Qtd": st.column_config.NumberColumn("Qtd", format="%.4f"),
                        "Preco_Medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
                        "PnL_Pct": st.column_config.NumberColumn("Rentab. %", format="%.2f %%"),
                        "Total_BRL": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=280,
                    on_select="rerun",
                    selection_mode="single-row",
                )

                if selection and selection.selection.rows:
                    idx_sel = selection.selection.rows[0]
                    ativo = str(live_df.iloc[idx_sel]["Ativo"])
                    show_asset_details_popup(ativo)

    # QUICK ADD
    st.markdown("---")
    with st.expander("➕ Adicionar Novo Ativo (Formulário Rápido)", expanded=False):
        with st.form("form_add_asset"):
            fc1, fc2, fc3 = st.columns(3)
            f_tipo = fc1.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa"])
            f_ativo = fc2.text_input("Ativo (Ticker)", placeholder="Ex: PETR4").upper().strip()
            f_moeda = fc3.selectbox("Moeda", ["BRL", "USD"])

            fc4, fc5 = st.columns(2)
            f_qtd = fc4.number_input("Quantidade", min_value=0.0, step=1.0)
            f_preco = fc5.number_input("Preço Médio", min_value=0.0, step=0.01, format="%.2f")

            if st.form_submit_button("Adicionar à Carteira"):
                if f_ativo and f_qtd > 0:
                    new_asset = {
                        "Tipo": f_tipo,
                        "Ativo": f_ativo,
                        "Nome": f_ativo,
                        "Qtd": float(f_qtd),
                        "Preco_Medio": float(f_preco),
                        "Moeda": f_moeda,
                        "Obs": "",
                    }
                    df_new = pd.concat([df, pd.DataFrame([new_asset])], ignore_index=True)
                    st.session_state["carteira_df"] = df_new
                    st.session_state["wallet_mode"] = True
                    save_user_data_db(username, st.session_state["carteira_df"],
                                      st.session_state.get("gastos_df", pd.DataFrame()))
                    st.toast("Ativo adicionado!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Preencha o ticker e quantidade > 0.")

    # EDITOR
    with st.expander("📝 Editar Tabela Completa", expanded=False):
        df_edit = st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS)).copy()
        if df_edit.empty:
            df_edit = pd.DataFrame(columns=CARTEIRA_COLS)

        edit_cols = ["Tipo", "Ativo", "Qtd", "Preco_Medio", "Moeda", "Obs"]
        edited_df = st.data_editor(
            df_edit[edit_cols],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação/ETF", "Cripto", "Renda Fixa"]),
                "Moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.01, format="%.4f"),
                "Preco_Medio": st.column_config.NumberColumn("Preço Médio", min_value=0.0, step=0.01, format="R$ %.2f"),
            },
            key="editor_carteira",
        )

        if st.button("💾 Salvar Edições (Tabela)", type="primary", use_container_width=True):
            # reintroduz Nome (se não existir)
            if "Nome" not in edited_df.columns:
                edited_df["Nome"] = edited_df["Ativo"]
            if "Obs" not in edited_df.columns:
                edited_df["Obs"] = ""
            edited_df["Tipo"] = edited_df["Tipo"].astype(str).apply(_normalize_tipo)

            # reordena
            for c in CARTEIRA_COLS:
                if c not in edited_df.columns:
                    edited_df[c] = "" if c not in ["Qtd", "Preco_Medio"] else 0.0
            edited_df = edited_df[CARTEIRA_COLS].copy()

            st.session_state["carteira_df"] = edited_df
            save_user_data_db(username, st.session_state["carteira_df"],
                              st.session_state.get("gastos_df", pd.DataFrame()))
            st.toast("Carteira salva!", icon="✅")
            st.rerun()

    st.write("")
    df_export = st.session_state.get("carteira_df", pd.DataFrame(columns=CARTEIRA_COLS))
    st.download_button(
        "⬇️ Backup Local (CSV)",
        df_export.to_csv(index=False).encode("utf-8"),
        "minha_carteira.csv",
        "text/csv",
        use_container_width=True,
    )

    if st.button("🧹 Limpar Carteira", use_container_width=True):
        st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
        st.session_state["wallet_mode"] = False
        save_user_data_db(username, st.session_state["carteira_df"], st.session_state.get("gastos_df", pd.DataFrame()))
        st.rerun()