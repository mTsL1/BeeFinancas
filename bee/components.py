import streamlit as st
from datetime import datetime

from .safe_imports import yf
from .formatters import fmt_ptbr_number, fmt_money_brl, fmt_money_usd
from .market_data import yf_last_and_prev_close

def nav_btn(label, key_page):
    st.sidebar.markdown("<div class='navbtn'>", unsafe_allow_html=True)
    if st.sidebar.button(label, key=f"NAV_{key_page}", use_container_width=True):
        st.session_state["page"] = key_page
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

def kpi_card(title, value, sub="", color=None, compact=False, small=False):
    extra = ""
    if compact:
        extra = "kpi-compact"
    if small:
        extra = "kpi-small"
    st.markdown(
        f"""
<div class="bee-card {extra}" style="{f'border-top: 3px solid {color};' if color else ''}">
  <div class="card-title">{title}</div>
  <div class="kpi">{value}</div>
  <div class="sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True
    )

def sidebar_market_monitor():
    try:
        st.markdown(
            "<div style='font-size:12px; color:#666; font-weight:900; margin-bottom:10px; text-transform:uppercase;'>Market Monitor</div>",
            unsafe_allow_html=True,
        )

        ibov_val = ibov_pct = None
        usd_val = usd_pct = None
        btc_usd_val = btc_usd_pct = None
        btc_brl_val = btc_brl_pct = None

        if yf is not None:
            tickers_monitor = ["^BVSP", "BRL=X", "BTC-USD", "BTC-BRL"]
            snap = yf_last_and_prev_close(tickers_monitor)

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

        def pill(name, price_text, pct):
            cor = "tp-up" if (pct is not None and pct >= 0) else "tp-down"
            color = "#00C805" if (pct is not None and pct >= 0) else "#FF3B30"
            pct_txt = f"{pct:+.2f}%" if pct is not None else "—"
            st.markdown(
                f"""
<div class='ticker-pill {cor}'>
  <span class='tp-name'>{name}</span>
  <div style='display:flex; align-items:center; gap:10px;'>
    <span class='tp-price'>{price_text}</span>
    <span class='tp-pct' style='color:{color};'>{pct_txt}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        pill("IBOV", f"{fmt_ptbr_number(ibov_val, 0)}" if ibov_val is not None else "—", ibov_pct)
        pill("USD/BRL", f"{fmt_money_brl(usd_val, 2)}" if usd_val is not None else "—", usd_pct)
        pill("BTC (US$)", fmt_money_usd(btc_usd_val, 0) if btc_usd_val is not None else "—", btc_usd_pct)
        pill("BTC (R$)", f"R$ {fmt_ptbr_number(btc_brl_val, 0)}" if btc_brl_val is not None else "—", btc_brl_pct)

    except Exception:
        pass

def top_bar():
    c_spacer, c_info = st.columns([6, 2.5])
    with c_spacer:
        st.write("")
    with c_info:
        c_clock, c_btn = st.columns([2.5, 1], gap="small")
        with c_clock:
            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            st.markdown(
                f"""
            <div style='
                display: flex; 
                justify-content: center; 
                align-items: center;
                height: 38px;
                border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 8px; 
                color: #BDBDBD; 
                font-size: 13px; 
                background: rgba(255,255,255,0.03);
                font-weight: 600;
            '>
                🕒 {now_str}
            </div>
            """,
                unsafe_allow_html=True
            )
        with c_btn:
            if st.button("↻", key="top_refresh", help="Atualizar dados", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.06); margin-top:10px'>", unsafe_allow_html=True)
