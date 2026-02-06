import pandas as pd
import streamlit as st
import requests
import feedparser
from datetime import datetime

from .safe_imports import yf, go, px, dtparser, GoogleTranslator
from .formatters import fmt_ptbr_number

def normalize_ticker(ativo: str, tipo: str, moeda: str) -> str:
    a = (ativo or "").strip().upper()
    if not a:
        return ""
    if a.endswith(".SA") or a.endswith("-USD") or a.endswith("=X") or a.startswith("^"):
        return a
    if tipo == "Cripto" or a in ["BTC", "ETH", "SOL", "DOGE", "ADA", "XRP", "DOT", "MATIC"]:
        return a if "-" in a else f"{a}-USD"
    if a in ("BRL=X", "USDBRL", "USD", "DOLAR"):
        return "BRL=X"
    has_digit = any(ch.isdigit() for ch in a)
    if moeda == "BRL" and has_digit and not a.endswith(".SA"):
        return f"{a}.SA"
    return a

def format_market_cap(x: float) -> str:
    try:
        if not x:
            return "—"
        x = float(x)
        if x >= 1e12:
            return f"{x / 1e12:.2f} T"
        if x >= 1e9:
            return f"{x / 1e9:.2f} B"
        if x >= 1e6:
            return f"{x / 1e6:.2f} M"
        return f"{x:,.0f}"
    except Exception:
        return "—"

def calculate_rsi(data, window=14):
    try:
        delta = data["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception:
        return None

@st.cache_data(ttl=600)
def yf_last_and_prev_close(tickers: list[str]) -> pd.DataFrame:
    if yf is None or not tickers:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])
    try:
        data = yf.download(tickers, period="5d", progress=False, threads=True, group_by="ticker", auto_adjust=False)
    except Exception:
        return pd.DataFrame(columns=["ticker", "last", "prev", "var_pct"])

    out = []
    if len(tickers) == 1:
        t = tickers[0]
        try:
            s = data["Close"]
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 2:
                last = float(s.iloc[-1])
                prev = float(s.iloc[-2])
                var_pct = ((last - prev) / prev) * 100 if prev else 0.0
                out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var_pct})
        except Exception:
            pass
    else:
        for t in tickers:
            try:
                s = None
                if isinstance(data.columns, pd.MultiIndex):
                    if ("Close", t) in data.columns:
                        s = data[("Close", t)]
                    elif (t, "Close") in data.columns:
                        s = data[(t, "Close")]
                else:
                    if "Close" in data.columns:
                        s = data["Close"]
                if s is None:
                    continue
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 2:
                    last = float(s.iloc[-1])
                    prev = float(s.iloc[-2])
                    var_pct = ((last - prev) / prev) * 100 if prev else 0.0
                    out.append({"ticker": t, "last": last, "prev": prev, "var_pct": var_pct})
            except Exception:
                pass
    return pd.DataFrame(out)

@st.cache_data(ttl=1200)
def yf_info_extended(ticker: str) -> dict:
    if yf is None or not ticker:
        return {}
    try:
        tk = yf.Ticker(ticker)
        current_price = 0.0
        try:
            h = tk.history(period="5d", auto_adjust=False)
            if not h.empty:
                current_price = float(h["Close"].iloc[-1])
        except Exception:
            pass

        if current_price == 0.0:
            try:
                if hasattr(tk, "fast_info") and tk.fast_info:
                    current_price = float(tk.fast_info.last_price or 0.0)
            except Exception:
                pass

        inf = tk.info or {}

        def safe_get(keys, d="—"):
            for k in keys:
                if k in inf and inf[k]:
                    return inf[k]
            return d

        summary = safe_get(["longBusinessSummary"], "")
        if summary and GoogleTranslator:
            try:
                summary = GoogleTranslator(source="auto", target="pt").translate(summary)
            except Exception:
                pass

        return {
            "currentPrice": current_price,
            "longName": safe_get(["longName", "shortName"], ticker),
            "sector": safe_get(["sector"]),
            "industry": safe_get(["industry"]),
            "summary": summary,
            "trailingPE": safe_get(["trailingPE", "forwardPE"], None),
            "dividendYield": safe_get(["dividendYield"], None),
            "marketCap": safe_get(["marketCap"], None),
            "roe": safe_get(["returnOnEquity"]),
            "margins": safe_get(["profitMargins"]),
            "beta": safe_get(["beta"])
        }
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_stock_history_plot(ticker: str, period="1y"):
    if yf is None or go is None:
        return None, None
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if df.empty:
            return None, None
        fig = go.Figure(data=[
            go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=ticker)
        ])
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=320
        )
        rsi_val = calculate_rsi(df)
        return fig, rsi_val
    except Exception:
        return None, None

