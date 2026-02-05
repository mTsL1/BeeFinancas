import streamlit as st
from ..market_data import normalize_ticker, yf_info_extended, get_stock_history_plot, format_market_cap
from ..formatters import fmt_money_brl

def render_analisar():
    st.markdown("## 🔍 Analisar Pro")
    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input("Ativo", placeholder="WEGE3 / PETR4 / IVVB11 / AAPL",
                               label_visibility="collapsed").upper().strip()
    with c_p:
        periodo = st.selectbox("Zoom", ["1mo", "6mo", "1y", "5y", "max"], index=2)

    if ticker:
        tk_real = normalize_ticker(ticker, "Ação", "BRL")
        info = yf_info_extended(tk_real)
        if info:
            st.markdown(f"### {info.get('longName', ticker)}")

            m1, m2, m3, m4 = st.columns(4)
            cur_price = info.get("currentPrice", 0.0)

            with m1:
                st.metric("Preço", fmt_money_brl(cur_price, 2) if cur_price else "—")

            val_dy = info.get("dividendYield")
            with m2:
                if val_dy and val_dy < 2:
                    st.metric("DY", f"{val_dy * 100:.2f}%")
                elif val_dy:
                    st.metric("DY", f"{val_dy:.2f}%")
                else:
                    st.metric("DY", "—")

            val_pe = info.get("trailingPE")
            with m3:
                st.metric("P/L", f"{val_pe:.2f}" if val_pe else "—")

            with m4:
                st.metric("Market Cap", format_market_cap(info.get("marketCap")))

            st.markdown("---")
            f1, f2, f3 = st.columns(3)
            with f1:
                roe_val = info.get("roe")
                st.metric("ROE (Rentab.)", f"{roe_val * 100:.2f}%" if roe_val else "—")
            with f2:
                mg_val = info.get("margins")
                st.metric("Margem Líq.", f"{mg_val * 100:.2f}%" if mg_val else "—")
            with f3:
                beta_val = info.get("beta")
                st.metric("Beta (Volat.)", f"{beta_val:.2f}" if beta_val else "—")

            st.markdown("---")
            fig, rsi = get_stock_history_plot(tk_real, period=periodo)

            if rsi:
                rsi_text = f"{rsi:.1f}"
                if rsi > 70:
                    rsi_status = "⚠️ Sobrecomprado (Cara?)"
                    rsi_color_code = "#FF3B30"
                elif rsi < 30:
                    rsi_status = "💎 Sobrevendido (Barata?)"
                    rsi_color_code = "#00C805"
                else:
                    rsi_status = "Neutro"
                    rsi_color_code = "#FFD700"

                st.markdown(
                    f"**RSI (IFR 14):** <span style='color:{rsi_color_code}; font-weight:bold; font-size:18px'>{rsi_text}</span> — {rsi_status}",
                    unsafe_allow_html=True
                )
                st.caption("RSI acima de 70 indica alta forte (risco correção). Abaixo de 30 indica baixa forte (oportunidade?).")

            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Sem gráfico disponível. O Yahoo Finance pode estar instável para este ativo.")

            with st.expander("Resumo da Empresa"):
                st.write(info.get("summary", "—"))
        else:
            st.error("Ativo não encontrado ou Yahoo Finance inacessível.")
