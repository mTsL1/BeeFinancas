import pandas as pd
import streamlit as st

from bee.safe_imports import yf, go
from bee.formatters import fmt_money_brl
from bee.market_data import normalize_ticker, yf_info_extended, get_stock_history_plot, get_google_news_items
from bee.formatters import fmt_ptbr_number


def _max_drawdown_pct(close: pd.Series) -> float:
    if close is None or close.empty: return 0.0
    roll_max = close.cummax()
    dd = close / roll_max - 1.0
    return float(dd.min() * 100.0)


def _vol_annualized_pct(close: pd.Series) -> float:
    if close is None or close.empty: return 0.0
    ret = close.pct_change().dropna()
    if ret.empty: return 0.0
    return float(ret.std() * (252 ** 0.5) * 100.0)


def _apply_analyzer_css():
    st.markdown("""
        <style>
          .kpi-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr); /* 4 colunas no analisador */
            gap: 15px;
            margin-bottom: 25px;
          }
          .kpi-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-top: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center; justify-content: center; text-align: center;
            min-height: 90px; backdrop-filter: blur(10px);
          }
          .kpi-label {
            font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;
            color: rgba(255,255,255,0.6); margin-bottom: 6px; font-weight: 600;
          }
          .kpi-value {
            font-size: 22px; font-weight: 800; color: #ffffff; line-height: 1.1;
          }
          @media (max-width: 900px){ .kpi-container { grid-template-columns: 1fr 1fr; } }
        </style>
    """, unsafe_allow_html=True)


def render_analisar():
    _apply_analyzer_css()  # <<< CSS MÁGICO

    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input("Ativo", placeholder="WEGE3 / PETR4 / IVVB11",
                               label_visibility="collapsed").upper().strip()
    with c_p:
        periodo = st.selectbox("Zoom", ["1mo", "6mo", "1y", "5y", "max"], index=2)

    if not ticker:
        st.caption("Digite um ticker para ver o raio-x.")
        return

    tk_real = normalize_ticker(ticker, "Ação", "BRL")
    info = yf_info_extended(tk_real)
    if not info:
        st.error("Ativo não encontrado ou Yahoo Finance inacessível.")
        return

    st.markdown(f"### {info.get('longName', ticker)}")

    # Dados
    cur_price = info.get("currentPrice", 0.0) or 0.0
    val_dy = info.get("dividendYield")
    dy_txt = f"{float(val_dy) * 100:.2f}%" if val_dy else "—"

    val_pe = info.get("trailingPE")
    pe_txt = f"{float(val_pe):.2f}" if val_pe else "—"

    mcap = info.get("marketCap")
    if mcap:
        x = float(mcap)
        if x >= 1e12:
            mcap_txt = f"{x / 1e12:.2f} T"
        elif x >= 1e9:
            mcap_txt = f"{x / 1e9:.2f} B"
        elif x >= 1e6:
            mcap_txt = f"{x / 1e6:.2f} M"
        else:
            mcap_txt = f"{x:,.0f}"
    else:
        mcap_txt = "—"

    # CARDS HTML NO LUGAR DE ST.METRIC
    st.markdown(f"""
    <div class="kpi-container">
      <div class="kpi-card"><div class="kpi-label">PREÇO</div><div class="kpi-value">{fmt_money_brl(cur_price, 2) if cur_price else "—"}</div></div>
      <div class="kpi-card"><div class="kpi-label">DY</div><div class="kpi-value">{dy_txt}</div></div>
      <div class="kpi-card"><div class="kpi-label">P/L</div><div class="kpi-value">{pe_txt}</div></div>
      <div class="kpi-card"><div class="kpi-label">MARKET CAP</div><div class="kpi-value">{mcap_txt}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Histórico
    if yf is None: return st.warning("yfinance não disponível.")
    try:
        t = yf.Ticker(tk_real)
        hist = t.history(period="2y", auto_adjust=False)
    except:
        hist = pd.DataFrame()

    if hist is None or hist.empty or "Close" not in hist.columns:
        st.warning("Sem histórico suficiente.")
    else:
        close = hist["Close"].dropna()
        sma200 = close.rolling(200).mean()
        sma200_last = float(sma200.dropna().iloc[-1]) if len(sma200.dropna()) else None

        try:
            h1y = t.history(period="1y", auto_adjust=False)
            c1y = h1y["Close"].dropna() if not h1y.empty else close
        except:
            c1y = close

        hi52 = float(c1y.max()) if not c1y.empty else 0
        lo52 = float(c1y.min()) if not c1y.empty else 0
        dd = _max_drawdown_pct(close)
        vol = _vol_annualized_pct(close)

        dist_sma = 0.0
        if sma200_last and cur_price: dist_sma = (float(cur_price) / float(sma200_last) - 1.0) * 100.0

        # CARDS TÉCNICOS HTML
        st.markdown(f"""
        <div class="kpi-container">
          <div class="kpi-card"><div class="kpi-label">52W HIGH</div><div class="kpi-value">{fmt_money_brl(hi52, 2)}</div></div>
          <div class="kpi-card"><div class="kpi-label">52W LOW</div><div class="kpi-value">{fmt_money_brl(lo52, 2)}</div></div>
          <div class="kpi-card"><div class="kpi-label">MAX DRAWDOWN</div><div class="kpi-value" style="color:#f87171;">{dd:.2f}%</div></div>
          <div class="kpi-card"><div class="kpi-label">VOLATILIDADE</div><div class="kpi-value">{vol:.2f}%</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Linha extra centralizada se quiser, ou metrics padrão para dados secundários
        c1, c2 = st.columns(2)
        c1.metric("SMA 200", f"{fmt_money_brl(sma200_last, 2) if sma200_last else '—'}")
        c2.metric("Dist. SMA 200", f"{dist_sma:+.2f}%")

    st.markdown("---")
    fig, rsi = get_stock_history_plot(tk_real, period=periodo)
    if rsi:
        if float(rsi) > 70:
            st.warning(f"RSI (14): {float(rsi):.1f} — Sobrecomprado")
        elif float(rsi) < 30:
            st.success(f"RSI (14): {float(rsi):.1f} — Sobrevendido")
        else:
            st.info(f"RSI (14): {float(rsi):.1f} — Neutro")

    if fig: st.plotly_chart(fig, use_container_width=True)

    with st.expander("🧠 Resumo da Empresa"):
        st.write(info.get("summary", "—"))

    st.markdown("---")
    st.markdown("### 📰 Notícias")
    items = get_google_news_items(f"{ticker} Brasil", limit=5)
    if items:
        for n in items: st.link_button(f"{n['title']} — {n['source']}", n["link"], use_container_width=True)
    else:
        st.info("Sem notícias.")