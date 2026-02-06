import re
import sqlite3
from datetime import datetime, date

import pandas as pd
import streamlit as st

from bee.config import DB_FILE
from bee.safe_imports import px
from bee.formatters import fmt_money_brl

from bee.db import (
    save_user_data_db,
    get_budgets_db, set_budget_db,
    list_rules_db, add_rule_db,
    list_recurring_db, add_recurring_db, set_recurring_active_db
)

GASTOS_COLS = ["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"]


# =========================================================
# Compat helpers (pra não quebrar se a ordem do db variar)
# =========================================================
def _get_budgets(username: str) -> dict:
    try:
        # versão (username, db_file)
        return get_budgets_db(username, DB_FILE)  # type: ignore
    except Exception:
        try:
            # versão (db_file, username)
            return get_budgets_db(DB_FILE, username)  # type: ignore
        except Exception:
            return {}


def _set_budget(username: str, categoria: str, budget: float):
    try:
        set_budget_db(username, categoria, budget, DB_FILE)  # type: ignore
    except Exception:
        try:
            set_budget_db(DB_FILE, username, categoria, budget)  # type: ignore
        except Exception:
            pass


def _list_rules(username: str) -> list[dict]:
    try:
        return list_rules_db(username, DB_FILE)  # type: ignore
    except Exception:
        try:
            return list_rules_db(DB_FILE, username)  # type: ignore
        except Exception:
            return []


def _add_rule(username: str, pattern: str, categoria: str, active: int = 1):
    try:
        add_rule_db(username, pattern, categoria, active, DB_FILE)  # type: ignore
    except Exception:
        try:
            add_rule_db(DB_FILE, username, pattern, categoria, active)  # type: ignore
        except Exception:
            pass


def _list_recurring(username: str) -> list[dict]:
    try:
        return list_recurring_db(username, DB_FILE)  # type: ignore
    except Exception:
        try:
            return list_recurring_db(DB_FILE, username)  # type: ignore
        except Exception:
            return []


def _add_recurring(username: str, categoria: str, desc: str, tipo: str, val: float, pay: str, dom: int, active: int = 1):
    try:
        # versão (username, descricao, categoria, tipo, valor, pagamento, day_of_month, active, db_file)
        add_recurring_db(username, desc, categoria, tipo, val, pay, dom, active, DB_FILE)  # type: ignore
    except Exception:
        try:
            # versão (db_file, username, categoria, desc, tipo, val, pay, dom, active)
            add_recurring_db(DB_FILE, username, categoria, desc, tipo, val, pay, dom, active)  # type: ignore
        except Exception:
            pass


def _set_recurring_active(username: str, rec_id: int, active: int):
    try:
        set_recurring_active_db(username, rec_id, active, DB_FILE)  # type: ignore
    except Exception:
        try:
            set_recurring_active_db(DB_FILE, username, rec_id, active)  # type: ignore
        except Exception:
            pass


