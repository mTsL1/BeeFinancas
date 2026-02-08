import streamlit as st
import pandas as pd

# Imports relativos
from ..safe_imports import yf
from ..formatters import fmt_ptbr_number, fmt_money_brl, fmt_money_usd
from ..market_data import (
    yf_last_and_prev_close,
    atualizar_precos_carteira_memory
)


def render_home():
    # --- CABEÇALHO ---
    # Blindagem do nome do usuário
    raw_name = st.session_state.get('user_name_display', 'Investidor')
    user_name = str(raw_name).split()[0] if raw_name else "Investidor"

    st.title(f"👋 Olá, {user_name}!")
    st.caption("Resumo do mercado e da sua carteira.")
    st.divider()

    # --- 1. MERCADO AGORA (NATIVO ST.METRIC) ---
    st.subheader("🌎 Mercado Agora")

    # Valores padrão
    ibov_val, ibov_pct = 0.0, 0.0
    usd_val, usd_pct = 0.0, 0.0
    btcu_val, btcu_pct = 0.0, 0.0

    if yf:
        tickers = ["^BVSP", "BRL=X", "BTC-USD"]
        snap = yf_last_and_prev_close(tickers)
        if not snap.empty:
            # IBOV
            row_ib = snap[snap["ticker"] == "^BVSP"]
            if not row_ib.empty:
                ibov_val = float(row_ib.iloc[0]["last"])
                ibov_pct = float(row_ib.iloc[0]["var_pct"])

            # USD
            row_us = snap[snap["ticker"] == "BRL=X"]
            if not row_us.empty:
                usd_val = float(row_us.iloc[0]["last"])
                usd_pct = float(row_us.iloc[0]["var_pct"])

            # BTC
            row_btc = snap[snap["ticker"] == "BTC-USD"]
            if not row_btc.empty:
                btcu_val = float(row_btc.iloc[0]["last"])
                btcu_pct = float(row_btc.iloc[0]["var_pct"])

    # Exibição com st.metric (Nativo e seguro)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("IBOVESPA", fmt_ptbr_number(ibov_val, 0), f"{ibov_pct:+.2f}%")
    with col2:
        st.metric("DÓLAR", fmt_money_brl(usd_val, 2), f"{usd_pct:+.2f}%")
    with col3:
        st.metric("BITCOIN (USD)", fmt_money_usd(btcu_val, 0), f"{btcu_pct:+.2f}%")

    st.markdown("---")

    # --- 2. DESTAQUES DA CARTEIRA ---
    st.subheader("🚀 Destaques da Carteira (24h)")

    df_cart = st.session_state.get("carteira_df", pd.DataFrame())

    if df_cart.empty:
        st.info("Sua carteira está vazia. Adicione ativos na aba 'Carteira' para ver os destaques.")
    else:
        # Processa dados
        df_calc, _ = atualizar_precos_carteira_memory(df_cart)
        # Filtra só Ações/Cripto/FIIs (remove Renda Fixa)
        df_stocks = df_calc[~df_calc["Tipo"].astype(str).str.contains("Renda Fixa|RF", case=False, na=False)].copy()

        if df_stocks.empty:
            st.info("Você possui apenas Renda Fixa. Adicione Renda Variável para ver oscilações diárias.")
        else:
            df_stocks = df_stocks.sort_values(by="Var_Dia_Pct", ascending=False)

            c_high, c_low = st.columns(2)

            with c_high:
                st.markdown("**🔥 Maiores Altas**")
                top_high = df_stocks.head(3)[["Ativo", "Var_Dia_Pct", "Preco_Atual_BRL"]]
                st.dataframe(
                    top_high,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Ativo": "Ativo",
                        "Var_Dia_Pct": st.column_config.NumberColumn("Var %", format="%.2f %%"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço", format="R$ %.2f")
                    }
                )

            with c_low:
                st.markdown("**❄️ Maiores Baixas**")
                top_low = df_stocks.tail(3).sort_values(by="Var_Dia_Pct", ascending=True)[
                    ["Ativo", "Var_Dia_Pct", "Preco_Atual_BRL"]]
                st.dataframe(
                    top_low,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Ativo": "Ativo",
                        "Var_Dia_Pct": st.column_config.NumberColumn("Var %", format="%.2f %%"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço", format="R$ %.2f")
                    }
                )