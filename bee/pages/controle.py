import streamlit as st
import pandas as pd
from datetime import datetime

from ..safe_imports import px
from ..config import GASTOS_COLS
from ..db import save_user_data_db
from ..market_data import smart_load_csv
from ..formatters import fmt_money_brl

def render_controle():
    st.markdown("## 💸 Controle de Gastos 2.0")
    gastos_active = (not st.session_state["gastos_df"].empty) or st.session_state["gastos_mode"]

    if not gastos_active:
        c1, c2 = st.columns(2)
        with c1:
            uploaded_gastos = st.file_uploader("Importar CSV", type=["csv"], key="uploader_gastos")
            if uploaded_gastos:
                df_g = smart_load_csv(uploaded_gastos)
                if df_g is not None:
                    st.session_state["gastos_df"] = df_g
                    st.session_state["gastos_mode"] = True
                    save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                    st.rerun()
                else:
                    st.error("Arquivo inválido.")
        with c2:
            if st.button("Criar Planilha de Gastos", use_container_width=True):
                st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
                st.session_state["gastos_mode"] = True
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                st.rerun()
        return

    df_g = st.session_state["gastos_df"].copy()
    df_g["Data"] = pd.to_datetime(df_g["Data"], errors="coerce")
    df_g.dropna(subset=["Data"], inplace=True)

    today = datetime.now()
    meses_disp = sorted(list(set(df_g["Data"].dt.strftime("%Y-%m"))))
    if not meses_disp:
        meses_disp = [today.strftime("%Y-%m")]

    mes_atual_str = today.strftime("%Y-%m")
    idx_mes = meses_disp.index(mes_atual_str) if mes_atual_str in meses_disp else (len(meses_disp) - 1)

    col_sel, col_meta = st.columns([2, 2])
    with col_sel:
        mes_selecionado = st.selectbox("📅 Mês", meses_disp, index=idx_mes)
    with col_meta:
        nova_meta_gasto = st.number_input("💰 Orçamento Mensal (R$)", value=st.session_state["gasto_meta"], step=100.0)
        st.session_state["gasto_meta"] = nova_meta_gasto

    mask_mes = df_g["Data"].dt.strftime("%Y-%m") == mes_selecionado
    df_filtered = df_g[mask_mes]

    total_ent = float(df_filtered[df_filtered["Tipo"] == "Entrada"]["Valor"].sum())
    total_sai = float(df_filtered[df_filtered["Tipo"] == "Saída"]["Valor"].sum())
    saldo = total_ent - total_sai

    percent_gasto = min(total_sai / nova_meta_gasto, 1.0) if nova_meta_gasto > 0 else 0

    st.markdown(f"**Orçamento usado:** {percent_gasto * 100:.1f}% de {fmt_money_brl(nova_meta_gasto, 0)}")
    st.progress(percent_gasto)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Receitas", fmt_money_brl(total_ent, 2))
    with k2:
        st.metric("Despesas", fmt_money_brl(total_sai, 2))
    with k3:
        st.metric("Saldo", fmt_money_brl(saldo, 2))

    st.markdown("### 📊 Análise Visual")
    if px is not None and not df_filtered.empty and total_sai > 0:
        tab_g1, tab_g2 = st.tabs(["Por Categoria", "Evolução Diária"])

        with tab_g1:
            df_pie = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
            fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.5,
                         color_discrete_sequence=px.colors.sequential.Magma)
            fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with tab_g2:
            df_daily = df_filtered[df_filtered["Tipo"] == "Saída"].groupby("Data")["Valor"].sum().reset_index()
            fig_bar = px.bar(df_daily, x="Data", y="Valor", color="Valor", color_continuous_scale="Reds")
            fig_bar.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
    elif df_filtered.empty:
        st.info("Nenhum lançamento neste mês.")

    st.write("---")

    with st.expander("➕ Nova Transação", expanded=False):
        with st.form("form_gastos", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d_data = c1.date_input("Data", value=today)
            default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Outros"]
            existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
            all_cats = sorted(list(set(default_cats + existing_cats)))
            all_cats.append("➕ Nova (Digitar abaixo)")

            d_cat_select = c2.selectbox("Categoria", all_cats)
            d_cat_input = c2.text_input("Nova Categoria", placeholder="Ex: Pet")
            d_desc = c3.text_input("Descrição", placeholder="Ex: Supermercado")
            d_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"])

            c5, c6 = st.columns(2)
            d_val = c5.number_input("Valor (R$)", min_value=0.0, step=10.0)
            d_pag = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])

            if st.form_submit_button("Salvar"):
                final_cat = d_cat_input if (d_cat_select == "➕ Nova (Digitar abaixo)" and d_cat_input) else d_cat_select
                if final_cat == "➕ Nova (Digitar abaixo)":
                    final_cat = "Outros"

                new_row = {
                    "Data": d_data,
                    "Categoria": final_cat,
                    "Descricao": d_desc,
                    "Tipo": d_tipo,
                    "Valor": d_val,
                    "Pagamento": d_pag,
                }
                df_g = pd.concat([df_g, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state["gastos_df"] = df_g
                save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
                st.toast("Transação salva!", icon="💸")
                st.rerun()

    st.markdown("##### Extrato Detalhado")
    df_g_edited = st.data_editor(
        df_g,
        num_rows="dynamic",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
        },
        use_container_width=True,
        height=340,
        key="editor_gastos"
    )
    if st.button("💾 Salvar na Nuvem (DB)", key="save_gastos"):
        st.session_state["gastos_df"] = df_g_edited
        save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
        st.toast("Extrato atualizado!", icon="✅")
        st.rerun()

    st.write("---")

    st.download_button(
        "⬇️ Backup Local (CSV)",
        df_g.to_csv(index=False).encode("utf-8"),
        "meus_gastos.csv",
        "text/csv"
    )

    if st.button("Limpar Gastos"):
        st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
        st.session_state["gastos_mode"] = False
        save_user_data_db(st.session_state["username"], st.session_state["carteira_df"], st.session_state["gastos_df"])
        st.rerun()
