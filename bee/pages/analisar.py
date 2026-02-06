import pandas as pd
import streamlit as st

from bee.safe_imports import yf, go
from bee.formatters import fmt_money_brl
from bee.market_data import normalize_ticker, yf_info_extended, get_stock_history_plot, get_google_news_items
from bee.formatters import fmt_ptbr_number


def _max_drawdown_pct(close: pd.Series) -> float:
    if close is None or close.empty:
        return 0.0
    roll_max = close.cummax()
    dd = close / roll_max - 1.0
    return float(dd.min() * 100.0)


def _vol_annualized_pct(close: pd.Series) -> float:
    if close is None or close.empty:
        return 0.0
    ret = close.pct_change().dropna()
    if ret.empty:
        return 0.0
    return float(ret.std() * (252 ** 0.5) * 100.0)


def render_analisar():
    # Ajuste fino: diminuir fonte dos st.metric para não cortar valores
    st.markdown("""
    <style>
    /* Só ajustes visuais (afeta apenas esta página) */
    div[data-testid="stMetricValue"] {
      font-size: 22px !important;
      line-height: 1.05 !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
    }
    div[data-testid="stMetricLabel"] {
      font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    c_s, c_p = st.columns([3, 1])
    with c_s:
        ticker = st.text_input(
            "Ativo",
            placeholder="WEGE3 / PETR4 / IVVB11 / AAPL / BTC",
            label_visibility="collapsed",
        ).upper().strip()
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

    # blocão de métricas Yahoo
    cur_price = info.get("currentPrice", 0.0) or 0.0
    val_dy = info.get("dividendYield")
    val_pe = info.get("trailingPE")
    mcap = info.get("marketCap")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Preço", fmt_money_brl(cur_price, 2) if cur_price else "—")
    with m2:
        if val_dy is None:
            st.metric("DY", "—")
        else:
            st.metric("DY", f"{float(val_dy) * 100:.2f}%")
    with m3:
        st.metric("P/L", f"{float(val_pe):.2f}" if val_pe else "—")
    with m4:
        if not mcap:
            st.metric("Market Cap", "—")
        else:
            # formata cap de forma simples
            x = float(mcap)
            if x >= 1e12:
                txt = f"{x/1e12:.2f} T"
            elif x >= 1e9:
                txt = f"{x/1e9:.2f} B"
            elif x >= 1e6:
                txt = f"{x/1e6:.2f} M"
            else:
                txt = f"{x:,.0f}"
            st.metric("Market Cap", txt)

    st.markdown("---")

    # histórico pra cálculos pro
    if yf is None:
        st.warning("yfinance não disponível no ambiente.")
        return

    try:
        t = yf.Ticker(tk_real)
        hist = t.history(period="2y", auto_adjust=False)
    except Exception:
        hist = pd.DataFrame()

    if hist is None or hist.empty or "Close" not in hist.columns:
        st.warning("Sem histórico suficiente para métricas avançadas.")
    else:
        close = hist["Close"].dropna()
        sma200 = close.rolling(200).mean()
        sma200_last = float(sma200.dropna().iloc[-1]) if len(sma200.dropna()) else None

        # 52w
        try:
            h1y = t.history(period="1y", auto_adjust=False)
            c1y = h1y["Close"].dropna() if h1y is not None and not h1y.empty else close
        except Exception:
            c1y = close

        hi52 = float(c1y.max()) if not c1y.empty else None
        lo52 = float(c1y.min()) if not c1y.empty else None

        dd = _max_drawdown_pct(close)
        vol = _vol_annualized_pct(close)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("52W High", f"{hi52:,.2f}" if hi52 else "—")
        with c2:
            st.metric("52W Low", f"{lo52:,.2f}" if lo52 else "—")
        with c3:
            st.metric("SMA200", f"{sma200_last:,.2f}" if sma200_last else "—")
        with c4:
            st.metric("Max Drawdown", f"{dd:.2f}%")

        c5, c6 = st.columns(2)
        with c5:
            st.metric("Volatilidade (anual)", f"{vol:.2f}%")
        with c6:
            if sma200_last and cur_price:
                dist = (float(cur_price) / float(sma200_last) - 1.0) * 100.0
                st.metric("Distância da SMA200", f"{dist:+.2f}%")
            else:
                st.metric("Distância da SMA200", "—")

    # gráfico + RSI (se seu market_data retorna)
    st.markdown("---")
    fig, rsi = get_stock_history_plot(tk_real, period=periodo)

    if rsi:
        rsi_text = f"{float(rsi):.1f}"
        if float(rsi) > 70:
            st.warning(f"RSI (14): {rsi_text} — Sobrecomprado (risco de correção)")
        elif float(rsi) < 30:
            st.success(f"RSI (14): {rsi_text} — Sobrevendido (pode ser oportunidade)")
        else:
            st.info(f"RSI (14): {rsi_text} — Neutro")

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Sem gráfico disponível. Yahoo Finance pode estar instável para este ativo.")

    # resumo
    with st.expander("🧠 Resumo da Empresa", expanded=False):
        st.write(info.get("summary", "—"))

    # notícias contextualizadas (ticker + brasil)
    st.markdown("---")
    st.markdown("### 📰 Notícias do ativo")
    q = f"{ticker} Brasil"
    items = get_google_news_items(q, limit=8)
    if items:
        for n in items:
            st.link_button(f"{n['title']} — {n['source']}", n["link"], use_container_width=True)
    else:
        st.info("Sem notícias agora.")