@st.cache_data(ttl=900)
def get_google_news_items(query: str, limit: int = 8) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
        items = []
        for e in getattr(feed, "entries", [])[:limit]:
            try:
                p_dt = dtparser.parse(e.published) if dtparser else datetime.now()
            except Exception:
                p_dt = datetime.now()
            title = getattr(e, "title", "Notícia").rsplit(" - ", 1)[0]
            source = getattr(e, "source", {}).get("title") or "News"
            items.append({"title": title, "link": e.link, "source": source, "published_dt": p_dt})
        return items
    except Exception:
        return []

def smart_load_csv(uploaded_file, sep_priority=","):
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=sep_priority)
        if len(df.columns) > 1:
            return df
    except Exception:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";" if sep_priority == "," else ",")
        if len(df.columns) > 1:
            return df
    except Exception:
        pass

    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
        return df
    except Exception:
        pass
    return None

def atualizar_precos_carteira_memory(df):
    df = df.copy()
    if df.empty:
        return df, {"total_brl": 0, "pnl_brl": 0, "pnl_pct": 0}

    usdbrl = 5.80
    if yf is not None:
        try:
            fx = yf_last_and_prev_close(["BRL=X"])
            if not fx.empty:
                usdbrl = float(fx.iloc[0]["last"])
        except Exception:
            pass

    df["Ticker_YF"] = df.apply(
        lambda r: normalize_ticker(str(r["Ativo"]), "Ação", str(r.get("Moeda", "BRL")).upper()),
        axis=1,
    )

    df["Preco_Atual"] = 0.0
    df["Var_Dia_Pct"] = 0.0

    is_rf = df["Tipo"].astype(str).str.contains("Renda Fixa|RF", case=False, na=False)
    df.loc[is_rf, "Preco_Atual"] = df.loc[is_rf, "Preco_Medio"]

    tickers = df.loc[~is_rf, "Ticker_YF"].unique().tolist()
    px_map = {}

    if tickers and yf is not None:
        px_df = yf_last_and_prev_close(tickers)
        for _, r in px_df.iterrows():
            px_map[r["ticker"]] = {"price": float(r["last"]), "var": float(r["var_pct"])}

    for i, row in df.iterrows():
        if bool(is_rf.iloc[i]):
            continue
        data_tick = px_map.get(row["Ticker_YF"], {"price": 0.0, "var": 0.0})
        df.at[i, "Preco_Atual"] = data_tick["price"]
        df.at[i, "Var_Dia_Pct"] = data_tick["var"]

    for c in ["Qtd", "Preco_Medio"]:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["Preco_Atual_BRL"] = df["Preco_Atual"]
    mask_usd_source = df["Ticker_YF"].astype(str).str.endswith("-USD")
    df.loc[mask_usd_source, "Preco_Atual_BRL"] *= usdbrl

    mask_user_usd = df["Moeda"].astype(str).str.upper() == "USD"
    df["Preco_Medio_BRL"] = df["Preco_Medio"]
    df.loc[mask_user_usd, "Preco_Medio_BRL"] = df.loc[mask_user_usd, "Preco_Medio"] * usdbrl

    df["Total_BRL"] = df["Qtd"] * df["Preco_Atual_BRL"]
    df["Custo_BRL"] = df["Qtd"] * df["Preco_Medio_BRL"]
    df["PnL_BRL"] = df["Total_BRL"] - df["Custo_BRL"]
    df["PnL_Pct"] = df.apply(lambda x: (x["PnL_BRL"] / x["Custo_BRL"] * 100) if x["Custo_BRL"] > 0 else 0, axis=1)

    total = float(df["Total_BRL"].sum())
    pnl = float(df["PnL_BRL"].sum())
    custo = float(df["Custo_BRL"].sum())
    pnl_pct = (pnl / custo * 100) if custo > 0 else 0.0

    return df, {"total_brl": total, "pnl_brl": pnl, "pnl_pct": pnl_pct}

def investidor10_link(ativo: str) -> str:
    a = (ativo or "").strip().upper().replace(".SA", "")
    if any(ch.isdigit() for ch in a):
        return f"https://investidor10.com.br/acoes/{a.lower()}/"
    return "https://investidor10.com.br/"
