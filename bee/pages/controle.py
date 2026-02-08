import re
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# =========================================================
# IMPORTS DO SEU PROJETO (BEE)
# =========================================================
from bee.config import DB_FILE
from bee.safe_imports import px
from bee.formatters import fmt_money_brl
from bee.db import (
    save_user_data_db, get_budgets_db, set_budget_db,
    list_rules_db, add_rule_db,
    list_recurring_db, add_recurring_db, set_recurring_active_db
)

GASTOS_COLS = ["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"]


# =========================================================
# 1. HELPERS E CSS (VISUAL UNIFICADO)
# =========================================================
def _to_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _ym(series: pd.Series) -> pd.Series:
    return _to_dt(series).dt.strftime("%Y-%m")


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _compact_brl(v: float) -> str:
    # Helper visual para números grandes
    try:
        v = float(v)
    except:
        return "R$ 0"
    return fmt_money_brl(v, 2)


def _apply_unified_css():
    st.markdown("""
        <style>
          /* --- KPI CARDS (PADRÃO GLOBAL) --- */
          .kpi-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr); /* 4 colunas no controle */
            gap: 15px;
            margin-bottom: 25px;
          }
          .kpi-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-top: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center; justify-content: center; text-align: center;
            min-height: 100px; backdrop-filter: blur(10px);
          }
          .kpi-label {
            font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase;
            color: rgba(255,255,255,0.6); margin-bottom: 8px; font-weight: 600;
          }
          .kpi-value {
            font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.1;
          }

          /* --- BOTÕES DE NAVEGAÇÃO UNIFORMES --- */
          div[data-testid="column"] > div > div > div > button {
             width: 100% !important; height: 60px !important;
             border: 1px solid rgba(255,255,255,0.08) !important;
             background: rgba(255, 255, 255, 0.03) !important;
             border-radius: 12px !important; transition: all 0.2s ease !important;
             font-weight: 600 !important; font-size: 15px !important;
          }
          div[data-testid="column"] > div > div > div > button:hover {
             background: rgba(255, 255, 255, 0.08) !important;
             border-color: rgba(255,255,255,0.2) !important; transform: translateY(-2px);
          }

          /* Responsividade */
          @media (max-width: 900px){ .kpi-container { grid-template-columns: 1fr 1fr; } }
          @media (max-width: 600px){ .kpi-container { grid-template-columns: 1fr; } }
        </style>
    """, unsafe_allow_html=True)


# =========================================================
# 2. DATA HANDLERS (SEU CÓDIGO MANTIDO)
# =========================================================
def _get_budgets(username: str) -> dict:
    try:
        return get_budgets_db(username, DB_FILE)
    except:
        return get_budgets_db(DB_FILE, username)


def _set_budget(username: str, categoria: str, budget: float):
    try:
        set_budget_db(username, categoria, budget, DB_FILE)
    except:
        set_budget_db(DB_FILE, username, categoria, budget)


def _list_rules(username: str) -> list[dict]:
    try:
        return list_rules_db(username, DB_FILE)
    except:
        return list_rules_db(DB_FILE, username)


def _add_rule(username: str, pattern: str, categoria: str, active: int = 1):
    try:
        add_rule_db(username, pattern, categoria, active, DB_FILE)
    except:
        add_rule_db(DB_FILE, username, pattern, categoria, active)


def _list_recurring(username: str) -> list[dict]:
    try:
        return list_recurring_db(username, DB_FILE)
    except:
        return list_recurring_db(DB_FILE, username)


def _add_recurring(username: str, categoria: str, desc: str, tipo: str, val: float, pay: str, dom: int,
                   active: int = 1):
    try:
        add_recurring_db(username, desc, categoria, tipo, val, pay, dom, active, DB_FILE)
    except:
        add_recurring_db(DB_FILE, username, categoria, desc, tipo, val, pay, dom, active)


def _set_recurring_active(username: str, rec_id: int, active: int):
    try:
        set_recurring_active_db(username, rec_id, active, DB_FILE)
    except:
        set_recurring_active_db(DB_FILE, username, rec_id, active)


