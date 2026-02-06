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


# =========================
# Helpers
# =========================

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
        elif c in ["descricao", "descrição", "description", "desc"]:
            rename_map[col] = "Descricao"
        elif c in ["tipo", "type"]:
            rename_map[col] = "Tipo"
        elif c in ["valor", "value", "amount"]:
            rename_map[col] = "Valor"
        elif c in ["pagamento", "payment"]:
            rename_map[col] = "Pagamento"
    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    for col in GASTOS_COLS:
        if col not in df.columns:
            df[col] = ""

    df = df[GASTOS_COLS]

    # robusto: datas BR e bagunçadas
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    # double-check: se ainda não virou datetime, força string -> datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"].astype(str), errors="coerce", dayfirst=True)

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

    # tipos válidos
    df["Tipo"] = df["Tipo"].astype(str).str.strip()
    df.loc[~df["Tipo"].isin(["Entrada", "Saída"]), "Tipo"] = "Saída"

    df["Categoria"] = df["Categoria"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Categoria"] == "", "Categoria"] = "Outros"

    df["Descricao"] = df["Descricao"].astype(str).replace("nan", "").str.strip()
    df["Pagamento"] = df["Pagamento"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Pagamento"] == "", "Pagamento"] = "Pix"

    return df


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _to_money(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


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


# =========================
# Recurring log (anti-duplicação)
# =========================
def _recurring_was_applied(username: str, rec_id: int, yyyymm: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
              CREATE TABLE IF NOT EXISTS recurring_log
              (
                  username
                  TEXT,
                  recurring_id
                  INTEGER,
                  yyyymm
                  TEXT,
                  PRIMARY
                  KEY
              (
                  username,
                  recurring_id,
                  yyyymm
              )
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
              CREATE TABLE IF NOT EXISTS recurring_log
              (
                  username
                  TEXT,
                  recurring_id
                  INTEGER,
                  yyyymm
                  TEXT,
                  PRIMARY
                  KEY
              (
                  username,
                  recurring_id,
                  yyyymm
              )
                  )
              """)
    c.execute("INSERT OR IGNORE INTO recurring_log(username, recurring_id, yyyymm) VALUES(?,?,?)",
              (username, int(rec_id), yyyymm))
    conn.commit()
    conn.close()


def _apply_recurring_for_month(username: str, gastos_df: pd.DataFrame, yyyymm: str) -> tuple[pd.DataFrame, int]:
    """
    Gera 1 lançamento por recorrência ativa, por mês, sem duplicar.
    """
    # Converter lista pura para DataFrame antes de iterar
    rec_list = list_recurring_db(DB_FILE, username)
    df_rec = pd.DataFrame(rec_list)

    if df_rec.empty:
        return gastos_df, 0

    created = 0
    rows = []
    year, month = int(yyyymm.split("-")[0]), int(yyyymm.split("-")[1])

    for _, r in df_rec.iterrows():
        # Tenta pegar 'rec_id', se não tiver usa 'id'
        rec_id = int(r.get("rec_id") or r.get("id") or 0)

        if int(r.get("active", 1)) != 1:
            continue

        if _recurring_was_applied(username, rec_id, yyyymm):
            continue

        dom = int(r.get("day_of_month") or r.get("Dia") or 5)
        dom = max(1, min(28, dom))
        dt = datetime(year, month, dom)

        # Ajuste de chaves para compatibilidade
        cat_val = r.get("categoria") or r.get("Categoria") or "Outros"
        desc_val = r.get("descricao") or r.get("Descrição") or ""
        tipo_val = r.get("tipo") or r.get("Tipo") or "Saída"
        val_val = float(r.get("valor") or r.get("Valor") or 0.0)
        pay_val = r.get("pagamento") or r.get("Pagamento") or "Pix"

        rows.append({
            "Data": dt,
            "Categoria": str(cat_val),
            "Descricao": str(desc_val),
            "Tipo": str(tipo_val),
            "Valor": val_val,
            "Pagamento": str(pay_val),
        })
        _mark_recurring_applied(username, rec_id, yyyymm)
        created += 1

    if created > 0:
        gastos_df = _append_rows(gastos_df, rows)

    return gastos_df, created


# =========================
# Rules (import CSV)
# =========================
def _pick_pattern(text: str) -> str:
    s = str(text or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    parts = [p.strip() for p in s.split() if len(p.strip()) >= 4]
    return parts[0] if parts else (s[:12].strip() or "rule")


def _apply_rules(rules_df: pd.DataFrame, desc: str) -> str:
    d = (desc or "").lower()
    if rules_df is None or rules_df.empty:
        return "Outros"
    for _, r in rules_df.sort_values("active", ascending=False).iterrows():
        # Nota: assumindo prioridade implícita ou só active
        if int(r.get("active", 1)) == 0:
            continue

        p = str(r.get("pattern", "")).lower().strip()
        if p and p in d:
            return str(r.get("categoria", "Outros"))
    return "Outros"


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


# =========================
# UI Sections
# =========================
def _render_extrato(username: str):
    st.subheader("📒 Extrato (mês)")

    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

    # Garante Data (datetime) para evitar erro .dt
    df_g["Data"] = pd.to_datetime(df_g["Data"], errors="coerce")

    today = datetime.now()
    meses_disp = sorted(list(set(df_g["Data"].dt.strftime("%Y-%m")))) if not df_g.empty else []
    if not meses_disp:
        meses_disp = [today.strftime("%Y-%m")]

    mes_atual_str = today.strftime("%Y-%m")
    idx_mes = meses_disp.index(mes_atual_str) if mes_atual_str in meses_disp else (len(meses_disp) - 1)

    col_sel, col_btn = st.columns([2, 1])
    with col_sel:
        mes = st.selectbox("📅 Mês", meses_disp, index=idx_mes)
    with col_btn:
        if st.button("🔁 Gerar Recorrências do mês", use_container_width=True):
            df_new, created = _apply_recurring_for_month(username, df_g, mes)
            st.session_state["gastos_df"] = df_new
            save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()),
                              st.session_state["gastos_df"])
            st.toast(f"Recorrências criadas: {created}", icon="🔁")
            st.rerun()

    mask = df_g["Data"].dt.strftime("%Y-%m") == mes
    dfm = df_g[mask].copy()

    total_ent = float(dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum())
    total_sai = float(dfm[dfm["Tipo"] == "Saída"]["Valor"].sum())
    saldo = total_ent - total_sai

    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas", fmt_money_brl(total_ent, 2))
    k2.metric("Despesas", fmt_money_brl(total_sai, 2))
    k3.metric("Saldo", fmt_money_brl(saldo, 2))

    st.markdown("### 📊 Análise visual")
    if px is not None and not dfm.empty and total_sai > 0:
        tab1, tab2 = st.tabs(["Por categoria", "Evolução diária"])
        with tab1:
            df_pie = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index()
            fig = px.pie(df_pie, values="Valor", names="Categoria", hole=0.5,
                         color_discrete_sequence=px.colors.sequential.Magma)
            fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            df_day = dfm[dfm["Tipo"] == "Saída"].groupby(dfm["Data"].dt.date)["Valor"].sum().reset_index()
            df_day.columns = ["Data", "Valor"]
            fig = px.bar(df_day, x="Data", y="Valor", color="Valor", color_continuous_scale="Reds")
            fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes para gráficos.")

    st.markdown("---")

    # Nova transação manual
    with st.expander("➕ Nova transação", expanded=False):
        with st.form("form_gastos", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d_data = c1.date_input("Data", value=today.date())
            default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Saúde",
                            "Outros"]
            existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
            all_cats = sorted(list(set(default_cats + existing_cats)))
            all_cats.append("➕ Nova (Digitar abaixo)")

            d_cat_select = c2.selectbox("Categoria", all_cats)
            d_cat_input = c2.text_input("Nova categoria", placeholder="Ex: Pet")
            d_desc = c3.text_input("Descrição", placeholder="Ex: Supermercado")
            d_tipo = c4.selectbox("Tipo", ["Saída", "Entrada"])

            c5, c6 = st.columns(2)
            d_val = c5.number_input("Valor (R$)", min_value=0.0, step=10.0)
            d_pag = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])

            if st.form_submit_button("Salvar", type="primary", use_container_width=True):
                final_cat = d_cat_input if (d_cat_select == "➕ Nova (Digitar abaixo)" and d_cat_input) else d_cat_select
                if final_cat == "➕ Nova (Digitar abaixo)":
                    final_cat = "Outros"

                new_row = {
                    "Data": pd.to_datetime(d_data),
                    "Categoria": final_cat,
                    "Descricao": d_desc,
                    "Tipo": d_tipo,
                    "Valor": float(d_val),
                    "Pagamento": d_pag,
                }
                df_g2 = _append_rows(df_g, [new_row])
                st.session_state["gastos_df"] = df_g2
                save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()),
                                  st.session_state["gastos_df"])
                st.toast("Transação salva!", icon="✅")
                st.rerun()

    st.markdown("### 🧾 Extrato detalhado")
    df_edit = st.data_editor(
        df_g,
        num_rows="dynamic",
        use_container_width=True,
        height=360,
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
        },
        key="editor_gastos",
    )
    if st.button("💾 Salvar alterações do extrato", type="primary", use_container_width=True):
        st.session_state["gastos_df"] = _ensure_gastos_columns(df_edit)
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast("Extrato atualizado!", icon="✅")
        st.rerun()

    st.download_button(
        "⬇️ Backup Local (CSV)",
        df_g.to_csv(index=False).encode("utf-8"),
        "meus_gastos.csv",
        "text/csv",
        use_container_width=True,
    )

    if st.button("🧹 Limpar Gastos", use_container_width=True):
        st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
        st.session_state["gastos_mode"] = False
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.rerun()


def _render_envelopes(username: str):
    st.subheader("📦 Envelopes (orçamento por categoria)")

    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    budgets = get_budgets_db(DB_FILE, username)

    month_key = _month_key(datetime.now())
    spent = _spent_by_category_month(df_g, month_key)

    all_cats = sorted(set(list(spent.keys()) + list(budgets.keys()) + [
        "Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Saúde", "Educação", "Outros"
    ]))

    c1, c2 = st.columns([1, 2])
    with c1:
        cat = st.selectbox("Categoria", all_cats)
        lim = st.number_input("Meta mensal (R$)", min_value=0.0, step=50.0, value=float(budgets.get(cat, 0.0)))
        if st.button("Salvar meta", type="primary", use_container_width=True):
            set_budget_db(DB_FILE, username, cat, lim)
            st.toast("Meta salva!", icon="✅")
            st.rerun()

    rows = []
    for cat in all_cats:
        lim = float(budgets.get(cat, 0.0))
        sp = float(spent.get(cat, 0.0))
        pct = (sp / lim * 100) if lim > 0 else 0.0
        rows.append({"Categoria": cat, "Meta": lim, "Gasto": sp, "Uso %": round(pct, 1)})

    t = pd.DataFrame(rows).sort_values("Uso %", ascending=False)
    st.dataframe(
        t,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Meta": st.column_config.NumberColumn("Meta", format="R$ %.2f"),
            "Gasto": st.column_config.NumberColumn("Gasto", format="R$ %.2f"),
            "Uso %": st.column_config.NumberColumn("Uso %", format="%.1f %%"),
        },
    )

    estouradas = t[(t["Meta"] > 0) & (t["Uso %"] >= 100)]
    if not estouradas.empty:
        st.warning("⚠️ Estourou: " + ", ".join(estouradas["Categoria"].head(6).tolist()))
    else:
        st.success("✅ Tudo dentro das metas (ou sem meta definida ainda).")


def _render_recorrencias(username: str):
    st.subheader("🔁 Recorrências (contas fixas)")
    st.caption("Você gera 1 lançamento por mês sem duplicar (botão no Extrato).")

    with st.expander("➕ Nova recorrência", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        cat = c1.text_input("Categoria", value="Moradia")
        desc = c2.text_input("Descrição", placeholder="Ex: Aluguel / Internet")
        kind = c3.selectbox("Tipo", ["Saída", "Entrada"])
        dom = c4.number_input("Dia do mês (1-28)", min_value=1, max_value=28, value=5)

        c5, c6 = st.columns(2)
        val = c5.number_input("Valor", min_value=0.0, step=10.0, value=100.0)
        pay = c6.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])

        if st.button("Salvar recorrência", type="primary", use_container_width=True):
            add_recurring_db(DB_FILE, username, cat, desc, kind, val, pay, dom, active=1)
            st.toast("Recorrência criada!", icon="🔁")
            st.rerun()

    # === CORREÇÃO: Converter Lista -> DataFrame antes de checar empty ===
    rec_list = list_recurring_db(DB_FILE, username)
    df = pd.DataFrame(rec_list)
    # ===================================================================

    if df.empty:
        st.info("Sem recorrências ainda.")
        return

    st.dataframe(df.drop(columns=["id", "rec_id"], errors="ignore"), use_container_width=True, hide_index=True)

    st.markdown("#### ⚙️ Ativar / Desativar")
    cA, cB, cC = st.columns([1, 1, 2])
    with cA:
        if "rec_id" in df.columns:
            rid = st.number_input("ID", min_value=1, step=1, value=int(df.iloc[0]["rec_id"]))
        else:
            rid = 0
    with cB:
        act = st.selectbox("Ação", ["Ativar", "Desativar"])
    with cC:
        if st.button("Aplicar", use_container_width=True):
            set_recurring_active_db(DB_FILE, username, rid, 1 if act == "Ativar" else 0)
            st.toast("Atualizado!", icon="✅")
            st.rerun()


def _render_import_csv(username: str):
    st.subheader("📥 Importar CSV + Regras (aprende)")
    st.caption("Você importa a fatura e o app sugere categoria. Ao confirmar, ele salva regras automaticamente.")

    # === CORREÇÃO: Converter Lista -> DataFrame ===
    rules_data = list_rules_db(DB_FILE, username)
    rules_df = pd.DataFrame(rules_data)
    # ==============================================

    if rules_df.empty:
        st.info("Sem regras ainda. Depois do primeiro import, ele aprende.")
    else:
        st.dataframe(rules_df, use_container_width=True, hide_index=True)

    up = st.file_uploader("Subir CSV do cartão", type=["csv"], key="uploader_csv_cartao")
    if not up:
        return

    df_raw = _smart_load_csv(up)
    if df_raw is None or df_raw.empty:
        st.error("CSV inválido ou vazio.")
        return

    cols = {c.lower(): c for c in df_raw.columns}
    col_desc = cols.get("descricao") or cols.get("description") or cols.get("histórico") or cols.get("historico")
    col_val = cols.get("valor") or cols.get("amount") or cols.get("total") or cols.get("value")
    col_date = cols.get("data") or cols.get("date")

    if not col_desc or not col_val:
        st.error("Não achei colunas 'descricao' e 'valor'. Renomeie no CSV ou exporte em outro formato.")
        st.write("Colunas encontradas:", list(df_raw.columns))
        return

    df2 = pd.DataFrame()
    df2["Descricao"] = df_raw[col_desc].astype(str)

    df2["Valor"] = pd.to_numeric(
        df_raw[col_val].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0.0)

    if col_date:
        df2["Data"] = pd.to_datetime(df_raw[col_date], errors="coerce")
    else:
        df2["Data"] = pd.to_datetime(datetime.now().date())

    df2["Categoria"] = df2["Descricao"].apply(lambda x: _apply_rules(rules_df, x))
    df2["Tipo"] = "Saída"
    df2["Pagamento"] = "Crédito"

    st.markdown("### ✅ Revise e confirme")
    edited = st.data_editor(
        df2[["Data", "Descricao", "Valor", "Categoria", "Tipo", "Pagamento"]],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Categoria": st.column_config.SelectboxColumn("Categoria", options=[
                "Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Saúde", "Educação", "Outros"
            ]),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Saída", "Entrada"]),
            "Pagamento": st.column_config.SelectboxColumn("Pagamento",
                                                          options=["Crédito", "Débito", "Pix", "Dinheiro"]),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        }
    )

    if st.button("Importar + Aprender regras", type="primary", use_container_width=True):
        df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

        rows = []
        for _, r in edited.iterrows():
            rows.append({
                "Data": pd.to_datetime(r["Data"]),
                "Categoria": str(r["Categoria"]),
                "Descricao": str(r["Descricao"]),
                "Tipo": str(r["Tipo"]),
                "Valor": float(r["Valor"]),
                "Pagamento": str(r["Pagamento"]),
            })

            # aprende regra
            pat = _pick_pattern(r["Descricao"])
            add_rule_db(DB_FILE, username, pat, str(r["Categoria"]), priority=50)

        df_new = _append_rows(df_g, rows)
        st.session_state["gastos_df"] = df_new
        st.session_state["gastos_mode"] = True
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])

        st.toast(f"Importado {len(rows)} lançamentos e salvei regras ✅", icon="✅")
        st.rerun()


def render_controle():
    st.markdown("## 💸 Controle de Gastos")

    username = st.session_state["username"]

    tabs = st.tabs(["📒 Extrato", "📦 Envelopes", "🔁 Recorrências", "📥 Import CSV"])
    with tabs[0]:
        _render_extrato(username)
    with tabs[1]:
        _render_envelopes(username)
    with tabs[2]:
        _render_recorrencias(username)
    with tabs[3]:
        _render_import_csv(username)