# =========================================================
# Data helpers
# =========================================================
def _ensure_gastos_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=GASTOS_COLS)

    df = df.copy()

    # normaliza nomes comuns
    rename_map = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["data", "date"]:
            rename_map[col] = "Data"
        elif c in ["categoria", "category"]:
            rename_map[col] = "Categoria"
        elif c in ["descricao", "descrição", "description", "desc", "historico", "histórico"]:
            rename_map[col] = "Descricao"
        elif c in ["tipo", "type"]:
            rename_map[col] = "Tipo"
        elif c in ["valor", "value", "amount", "total"]:
            rename_map[col] = "Valor"
        elif c in ["pagamento", "payment", "forma", "forma_pagamento"]:
            rename_map[col] = "Pagamento"

    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    for col in GASTOS_COLS:
        if col not in df.columns:
            df[col] = ""

    df = df[GASTOS_COLS]

    # datas
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Data"])

    # valores
    if df["Valor"].dtype == object:
        df["Valor"] = (
            df["Valor"].astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    # tipo
    df["Tipo"] = df["Tipo"].astype(str).str.strip()
    # aceita "Entrada"/"Saída" e também "Saida"
    df.loc[df["Tipo"].str.lower().isin(["saida", "saída"]), "Tipo"] = "Saída"
    df.loc[~df["Tipo"].isin(["Entrada", "Saída"]), "Tipo"] = "Saída"

    df["Categoria"] = df["Categoria"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Categoria"] == "", "Categoria"] = "Outros"

    df["Descricao"] = df["Descricao"].astype(str).replace("nan", "").str.strip()
    df["Pagamento"] = df["Pagamento"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Pagamento"] == "", "Pagamento"] = "Pix"

    return df


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _append_rows(gastos_df: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return gastos_df
    add = pd.DataFrame(rows)
    add["Data"] = pd.to_datetime(add["Data"], errors="coerce")
    add = add.dropna(subset=["Data"])
    out = pd.concat([gastos_df, add], ignore_index=True)
    out["Data"] = pd.to_datetime(out["Data"], errors="coerce")
    out = out.dropna(subset=["Data"])
    return out


def _spent_by_category_month(gastos_df: pd.DataFrame, month_key: str) -> dict:
    if gastos_df is None or gastos_df.empty:
        return {}
    df = gastos_df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    dfm = df[df["Data"].dt.strftime("%Y-%m") == month_key]
    dfm = dfm[dfm["Tipo"].astype(str).str.lower() == "saída"]
    if dfm.empty:
        return {}
    return dfm.groupby("Categoria")["Valor"].sum().to_dict()


# =========================================================
# Recurring log (anti-duplicação)
# =========================================================
def _recurring_was_applied(username: str, rec_id: int, yyyymm: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS recurring_log (
            username TEXT,
            recurring_id INTEGER,
            yyyymm TEXT,
            PRIMARY KEY (username, recurring_id, yyyymm)
        )
    """)
    c.execute("SELECT 1 FROM recurring_log WHERE username=? AND recurring_id=? AND yyyymm=?",
              (username, int(rec_id), yyyymm))
    ok = c.fetchone() is not None
    conn.close()
    return ok


def _mark_recurring_applied(username: str, rec_id: int, yyyymm: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS recurring_log (
            username TEXT,
            recurring_id INTEGER,
            yyyymm TEXT,
            PRIMARY KEY (username, recurring_id, yyyymm)
        )
    """)
    c.execute("INSERT OR IGNORE INTO recurring_log(username, recurring_id, yyyymm) VALUES(?,?,?)",
              (username, int(rec_id), yyyymm))
    conn.commit()
    conn.close()


def _apply_recurring_for_month(username: str, gastos_df: pd.DataFrame, yyyymm: str) -> tuple[pd.DataFrame, int]:
    rec_list = _list_recurring(username)
    df_rec = pd.DataFrame(rec_list)
    if df_rec.empty:
        return gastos_df, 0

    created = 0
    rows = []
    year, month = int(yyyymm.split("-")[0]), int(yyyymm.split("-")[1])

    for _, r in df_rec.iterrows():
        rec_id = int(r.get("rec_id") or r.get("id") or 0)
        if int(r.get("active", 1)) != 1:
            continue
        if _recurring_was_applied(username, rec_id, yyyymm):
            continue

        dom = int(r.get("day_of_month") or r.get("Dia") or 5)
        dom = max(1, min(28, dom))
        dt = datetime(year, month, dom)

        cat_val = r.get("categoria") or r.get("Categoria") or "Outros"
        desc_val = r.get("descricao") or r.get("Descrição") or r.get("descricao") or ""
        tipo_val = r.get("tipo") or r.get("Tipo") or "Saída"
        val_val = float(r.get("valor") or r.get("Valor") or 0.0)
        pay_val = r.get("pagamento") or r.get("Pagamento") or "Pix"

        rows.append({
            "Data": dt,
            "Categoria": str(cat_val),
            "Descricao": str(desc_val),
            "Tipo": "Entrada" if str(tipo_val).lower() == "entrada" else "Saída",
            "Valor": float(val_val),
            "Pagamento": str(pay_val),
        })
        _mark_recurring_applied(username, rec_id, yyyymm)
        created += 1

    if created > 0:
        gastos_df = _append_rows(gastos_df, rows)

    return gastos_df, created


# =========================================================
# CSV helpers + rules
# =========================================================
def _smart_load_csv(uploaded_file) -> pd.DataFrame | None:
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file)
        if df is not None and len(df.columns) > 1:
            return df
    except Exception:
        pass
    uploaded_file.seek(0)
    try:
        df = pd.read_csv(uploaded_file, sep=";")
        if df is not None and len(df.columns) > 1:
            return df
    except Exception:
        pass
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file, sep=";", encoding="latin1")
    except Exception:
        return None


def _pick_pattern(text: str) -> str:
    s = str(text or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    parts = [p.strip() for p in s.split() if len(p.strip()) >= 4]
    return parts[0] if parts else (s[:12].strip() or "rule")


def _apply_rules(rules_df: pd.DataFrame, desc: str) -> str:
    d = (desc or "").lower()
    if rules_df is None or rules_df.empty:
        return "Outros"

    # active primeiro
    try:
        df = rules_df.copy()
        if "active" in df.columns:
            df = df.sort_values("active", ascending=False)
    except Exception:
        df = rules_df

    for _, r in df.iterrows():
        if int(r.get("active", 1)) == 0:
            continue
        p = str(r.get("pattern", "")).lower().strip()
        if p and p in d:
            return str(r.get("categoria", "Outros"))
    return "Outros"


# =========================================================
# UI: Dashboard / Extrato / Envelopes / Recorrências / Import
# =========================================================
def _render_dashboard(username: str):
    st.subheader("📊 Dashboard do mês")

    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()
    mes = _month_key(today)

    dfm = df_g[df_g["Data"].dt.strftime("%Y-%m") == mes].copy()

    total_ent = float(dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum())
    total_sai = float(dfm[dfm["Tipo"] == "Saída"]["Valor"].sum())
    saldo = total_ent - total_sai

    # previsão simples: gasto médio/dia * dias do mês
    dias_passados = max(1, today.day)
    gasto_por_dia = (total_sai / dias_passados) if dias_passados > 0 else 0.0
    # dias do mês aproximado (robusto sem libs)
    try:
        next_month = datetime(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
        last_day = (next_month - pd.Timedelta(days=1)).day
    except Exception:
        last_day = 30
    previsao_gasto = gasto_por_dia * last_day
    previsao_saldo = total_ent - previsao_gasto

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receitas (mês)", fmt_money_brl(total_ent, 2))
    c2.metric("Despesas (mês)", fmt_money_brl(total_sai, 2))
    c3.metric("Saldo (mês)", fmt_money_brl(saldo, 2))
    c4.metric("Saldo previsto", fmt_money_brl(previsao_saldo, 2))

    st.caption("Previsão baseada na média diária de despesas até hoje (simples, mas ajuda MUITO).")

    st.markdown("### 🔥 Top gastos por categoria")
    if dfm.empty:
        st.info("Sem lançamentos neste mês ainda.")
        return

    df_cat = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
    df_cat = df_cat.sort_values("Valor", ascending=False)

    left, right = st.columns([1.2, 1])
    with left:
        st.dataframe(
            df_cat.head(12),
            use_container_width=True,
            hide_index=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )
    with right:
        if px is not None and not df_cat.empty:
            fig = px.pie(df_cat.head(10), values="Valor", names="Categoria", hole=0.55)
            fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Plotly não disponível.")

    st.markdown("---")
    st.markdown("### 🚀 Ações rápidas")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("➕ Nova transação", use_container_width=True):
            st.session_state["controle_open_new"] = True
            st.rerun()
    with a2:
        if st.button("📦 Ajustar metas (Envelopes)", use_container_width=True):
            st.session_state["controle_tab"] = "📦 Envelopes"
            st.rerun()
    with a3:
        if st.button("🔁 Gerar recorrências do mês", use_container_width=True):
            df_new, created = _apply_recurring_for_month(username, df_g, mes)
            st.session_state["gastos_df"] = df_new
            save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
            st.toast(f"Recorrências criadas: {created}", icon="🔁")
            st.rerun()


def _render_extrato(username: str):
    st.subheader("📒 Extrato")

    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()

    # meses disponíveis
    meses_disp = sorted(list(set(df_g["Data"].dt.strftime("%Y-%m")))) if not df_g.empty else []
    if not meses_disp:
        meses_disp = [_month_key(today)]

    mes_atual = _month_key(today)
    idx_mes = meses_disp.index(mes_atual) if mes_atual in meses_disp else (len(meses_disp) - 1)

    col_sel, col_btn = st.columns([2, 1])
    with col_sel:
        mes = st.selectbox("📅 Mês", meses_disp, index=idx_mes, key="controle_mes")
    with col_btn:
        if st.button("🔁 Gerar recorrências do mês", use_container_width=True, key="controle_btn_rec"):
            df_new, created = _apply_recurring_for_month(username, df_g, mes)
            st.session_state["gastos_df"] = df_new
            save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
            st.toast(f"Recorrências criadas: {created}", icon="🔁")
            st.rerun()

    # filtros
    dfm = df_g[df_g["Data"].dt.strftime("%Y-%m") == mes].copy()

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1, 1.2])
    with f1:
        q = st.text_input("🔎 Buscar (descrição)", key="controle_busca")
    with f2:
        cats = ["Todas"] + sorted(dfm["Categoria"].dropna().unique().tolist())
        cat = st.selectbox("Categoria", cats, key="controle_cat")
    with f3:
        tipo = st.selectbox("Tipo", ["Todos", "Saída", "Entrada"], key="controle_tipo")
    with f4:
        pag = st.selectbox("Pagamento", ["Todos"] + sorted(dfm["Pagamento"].dropna().unique().tolist()), key="controle_pag")

    if q:
        dfm = dfm[dfm["Descricao"].astype(str).str.lower().str.contains(q.lower(), na=False)]
    if cat != "Todas":
        dfm = dfm[dfm["Categoria"] == cat]
    if tipo != "Todos":
        dfm = dfm[dfm["Tipo"] == tipo]
    if pag != "Todos":
        dfm = dfm[dfm["Pagamento"] == pag]

    total_ent = float(dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum())
    total_sai = float(dfm[dfm["Tipo"] == "Saída"]["Valor"].sum())
    saldo = total_ent - total_sai

    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas", fmt_money_brl(total_ent, 2))
    k2.metric("Despesas", fmt_money_brl(total_sai, 2))
    k3.metric("Saldo", fmt_money_brl(saldo, 2))

    # nova transação (expander + abrir via dashboard)
    open_new = bool(st.session_state.get("controle_open_new", False))
    with st.expander("➕ Nova transação", expanded=open_new):
        if open_new:
            st.session_state["controle_open_new"] = False

        with st.form("form_gastos", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d_data = c1.date_input("Data", value=today.date())
            default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Saúde", "Educação", "Outros"]
            existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
            all_cats = sorted(list(set(default_cats + existing_cats)))
            all_cats.append("➕ Nova (Digitar abaixo)")

            d_cat_select = c2.selectbox("Categoria", all_cats, key="controle_new_cat_sel")
            d_cat_input = c2.text_input("Nova categoria", placeholder="Ex: Pet", key="controle_new_cat_in")
            d_desc = c3.text_input("Descrição", placeholder="Ex: Supermercado", key="controle_new_desc")
            d_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"], key="controle_new_tipo")

            c5, c6 = st.columns(2)
            d_val = c5.number_input("Valor (R$)", min_value=0.0, step=10.0, key="controle_new_val")
            d_pag = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"], key="controle_new_pag")

            if st.form_submit_button("Salvar", type="primary", use_container_width=True):
                final_cat = d_cat_input if (d_cat_select == "➕ Nova (Digitar abaixo)" and d_cat_input) else d_cat_select
                if final_cat == "➕ Nova (Digitar abaixo)":
                    final_cat = "Outros"

                new_row = {
                    "Data": pd.to_datetime(d_data),
                    "Categoria": final_cat,
                    "Descricao": d_desc,
                    "Tipo": "Entrada" if d_tipo == "Entrada" else "Saída",
                    "Valor": float(d_val),
                    "Pagamento": d_pag,
                }
                df_g2 = _append_rows(df_g, [new_row])
                st.session_state["gastos_df"] = df_g2
                save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
                st.toast("Transação salva!", icon="✅")
                st.rerun()

    st.markdown("### 📈 Visual do mês")
    if px is not None and not dfm.empty and total_sai > 0:
        tab1, tab2 = st.tabs(["Por categoria", "Evolução diária"])
        with tab1:
            df_pie = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
            fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.55)
            fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            df_day = dfm[dfm["Tipo"] == "Saída"].groupby(dfm["Data"].dt.date)["Valor"].sum().reset_index()
            df_day.columns = ["Data", "Valor"]
            fig = px.bar(df_day, x="Data", y="Valor")
            fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes para gráficos.")

    st.markdown("---")
    st.markdown("### 🧾 Extrato detalhado (editar)")
    df_edit = st.data_editor(
        dfm.sort_values("Data", ascending=False),
        num_rows="dynamic",
        use_container_width=True,
        height=380,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
        },
        key="editor_gastos",
    )

    cA, cB = st.columns([1, 1])
    with cA:
        if st.button("💾 Salvar alterações", type="primary", use_container_width=True):
            # mistura: substitui só o mês editado e mantém outros meses intactos
            df_other = df_g[df_g["Data"].dt.strftime("%Y-%m") != mes].copy()
            df_new = _ensure_gastos_columns(pd.concat([df_other, df_edit], ignore_index=True))
            st.session_state["gastos_df"] = df_new
            save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
            st.toast("Extrato atualizado!", icon="✅")
            st.rerun()
    with cB:
        st.download_button(
            "⬇️ Backup Local (CSV)",
            df_g.to_csv(index=False).encode("utf-8"),
            "meus_gastos.csv",
            "text/csv",
            use_container_width=True,
        )

    if st.button("🧹 Limpar Gastos (zera tudo)", use_container_width=True):
        st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
        st.session_state["gastos_mode"] = False
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.rerun()


def _render_envelopes(username: str):
    st.subheader("📦 Envelopes (metas por categoria)")
    st.caption("Defina metas mensais e acompanhe se está dentro, no limite ou estourado.")

    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    budgets = _get_budgets(username)

    month_key = _month_key(datetime.now())
    spent = _spent_by_category_month(df_g, month_key)

    all_cats = sorted(set(list(spent.keys()) + list(budgets.keys()) + [
        "Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Saúde", "Educação", "Outros"
    ]))

    # editor de meta
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        cat = st.selectbox("Categoria", all_cats, key="env_cat")
    with c2:
        lim = st.number_input("Meta mensal (R$)", min_value=0.0, step=50.0, value=float(budgets.get(cat, 0.0)), key="env_lim")
    with c3:
        if st.button("Salvar meta", type="primary", use_container_width=True, key="env_save"):
            _set_budget(username, cat, lim)
            st.toast("Meta salva!", icon="✅")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Progresso das metas")

    # cards por categoria com barra
    estourou = []
    atencao = []
    ok = []

    for cat in all_cats:
        lim = float(budgets.get(cat, 0.0))
        sp = float(spent.get(cat, 0.0))
        if lim <= 0:
            continue

        pct = (sp / lim) if lim > 0 else 0.0
        if pct >= 1:
            estourou.append(cat)
        elif pct >= 0.8:
            atencao.append(cat)
        else:
            ok.append(cat)

        with st.container(border=True):
            a, b, c = st.columns([1.2, 1, 1])
            a.markdown(f"**{cat}**")
            b.write(f"Meta: {fmt_money_brl(lim, 2)}")
            c.write(f"Gasto: {fmt_money_brl(sp, 2)}")
            st.progress(min(1.0, pct))
            st.caption(f"Uso: {pct*100:.1f}%")

    if estourou:
        st.warning("⚠️ Estourou: " + ", ".join(estourou[:8]))
    elif atencao:
        st.info("🟡 Atenção: " + ", ".join(atencao[:8]))
    else:
        st.success("✅ Tudo dentro das metas (ou sem metas definidas ainda).")


def _render_recorrencias(username: str):
    st.subheader("🔁 Recorrências (contas fixas)")
    st.caption("Crie contas fixas e gere 1 lançamento por mês (sem duplicar).")

    with st.expander("➕ Nova recorrência", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        cat = c1.text_input("Categoria", value="Moradia", key="rec_cat")
        desc = c2.text_input("Descrição", placeholder="Ex: Aluguel / Internet", key="rec_desc")
        kind = c3.selectbox("Tipo", ["Saída", "Entrada"], key="rec_tipo")
        dom = c4.number_input("Dia do mês (1-28)", min_value=1, max_value=28, value=5, key="rec_dom")

        c5, c6 = st.columns(2)
        val = c5.number_input("Valor", min_value=0.0, step=10.0, value=100.0, key="rec_val")
        pay = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"], key="rec_pay")

        if st.button("Salvar recorrência", type="primary", use_container_width=True, key="rec_save"):
            _add_recurring(username, cat, desc, kind, float(val), pay, int(dom), active=1)
            st.toast("Recorrência criada!", icon="🔁")
            st.rerun()

    rec_list = _list_recurring(username)
    df = pd.DataFrame(rec_list)

    if df.empty:
        st.info("Sem recorrências ainda.")
        return

    st.markdown("### 📋 Suas recorrências")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### ⚙️ Ativar / Desativar")
    cA, cB, cC = st.columns([1, 1, 2])
    with cA:
        rid = st.number_input("rec_id", min_value=1, step=1, value=int(df.iloc[0].get("rec_id", 1)), key="rec_toggle_id")
    with cB:
        act = st.selectbox("Ação", ["Ativar", "Desativar"], key="rec_toggle_action")
    with cC:
        if st.button("Aplicar", use_container_width=True, key="rec_toggle_apply"):
            _set_recurring_active(username, int(rid), 1 if act == "Ativar" else 0)
            st.toast("Atualizado!", icon="✅")
            st.rerun()


def _render_import_csv(username: str):
    st.subheader("📥 Importar CSV + Regras (aprende)")
    st.caption("Importe fatura/extrato e o app sugere categorias e cria regras automaticamente.")

    rules_df = pd.DataFrame(_list_rules(username))
    if rules_df.empty:
        st.info("Sem regras ainda. Depois do primeiro import, ele aprende.")
    else:
        st.dataframe(rules_df, use_container_width=True, hide_index=True)

    up = st.file_uploader("Subir CSV do cartão/extrato", type=["csv"], key="uploader_csv_cartao")
    if not up:
        return

    df_raw = _smart_load_csv(up)
    if df_raw is None or df_raw.empty:
        st.error("CSV inválido ou vazio.")
        return

    cols = {str(c).lower(): c for c in df_raw.columns}
    col_desc = cols.get("descricao") or cols.get("description") or cols.get("histórico") or cols.get("historico") or cols.get("desc")
    col_val = cols.get("valor") or cols.get("amount") or cols.get("total") or cols.get("value")
    col_date = cols.get("data") or cols.get("date")

    if not col_desc or not col_val:
        st.error("Não achei colunas parecidas com 'descricao' e 'valor' no seu CSV.")
        st.write("Colunas encontradas:", list(df_raw.columns))
        return

    df = df_raw.copy()
    df["Descricao"] = df[col_desc].astype(str)
    df["Valor"] = df[col_val]
    df["Data"] = pd.to_datetime(df[col_date], errors="coerce", dayfirst=True) if col_date else pd.Timestamp(datetime.now().date())

    # normaliza valor
    if df["Valor"].dtype == object:
        df["Valor"] = (
            df["Valor"].astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    # regras
    rules_df2 = rules_df.copy()
    if "active" not in rules_df2.columns:
        rules_df2["active"] = 1

    # sugere categoria
    df["Categoria_sugerida"] = df["Descricao"].apply(lambda x: _apply_rules(rules_df2, x))
    df["Categoria_final"] = df["Categoria_sugerida"]

    st.markdown("### ✅ Conferir e ajustar categorias")
    edited = st.data_editor(
        df[["Data", "Descricao", "Valor", "Categoria_sugerida", "Categoria_final"]],
        use_container_width=True,
        height=380,
        num_rows="fixed",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
        key="editor_import",
    )

    tipo = st.selectbox("Tipo dos lançamentos importados", ["Saída", "Entrada"], key="import_tipo")
    pagamento = st.selectbox("Pagamento (padrão)", ["Crédito", "Pix", "Débito", "Dinheiro"], key="import_pag")

    if st.button("✅ Importar para o Controle", type="primary", use_container_width=True, key="import_apply"):
        df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

        rows = []
        for _, r in edited.iterrows():
            desc = str(r.get("Descricao", "")).strip()
            val = float(r.get("Valor", 0.0) or 0.0)
            dtv = r.get("Data", None)
            cat_final = str(r.get("Categoria_final", "Outros") or "Outros").strip()
            if not desc or val == 0:
                continue
            rows.append({
                "Data": pd.to_datetime(dtv, errors="coerce") if dtv is not None else pd.to_datetime(datetime.now().date()),
                "Categoria": cat_final if cat_final else "Outros",
                "Descricao": desc,
                "Tipo": "Entrada" if tipo == "Entrada" else "Saída",
                "Valor": abs(val),
                "Pagamento": pagamento,
            })

            # aprende regra: pega um padrão do texto e salva
            pat = _pick_pattern(desc)
            if pat:
                _add_rule(username, pat, cat_final, active=1)

        df_new = _append_rows(df_g, rows)
        st.session_state["gastos_df"] = _ensure_gastos_columns(df_new)
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast(f"Importado: {len(rows)} lançamentos", icon="✅")
        st.rerun()


# =========================================================
# Page entry
# =========================================================
def render_controle():
    username = st.session_state.get("username", "") or "guest"

    st.markdown("# 💸 Controle")
    st.caption("Gastos, orçamento (envelopes), recorrências e importação de faturas.")

    # tab persistente (fica onde você estava)
    if "controle_tab" not in st.session_state:
        st.session_state["controle_tab"] = "📊 Dashboard"

    tabs = ["📊 Dashboard", "📒 Extrato", "📦 Envelopes", "🔁 Recorrências", "📥 Importar CSV"]
    tab = st.radio("Seções", tabs, horizontal=True, index=tabs.index(st.session_state["controle_tab"]), key="controle_tab_radio")
    st.session_state["controle_tab"] = tab

    if tab == "📊 Dashboard":
        _render_dashboard(username)
    elif tab == "📒 Extrato":
        _render_extrato(username)
    elif tab == "📦 Envelopes":
        _render_envelopes(username)
    elif tab == "🔁 Recorrências":
        _render_recorrencias(username)
    else:
        _render_import_csv(username)