def _ensure_gastos_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0: return pd.DataFrame(columns=GASTOS_COLS)
    df = df.copy()
    rename_map = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["data", "date"]:
            rename_map[col] = "Data"
        elif c in ["categoria", "category"]:
            rename_map[col] = "Categoria"
        elif c in ["descricao", "descrição", "description", "historico"]:
            rename_map[col] = "Descricao"
        elif c in ["tipo", "type"]:
            rename_map[col] = "Tipo"
        elif c in ["valor", "value", "amount", "total"]:
            rename_map[col] = "Valor"
        elif c in ["pagamento", "payment", "forma"]:
            rename_map[col] = "Pagamento"
    if rename_map: df.rename(columns=rename_map, inplace=True)
    for col in GASTOS_COLS:
        if col not in df.columns: df[col] = ""
    df = df[GASTOS_COLS]
    df["Data"] = _to_dt(df["Data"])
    df = df.dropna(subset=["Data"])
    if df["Valor"].dtype == object:
        df["Valor"] = df["Valor"].astype(str).str.replace("R$", "", regex=False).str.replace(".", "",
                                                                                             regex=False).str.replace(
            ",", ".", regex=False).str.strip()
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    df["Tipo"] = df["Tipo"].astype(str).str.strip()
    df.loc[df["Tipo"].str.lower().isin(["saida", "saída"]), "Tipo"] = "Saída"
    df.loc[df["Tipo"].str.lower().isin(["entrada"]), "Tipo"] = "Entrada"
    df.loc[~df["Tipo"].isin(["Entrada", "Saída"]), "Tipo"] = "Saída"
    df["Categoria"] = df["Categoria"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Categoria"] == "", "Categoria"] = "Outros"
    df["Descricao"] = df["Descricao"].astype(str).replace("nan", "").str.strip()
    df["Pagamento"] = df["Pagamento"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Pagamento"] == "", "Pagamento"] = "Pix"
    return df


def _append_rows(gastos_df: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    base = _ensure_gastos_columns(gastos_df)
    if not rows: return base
    return _ensure_gastos_columns(pd.concat([base, _ensure_gastos_columns(pd.DataFrame(rows))], ignore_index=True))


def _spent_by_category_month(gastos_df: pd.DataFrame, month_key: str) -> dict:
    df = _ensure_gastos_columns(gastos_df)
    if df.empty: return {}
    dfm = df[_ym(df["Data"]) == month_key]
    dfm = dfm[dfm["Tipo"].astype(str).str.lower() == "saída"]
    if dfm.empty: return {}
    return dfm.groupby("Categoria")["Valor"].sum().to_dict()


# --- Recorrência ---
def _recurring_was_applied(username: str, rec_id: int, yyyymm: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS recurring_log (username TEXT, recurring_id INTEGER, yyyymm TEXT, PRIMARY KEY (username, recurring_id, yyyymm))")
    c.execute("SELECT 1 FROM recurring_log WHERE username=? AND recurring_id=? AND yyyymm=?",
              (username, int(rec_id), yyyymm))
    ok = c.fetchone() is not None
    conn.close()
    return ok


def _mark_recurring_applied(username: str, rec_id: int, yyyymm: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO recurring_log(username, recurring_id, yyyymm) VALUES(?,?,?)",
              (username, int(rec_id), yyyymm))
    conn.commit()
    conn.close()


def _apply_recurring_for_month(username: str, gastos_df: pd.DataFrame, yyyymm: str) -> tuple[pd.DataFrame, int]:
    rec_list = _list_recurring(username)
    df_rec = pd.DataFrame(rec_list)
    if df_rec.empty: return _ensure_gastos_columns(gastos_df), 0
    created = 0
    rows = []
    year, month = int(yyyymm.split("-")[0]), int(yyyymm.split("-")[1])
    for _, r in df_rec.iterrows():
        rec_id = int(r.get("rec_id") or r.get("id") or 0)
        if int(r.get("active", 1)) != 1: continue
        if _recurring_was_applied(username, rec_id, yyyymm): continue
        dom = int(r.get("day_of_month") or r.get("Dia") or 5)
        dt = datetime(year, month, max(1, min(28, dom)))
        rows.append({
            "Data": dt, "Categoria": str(r.get("categoria") or "Outros"), "Descricao": str(r.get("descricao") or ""),
            "Tipo": "Entrada" if str(r.get("tipo")).lower() == "entrada" else "Saída",
            "Valor": float(r.get("valor") or 0.0),
            "Pagamento": str(r.get("pagamento") or "Pix")
        })
        _mark_recurring_applied(username, rec_id, yyyymm)
        created += 1
    if created > 0: gastos_df = _append_rows(gastos_df, rows)
    return _ensure_gastos_columns(gastos_df), created


# --- Import CSV ---
def _smart_load_csv(uploaded_file) -> pd.DataFrame | None:
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file)
    except:
        pass
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file, sep=";")
    except:
        pass
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file, sep=";", encoding="latin1")
    except:
        return None


def _pick_pattern(text: str) -> str:
    s = re.sub(r"[^a-z0-9\s]", " ", str(text or "").lower())
    parts = [p.strip() for p in s.split() if len(p.strip()) >= 4]
    return parts[0] if parts else (s[:12].strip() or "rule")


def _apply_rules(rules_df: pd.DataFrame, desc: str) -> str:
    d = (desc or "").lower()
    if rules_df is None or rules_df.empty: return "Outros"
    for _, r in rules_df.iterrows():
        if int(r.get("active", 1)) == 0: continue
        if str(r.get("pattern", "")).lower().strip() in d: return str(r.get("categoria", "Outros"))
    return "Outros"


# =========================================================
# 3. INTERFACE (MODAL & VIEWS)
# =========================================================

@st.dialog("➕ Nova transação")
def _show_new_tx_dialog(username: str):
    st.caption("Adicione um lançamento rápido.")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()

    default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Saúde", "Educação",
                    "Outros"]
    existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
    all_cats = sorted(list(set(default_cats + existing_cats))) + ["➕ Nova (Digitar abaixo)"]

    mode = st.segmented_control("Data", options=["Hoje", "Ontem", "📅 Escolher"], default="Hoje", key="dlg_tx_date_mode")
    picked_date = today.date()
    if mode == "Ontem":
        picked_date = (today - timedelta(days=1)).date()
    elif mode == "📅 Escolher":
        picked_date = st.date_input("Escolher data", value=today.date(), key="dlg_tx_date_pick")

    c1, c2, c3 = st.columns([1, 1.2, 1])
    d_tipo = c1.selectbox("Tipo", ["Saída", "Entrada"], key="dlg_tx_tipo")
    d_pag = c2.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"], key="dlg_tx_pag")
    d_val = c3.number_input("Valor (R$)", min_value=0.0, step=10.0, key="dlg_tx_val")

    c4, c5 = st.columns([1.2, 1])
    d_cat_select = c4.selectbox("Categoria", all_cats, key="dlg_tx_cat_sel")
    d_cat_input = c4.text_input("Nova categoria", placeholder="Ex: Pet", key="dlg_tx_cat_in")
    d_desc = c5.text_input("Descrição", placeholder="Ex: Mercado / Uber", key="dlg_tx_desc")

    st.markdown("<br>", unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        if st.button("Salvar", type="primary", use_container_width=True, key="dlg_tx_save"):
            final_cat = d_cat_input if (d_cat_select == "➕ Nova (Digitar abaixo)" and d_cat_input) else d_cat_select
            if final_cat == "➕ Nova (Digitar abaixo)": final_cat = "Outros"
            new_row = {
                "Data": pd.to_datetime(picked_date), "Categoria": final_cat, "Descricao": d_desc.strip(),
                "Tipo": "Entrada" if d_tipo == "Entrada" else "Saída", "Valor": float(d_val), "Pagamento": d_pag
            }
            df_new = _append_rows(df_g, [new_row])
            st.session_state["gastos_df"] = df_new
            save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()),
                              st.session_state["gastos_df"])
            st.toast("Transação salva!", icon="✅")
            st.rerun()
    with b:
        if st.button("Cancelar", use_container_width=True, key="dlg_tx_cancel"): st.rerun()


