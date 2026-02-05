import streamlit as st

from .market_data import normalize_ticker, yf_info_extended, get_stock_history_plot
from .formatters import fmt_money_brl, fmt_ptbr_number

@st.dialog("🔍 Raio-X do Ativo")
def show_asset_details_popup(ativo_selecionado):
    tk_real = normalize_ticker(ativo_selecionado, "Ação", "BRL")

    with st.spinner(f"Carregando dados de {tk_real}..."):
        info = yf_info_extended(tk_real)
        fig, rsi = get_stock_history_plot(tk_real, period="6mo")

    if info and info.get("currentPrice", 0) > 0:
        st.markdown(f"### {info.get('longName', ativo_selecionado)}")

        def mini_metric(label, value):
            return f"""
            <div style="text-align:center; background:rgba(255,255,255,0.03); border-radius:8px; padding:8px;">
                <div style="font-size:11px; color:#888; text-transform:uppercase; margin-bottom:4px;">{label}</div>
                <div style="font-size:20px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{value}</div>
            </div>
            """

        m1, m2, m3 = st.columns(3)
        with m1:
            val_fmt = fmt_money_brl(info.get("currentPrice"), 2)
            st.markdown(mini_metric("Preço", val_fmt), unsafe_allow_html=True)
        with m2:
            dy_val = info.get("dividendYield", 0) or 0
            fmt_dy = f"{dy_val * 100:.2f}%"
            st.markdown(mini_metric("DY (Yield)", fmt_dy), unsafe_allow_html=True)
        with m3:
            pe_val = info.get("trailingPE", 0) or 0
            fmt_pe = f"{pe_val:.2f}"
            st.markdown(mini_metric("P/L", fmt_pe), unsafe_allow_html=True)

        st.markdown("---")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        if rsi:
            rsi_text = f"{rsi:.1f}"
            if rsi > 70:
                rsi_status = "⚠️ Sobrecomprado"
                rsi_color_code = "#FF3B30"
            elif rsi < 30:
                rsi_status = "💎 Sobrevendido"
                rsi_color_code = "#00C805"
            else:
                rsi_status = "Neutro"
                rsi_color_code = "#FFD700"

            st.markdown(
                f"<div style='text-align:center; padding:10px; border:1px solid #333; border-radius:10px; background:#111; margin-top:10px;'>"
                f"<span style='color:#ccc; font-size:13px'>RSI (14):</span> "
                f"<strong style='color:{rsi_color_code}; font-size:18px'>{rsi_text}</strong><br>"
                f"<span style='font-size:11px; color:#777'>{rsi_status}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.warning(
            f"Não conseguimos dados para {tk_real}. Verifique se o ticker está correto (Ex: PETR4.SA) ou se o Yahoo Finance está instável."
        )
