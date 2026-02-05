import streamlit as st
import pandas as pd

from ..safe_imports import px
from ..config import CARTEIRA_COLS
from ..db import save_user_data_db
from ..market_data import smart_load_csv, atualizar_precos_carteira_memory
from ..components import kpi_card
from ..formatters import fmt_money_brl
from ..dialogs import show_asset_details_popup

def render_carteira():
    st.markdown("## 💼 Carteira 2.0 (Multi-User)")
    wallet_active = (not st.session_state["carteira_df"].empty) or st.session_state["wallet_mode"]

    if not wallet_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("Importar CSV", type=["csv"], key="uploader_start")
            if uploaded_file:
                df_loaded = smart_load_csv(uploaded_file)
                if df_loaded is not None:
                    st.session_state["carteira_df"] = df_loaded
                    st.session_state["wallet_mode"] = True
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            st.success("Começar do zero")
            if st.button("Criar Nova Carteira", use_container_width=True):
                st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
                st.session_state["wallet_mode"] = True
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                st.rerun()
        return

    df = st.session_state["carteira_df"]

    if not df.empty:
        with st.spinner("Sincronizando preços..."):
            df_calc, kpi = atualizar_precos_carteira_memory(df)

        total_patrimonio = kpi["total_brl"]
        c_meta, c_set = st.columns([4, 1])
        with c_set:
            nova_meta = st.number_input(
                "Sua Meta (R$)",
                value=st.session_state["patrimonio_meta"],
                step=10000.0,
                label_visibility="collapsed"
            )
            st.session_state["patrimonio_meta"] = nova_meta

        with c_meta:
            progresso = min(total_patrimonio / nova_meta, 1.0) if nova_meta > 0 else 0
            st.progress(progresso)
            st.caption(f"Meta: {fmt_money_brl(nova_meta, 0)} ({(progresso * 100):.1f}%)")

        k1, k2, k3 = st.columns(3)
        with k1:
            kpi_card("TOTAL", fmt_money_brl(kpi["total_brl"], 2), "Patrimônio", compact=True)
        with k2:
            color = "#00C805" if kpi["pnl_brl"] >= 0 else "#FF3B30"
            kpi_card("RESULTADO", fmt_money_brl(kpi["pnl_brl"], 2), f"{kpi['pnl_pct']:+.2f}%", color=color, compact=True)
        with k3:
            kpi_card("ATIVOS", f"{len(df_calc)}", "Diversificação", compact=True)

        if px and not df_calc.empty:
            g1, g2 = st.columns([1, 2])
            with g1:
                fig_tree = px.treemap(
                    df_calc,
                    path=[px.Constant("Carteira"), "Tipo", "Ativo"],
                    values="Total_BRL",
                    color="PnL_Pct",
                    color_continuous_scale=["#FF3B30", "#111111", "#00C805"],
                    color_continuous_midpoint=0
                )
                fig_tree.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_tree, use_container_width=True)

            with g2:
                st.markdown("#### 🔴 Monitor de Rentabilidade")
                st.caption("Clique na linha para abrir o Pop-up com detalhes")

                live_df = df_calc[["Ativo", "Qtd", "Preco_Medio", "Preco_Atual_BRL", "PnL_Pct", "Total_BRL"]].copy()

                selection = st.dataframe(
                    live_df,
                    column_config={
                        "Ativo": "Ativo",
                        "Qtd": st.column_config.NumberColumn("Qtd", format="%.2f"),
                        "Preco_Medio": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
                        "PnL_Pct": st.column_config.NumberColumn("Rentab. %", format="%.2f %%"),
                        "Total_BRL": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=250,
                    on_select="rerun",
                    selection_mode="single-row"
                )

                if selection and selection.selection.rows:
                    idx_sel = selection.selection.rows[0]
                    ativo_selecionado = live_df.iloc[idx_sel]["Ativo"]
                    show_asset_details_popup(ativo_selecionado)

    st.write("---")

    with st.expander("➕ Adicionar Novo Ativo (Formulário Rápido)", expanded=False):
        with st.form("form_add_asset"):
            fc1, fc2, fc3 = st.columns(3)
            f_tipo = fc1.selectbox("Tipo", ["Ação/ETF", "Cripto", "Renda Fixa"])
            f_ativo = fc2.text_input("Ativo (Ticker)", placeholder="Ex: PETR4").upper()
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
                        "Qtd": f_qtd,
                        "Preco_Medio": f_preco,
                        "Moeda": f_moeda,
                        "Obs": ""
                    }
                    st.session_state["carteira_df"] = pd.concat(
                        [st.session_state["carteira_df"], pd.DataFrame([new_asset])],
                        ignore_index=True
                    )
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                    st.success(f"{f_ativo} adicionado com sucesso!")
                    st.rerun()
                else:
                    st.warning("Preencha o Ticker e a Quantidade.")

    with st.expander("📝 Editar Tabela Completa", expanded=False):
        st.caption("Edite os valores na tabela abaixo para atualizar sua carteira.")

        edit_cols = ["Tipo", "Ativo", "Qtd", "Preco_Medio", "Moeda", "Obs"]
        edited_df = st.data_editor(
            df[edit_cols] if not df.empty else pd.DataFrame(columns=edit_cols),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.01, format="%.4f"),
                "Preco_Medio": st.column_config.NumberColumn("Preço Médio", min_value=0.0, step=0.01, format="R$ %.2f"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ação/ETF", "Cripto", "Renda Fixa"]),
                "Moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
            },
            key="editor_carteira"
        )

        if st.button("💾 Salvar Edições (Tabela)", type="primary"):
            st.session_state["carteira_df"] = edited_df
            save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
            st.toast("Carteira salva com sucesso!", icon="✅")
            st.rerun()

    st.write("")
    st.download_button(
        "⬇️ Backup Local (CSV)",
        st.session_state["carteira_df"].to_csv(index=False).encode("utf-8"),
        "minha_carteira.csv",
        "text/csv"
    )
    if st.button("Limpar Carteira"):
        st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)
        st.session_state["wallet_mode"] = False
        save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
        st.rerun()