def _nav_btn(label: str, tab_key: str, icon: str = ""):
    active = st.session_state.get("controle_tab", "Dashboard") == tab_key
    caption = f"{icon} {label}".strip()
    if st.button(caption, use_container_width=True, key=f"ctl_nav_{tab_key}"):
        st.session_state["controle_tab"] = tab_key
        st.rerun()


# --- VIEWS ---

def _render_dashboard(username: str):
    st.subheader("📊 Dashboard do mês")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()
    mes = _month_key(today)
    dfm = df_g[_ym(df_g["Data"]) == mes].copy()

    total_ent = float(dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum()) if not dfm.empty else 0.0
    total_sai = float(dfm[dfm["Tipo"] == "Saída"]["Valor"].sum()) if not dfm.empty else 0.0

    # Previsão
    dias = max(1, today.day)
    try:
        last_day = (datetime(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1,
                             1) - timedelta(days=1)).day
    except:
        last_day = 30
    prev_gasto = (total_sai / dias) * last_day if dias > 0 else 0.0

    # HTML CARDS para ficarem iguais à carteira
    st.markdown(f"""
    <div class="kpi-container">
      <div class="kpi-card"><div class="kpi-label">RECEITAS (MÊS)</div><div class="kpi-value" style="color:#4ade80;">{_compact_brl(total_ent)}</div></div>
      <div class="kpi-card"><div class="kpi-label">DESPESAS (MÊS)</div><div class="kpi-value" style="color:#f87171;">{_compact_brl(total_sai)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SALDO ATUAL</div><div class="kpi-value">{_compact_brl(total_ent - total_sai)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SALDO PREVISTO</div><div class="kpi-value">{_compact_brl(total_ent - prev_gasto)}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔥 Top gastos")
    if not dfm.empty:
        df_cat = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index().sort_values("Valor",
                                                                                                           ascending=False)
        l, r = st.columns([1.2, 1])
        with l:
            st.dataframe(df_cat.head(12), use_container_width=True, hide_index=True,
                         column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})
        with r:
            if px:
                fig = px.pie(df_cat.head(10), values="Valor", names="Categoria", hole=0.55)
                fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados neste mês.")


def _render_extrato(username: str):
    st.subheader("📒 Extrato")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()
    meses_disp = sorted(list(set(_ym(df_g["Data"]).dropna().tolist()))) if not df_g.empty else [_month_key(today)]

    col_sel, col_btn = st.columns([2, 1])
    mes = col_sel.selectbox("📅 Mês", meses_disp, index=len(meses_disp) - 1, key="controle_mes")
    if col_btn.button("🔁 Gerar recorrentes", use_container_width=True):
        df_new, created = _apply_recurring_for_month(username, df_g, mes)
        st.session_state["gastos_df"] = df_new
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast(f"Criados: {created}", icon="🔁")
        st.rerun()

    dfm = df_g[_ym(df_g["Data"]) == mes].copy()
    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1, 1.2])
    q = f1.text_input("🔎 Buscar", key="c_busca")
    cat = f2.selectbox("Categoria", ["Todas"] + sorted(dfm["Categoria"].unique()) if not dfm.empty else ["Todas"],
                       key="c_cat")
    tipo = f3.selectbox("Tipo", ["Todos", "Saída", "Entrada"], key="c_tipo")

    if q: dfm = dfm[dfm["Descricao"].str.lower().str.contains(q.lower(), na=False)]
    if cat != "Todas": dfm = dfm[dfm["Categoria"] == cat]
    if tipo != "Todos": dfm = dfm[dfm["Tipo"] == tipo]

    # KPIs rápidos no Extrato também
    total_ent = float(dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum()) if not dfm.empty else 0.0
    total_sai = float(dfm[dfm["Tipo"] == "Saída"]["Valor"].sum()) if not dfm.empty else 0.0
    st.markdown(f"""
    <div class="kpi-container" style="grid-template-columns: repeat(3, 1fr); margin-bottom:10px;">
       <div class="kpi-card" style="min-height:80px;"><div class="kpi-label">ENTRADAS</div><div class="kpi-value" style="font-size:20px; color:#4ade80;">{_compact_brl(total_ent)}</div></div>
       <div class="kpi-card" style="min-height:80px;"><div class="kpi-label">SAÍDAS</div><div class="kpi-value" style="font-size:20px; color:#f87171;">{_compact_brl(total_sai)}</div></div>
       <div class="kpi-card" style="min-height:80px;"><div class="kpi-label">SALDO MÊS</div><div class="kpi-value" style="font-size:20px;">{_compact_brl(total_ent - total_sai)}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🧾 Editar Extrato")
    df_edit = st.data_editor(
        dfm.sort_values("Data", ascending=False), num_rows="dynamic", use_container_width=True, height=380,
        key="editor_gastos",
        column_config={"Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
                       "Valor": st.column_config.NumberColumn(format="R$ %.2f")}
    )
    if st.button("💾 Salvar Extrato", type="primary", use_container_width=True):
        df_other = df_g[_ym(df_g["Data"]) != mes].copy()
        st.session_state["gastos_df"] = _ensure_gastos_columns(pd.concat([df_other, df_edit], ignore_index=True))
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast("Salvo!", icon="✅")
        st.rerun()


def _render_envelopes(username: str):
    st.subheader("📦 Envelopes (Metas)")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    budgets = _get_budgets(username)
    spent = _spent_by_category_month(df_g, _month_key(datetime.now()))
    all_cats = sorted(
        set(list(spent.keys()) + list(budgets.keys()) + ["Moradia", "Alimentação", "Transporte", "Lazer", "Outros"]))

    c1, c2, c3 = st.columns([1.2, 1, 1])
    cat = c1.selectbox("Categoria", all_cats, key="env_cat")
    lim = c2.number_input("Meta (R$)", 0.0, step=50.0, value=float(budgets.get(cat, 0.0)), key="env_lim")
    if c3.button("Salvar Meta", type="primary", use_container_width=True):
        _set_budget(username, cat, lim)
        st.rerun()

    st.markdown("---")
    for cat in all_cats:
        lim = float(budgets.get(cat, 0.0))
        sp = float(spent.get(cat, 0.0))
        if lim <= 0: continue
        pct = min(1.0, sp / lim)
        with st.container(border=True):
            a, b, c = st.columns([1.2, 1, 1])
            a.markdown(f"**{cat}**");
            b.write(f"Meta: {fmt_money_brl(lim, 2)}");
            c.write(f"Gasto: {fmt_money_brl(sp, 2)}")
            st.progress(pct);
            st.caption(f"Uso: {pct * 100:.1f}%")


def _render_recorrencias(username: str):
    st.subheader("🔁 Recorrências")
    with st.expander("➕ Nova recorrência", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        cat = c1.text_input("Categoria", value="Moradia", key="rec_cat")
        desc = c2.text_input("Descrição", key="rec_desc")
        kind = c3.selectbox("Tipo", ["Saída", "Entrada"], key="rec_tipo")
        dom = c4.number_input("Dia (1-28)", 1, 28, 5, key="rec_dom")
        c5, c6 = st.columns(2)
        val = c5.number_input("Valor", 0.0, step=10.0, value=100.0, key="rec_val")
        if c6.button("Salvar", type="primary", use_container_width=True):
            _add_recurring(username, cat, desc, kind, float(val), "Pix", int(dom))
            st.rerun()

    df = pd.DataFrame(_list_recurring(username))
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        cA, cB, cC = st.columns([1, 1, 2])
        rid = cA.number_input("ID", 1, step=1, key="rec_id_tog")
        act = cB.selectbox("Ação", ["Ativar", "Desativar"], key="rec_act_tog")
        if cC.button("Aplicar", use_container_width=True):
            _set_recurring_active(username, rid, 1 if act == "Ativar" else 0)
            st.rerun()


def _render_import_csv(username: str):
    st.subheader("📥 Importar CSV")
    up = st.file_uploader("Subir Extrato/Fatura", type=["csv"], key="up_csv_gastos")
    if not up: return
    df_raw = _smart_load_csv(up)
    if df_raw is None: return st.error("CSV inválido.")

    cols = {str(c).lower(): c for c in df_raw.columns}
    col_desc = cols.get("descricao") or cols.get("description") or cols.get("histórico")
    col_val = cols.get("valor") or cols.get("amount") or cols.get("total")
    col_date = cols.get("data") or cols.get("date")

    if not (col_desc and col_val): return st.error("Colunas não identificadas.")

    df = df_raw.copy()
    df["Descricao"] = df[col_desc].astype(str)
    df["Valor"] = pd.to_numeric(
        df[col_val].astype(str).str.replace("R$", "", regex=False).str.replace(".", "", regex=False).str.replace(",",
                                                                                                                 ".",
                                                                                                                 regex=False),
        errors="coerce").fillna(0.0)
    df["Data"] = _to_dt(df[col_date]) if col_date else datetime.now().date()

    rules = pd.DataFrame(_list_rules(username))
    df["Categoria"] = df["Descricao"].apply(lambda x: _apply_rules(rules, x))

    edited = st.data_editor(df[["Data", "Descricao", "Valor", "Categoria"]], use_container_width=True, height=350)
    tipo = st.selectbox("Tipo", ["Saída", "Entrada"], key="imp_tipo")
    if st.button("✅ Importar", type="primary", use_container_width=True):
        rows = []
        for _, r in edited.iterrows():
            rows.append({
                "Data": pd.to_datetime(r["Data"]), "Categoria": r["Categoria"], "Descricao": r["Descricao"],
                "Tipo": tipo, "Valor": abs(float(r["Valor"])), "Pagamento": "Crédito"
            })
            pat = _pick_pattern(r["Descricao"])
            if pat: _add_rule(username, pat, r["Categoria"])

        df_new = _append_rows(st.session_state.get("gastos_df", pd.DataFrame()), rows)
        st.session_state["gastos_df"] = df_new
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast("Importado!", icon="✅")
        st.rerun()


# =========================================================
# MAIN ENTRY
# =========================================================
def render_controle():
    _apply_unified_css()  # <<< CSS MÁGICO AQUI
    username = st.session_state.get("username", "") or "guest"
    st.markdown("# 💸 Controle")
    st.caption("Gastos, Orçamento e Recorrências")

    if st.button("➕ Nova transação", type="primary", use_container_width=True):
        _show_new_tx_dialog(username)

    if "controle_tab" not in st.session_state: st.session_state["controle_tab"] = "Dashboard"

    # Navegação com 5 botões iguais
    n1, n2, n3, n4, n5 = st.columns(5, gap="small")
    with n1:
        _nav_btn("Dashboard", "Dashboard", "📊")
    with n2:
        _nav_btn("Extrato", "Extrato", "📒")
    with n3:
        _nav_btn("Envelopes", "Envelopes", "📦")
    with n4:
        _nav_btn("Recorrências", "Recorrências", "🔁")
    with n5:
        _nav_btn("Importar CSV", "Importar CSV", "📥")

    st.markdown("---")
    tab = st.session_state["controle_tab"]

    if tab == "Dashboard":
        _render_dashboard(username)
    elif tab == "Extrato":
        _render_extrato(username)
    elif tab == "Envelopes":
        _render_envelopes(username)
    elif tab == "Recorrências":
        _render_recorrencias(username)
    else:
        _render_import_csv(username)