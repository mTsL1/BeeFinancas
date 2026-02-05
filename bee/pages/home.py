import streamlit as st

from ..safe_imports import yf, px
from ..components import kpi_card
from ..formatters import fmt_ptbr_number, fmt_money_brl, fmt_money_usd, human_time_ago
from ..market_data import (
    normalize_ticker,
    yf_last_and_prev_close,
    get_google_news_items,
    atualizar_precos_carteira_memory,
    investidor10_link,
)

def render_home():
    st.markdown(f"## 📌 Visão do Mercado (Olá, {st.session_state['user_name_display']})")

    ibov_val = ibov_pct = None
    usd_val = usd_pct = None
    btc_usd_val = btc_usd_pct = None
    btc_brl_val = btc_brl_pct = None

    if yf is not None:
        tickers_home = ["^BVSP", "BRL=X", "BTC-USD", "BTC-BRL"]
        snap = yf_last_and_prev_close(tickers_home)

        if not snap.empty:
            ib = snap[snap["ticker"] == "^BVSP"]
            fx = snap[snap["ticker"] == "BRL=X"]
            btcu = snap[snap["ticker"] == "BTC-USD"]
            btcb = snap[snap["ticker"] == "BTC-BRL"]

            if not ib.empty:
                ibov_val = float(ib.iloc[0]["last"])
                ibov_pct = float(ib.iloc[0]["var_pct"])
            if not fx.empty:
                usd_val = float(fx.iloc[0]["last"])
                usd_pct = float(fx.iloc[0]["var_pct"])
            if not btcu.empty:
                btc_usd_val = float(btcu.iloc[0]["last"])
                btc_usd_pct = float(btcu.iloc[0]["var_pct"])
            if not btcb.empty:
                btc_brl_val = float(btcb.iloc[0]["last"])
                btc_brl_pct = float(btcb.iloc[0]["var_pct"])

            if (btc_brl_val is None or btc_brl_val == 0) and (btc_usd_val is not None and usd_val is not None):
                btc_brl_val = btc_usd_val * usd_val
                btc_brl_pct = btc_usd_pct

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        val = fmt_ptbr_number(ibov_val, 0) if ibov_val is not None else "—"
        sub = f"{ibov_pct:+.2f}% (dia)" if ibov_pct is not None else ""
        kpi_card("IBOV", val, sub, color="#FFD700", compact=True)
    with c2:
        val = fmt_money_brl(usd_val, 2) if usd_val is not None else "—"
        sub = f"{usd_pct:+.2f}% (dia)" if usd_pct is not None else ""
        kpi_card("USD/BRL", val, sub, color="#FFD700", compact=True)
    with c3:
        val = fmt_money_usd(btc_usd_val, 0) if btc_usd_val is not None else "—"
        sub = f"{btc_usd_pct:+.2f}% (24h)" if btc_usd_pct is not None else ""
        kpi_card("BTC (US$)", val, sub, color="#FFD700", compact=True)
    with c4:
        val = f"R$ {fmt_ptbr_number(btc_brl_val, 0)}" if btc_brl_val is not None else "—"
        sub = f"{btc_brl_pct:+.2f}% (24h)" if btc_brl_pct is not None else ""
        kpi_card("BTC (R$)", val, sub, color="#FFD700", small=True)

    st.write("")

    st.markdown("### 🏆 Destaques da Carteira (24h)")

    df_cart = st.session_state["carteira_df"]
    if not df_cart.empty:
        df_calc, _ = atualizar_precos_carteira_memory(df_cart)
        df_stocks = df_calc[~df_calc["Tipo"].astype(str).str.contains("Renda Fixa|RF", case=False, na=False)].copy()

        if not df_stocks.empty:
            df_stocks = df_stocks.sort_values(by="Var_Dia_Pct", ascending=False)
            my_gain = df_stocks.head(5)
            my_loss = df_stocks.tail(5).sort_values(by="Var_Dia_Pct", ascending=True)

            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("##### 🚀 Maiores Altas Hoje")
                st.dataframe(
                    my_gain[["Ativo", "Var_Dia_Pct", "Preco_Atual_BRL"]],
                    hide_index=True,
                    column_config={
                        "Ativo": "Ativo",
                        "Var_Dia_Pct": st.column_config.NumberColumn("Var Dia %", format="%.2f %%"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f")
                    },
                    use_container_width=True
                )
            with mc2:
                st.markdown("##### 🔻 Maiores Baixas Hoje")
                st.dataframe(
                    my_loss[["Ativo", "Var_Dia_Pct", "Preco_Atual_BRL"]],
                    hide_index=True,
                    column_config={
                        "Ativo": "Ativo",
                        "Var_Dia_Pct": st.column_config.NumberColumn("Var Dia %", format="%.2f %%"),
                        "Preco_Atual_BRL": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f")
                    },
                    use_container_width=True
                )
        else:
            st.info("Você só tem Renda Fixa ou a carteira está vazia.")
    else:
        st.warning("Adicione ativos na aba Carteira para ver seu ranking.")

    st.write("")
    st.markdown("### ⚡ Acesso Rápido")

    quick_ticker = st.text_input(
        "Ticker",
        placeholder="Ex: PETR4, VALE3, IVVB11...",
        label_visibility="collapsed",
    ).upper().strip()

    if quick_ticker:
        tk_norm = normalize_ticker(quick_ticker, "Ação", "BRL")
        c_info, c_btn = st.columns([3, 1])
        with c_info:
            if yf is not None:
                hist = yf_last_and_prev_close([tk_norm])
                if not hist.empty:
                    last = float(hist.iloc[0]["last"])
                    var = float(hist.iloc[0]["var_pct"])
                    cor_txt = "#00C805" if var >= 0 else "#FF3B30"
                    st.markdown(
                        f"""
<div style="margin-top:6px; margin-bottom:6px;">
  <span style="font-size:26px; font-weight:900; color:#fff;">{tk_norm.replace('.SA', '')}</span>
  <span style="font-size:22px; font-weight:900; color:{cor_txt}; margin-left:10px;">{fmt_ptbr_number(last, 2)} ({var:+.2f}%)</span>
</div>
""",
                        unsafe_allow_html=True,
                    )
        with c_btn:
            link = investidor10_link(quick_ticker)
            st.link_button("Abrir no Investidor10", link, use_container_width=True)

        if px is not None and yf is not None:
            try:
                chart_data = yf.Ticker(tk_norm).history(period="1mo", auto_adjust=False)
                if not chart_data.empty:
                    fig_mini = px.line(chart_data, y="Close")
                    fig_mini.update_layout(
                        xaxis_visible=False,
                        yaxis_visible=False,
                        margin=dict(l=0, r=0, t=5, b=5),
                        height=70,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_mini, use_container_width=True, config={"displayModeBar": False})
            except Exception:
                pass

    st.write("")
    st.markdown("### 📰 Notícias")
    news = get_google_news_items("investimentos brasil", limit=6)
    if news:
        for n in news:
            ago = human_time_ago(n["published_dt"])
            st.markdown(
                f"""
<a href="{n['link']}" target="_blank" class="news-card-link">
  <div class="news-card-box">
    <div class="nc-title">{n['title']}</div>
    <div class="nc-meta">
      <span class="nc-badge">{n['source']}</span>
      <span>• {ago}</span>
    </div>
  </div>
</a>
""",
                unsafe_allow_html=True,
            )
    else:
        st.info("Sem notícias agora.")
