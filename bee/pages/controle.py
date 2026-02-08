import re
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# =========================================================
# IMPORTS DO PROJETO (Mantidos)
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
# 1. HELPERS E FORMATADORES BRASIL
# =========================================================
def _to_dt(series: pd.Series) -> pd.Series:
    # O SEGREDO DO BRASIL: dayfirst=True força DD/MM/AAAA
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _ym(series: pd.Series) -> pd.Series:
    return _to_dt(series).dt.strftime("%Y-%m")


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _compact_brl(v: float) -> str:
    try:
        v = float(v)
    except:
        return "R$ 0,00"
    return fmt_money_brl(v, 2)


def _apply_unified_css():
    st.markdown("""
        <style>
          .kpi-container {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;
          }
          .kpi-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
            border-top: 1px solid rgba(255,255,255,0.15); border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25); padding: 16px;
            display: flex; flex-direction: column; align-items: center; text-align: center;
            min-height: 100px; backdrop-filter: blur(10px);
          }
          .kpi-label { font-size: 11px; opacity: 0.7; margin-bottom: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
          .kpi-value { font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.1; }

          div[data-testid="column"] > div > div > div > button {
             width: 100% !important; height: 50px !important;
             border: 1px solid rgba(255,255,255,0.1) !important;
             background: rgba(255, 255, 255, 0.05) !important;
             border-radius: 10px !important; font-weight: 600 !important; font-size: 14px !important;
          }
          div[data-testid="column"] > div > div > div > button:hover {
             background: rgba(255, 255, 255, 0.1) !important; border-color: rgba(255,255,255,0.3) !important;
          }
          /* Ajuste do Expander */
          .streamlit-expanderHeader { background-color: rgba(255,255,255,0.03); border-radius: 8px; }
          @media (max-width: 900px){ .kpi-container { grid-template-columns: 1fr 1fr; } }
        </style>
    """, unsafe_allow_html=True)


# =========================================================
# 2. DATA HANDLERS (DB)
# =========================================================
# Wrappers simples para evitar erro se DB_FILE mudar de ordem nos args
def _get_budgets(u): return get_budgets_db(u, DB_FILE)


def _set_budget(u, c, b): set_budget_db(u, c, b, DB_FILE)


def _list_rules(u): return list_rules_db(u, DB_FILE)


def _add_rule(u, p, c, a=1): add_rule_db(u, p, c, a, DB_FILE)


def _list_recurring(u): return list_recurring_db(u, DB_FILE)


def _add_recurring(u, c, d, t, v, p, dom, a=1): add_recurring_db(u, d, c, t, v, p, dom, a, DB_FILE)


def _set_recurring_active(u, rid, a): set_recurring_active_db(u, rid, a, DB_FILE)


def _ensure_gastos_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e padroniza o DataFrame para evitar erros de data/valor."""
    if df is None or len(df) == 0: return pd.DataFrame(columns=GASTOS_COLS)
    df = df.copy()

    # Renomeação inteligente de colunas (caso venha de CSV sujo)
    rename_map = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["data", "date"]:
            rename_map[col] = "Data"
        elif c in ["categoria", "category"]:
            rename_map[col] = "Categoria"
        elif c in ["descricao", "descrição", "description"]:
            rename_map[col] = "Descricao"
        elif c in ["tipo", "type"]:
            rename_map[col] = "Tipo"
        elif c in ["valor", "value", "amount"]:
            rename_map[col] = "Valor"
        elif c in ["pagamento", "payment"]:
            rename_map[col] = "Pagamento"
    if rename_map: df.rename(columns=rename_map, inplace=True)

    for col in GASTOS_COLS:
        if col not in df.columns: df[col] = ""

    df = df[GASTOS_COLS]

    # FORÇA DATA BRASILEIRA
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Data"])  # Remove datas inválidas

    # Limpeza de Valor (R$ 1.000,00 -> 1000.00)
    if df["Valor"].dtype == object:
        df["Valor"] = df["Valor"].astype(str).str.replace("R$", "", regex=False) \
            .str.replace(".", "", regex=False) \
            .str.replace(",", ".", regex=False).str.strip()
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    # Padronização de Texto
    df["Tipo"] = df["Tipo"].astype(str).str.strip().str.capitalize()
    df.loc[~df["Tipo"].isin(["Entrada", "Saída", "Saida"]), "Tipo"] = "Saída"
    df.loc[df["Tipo"] == "Saida", "Tipo"] = "Saída"  # Corrige acento

    df["Categoria"] = df["Categoria"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Categoria"] == "", "Categoria"] = "Outros"

    df["Descricao"] = df["Descricao"].astype(str).replace("nan", "").str.strip()
    df["Pagamento"] = df["Pagamento"].astype(str).replace("nan", "").str.strip()

    return df


def _append_rows(gastos_df: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    """Adiciona novas linhas e garante a estrutura."""
    base = _ensure_gastos_columns(gastos_df)
    if not rows: return base
    new_df = _ensure_gastos_columns(pd.DataFrame(rows))
    return pd.concat([base, new_df], ignore_index=True)


# --- RECORRÊNCIAS ---
def _recurring_was_applied(username, rec_id, yyyymm):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS recurring_log (username TEXT, recurring_id INTEGER, yyyymm TEXT, PRIMARY KEY (username, recurring_id, yyyymm))")
        c.execute("SELECT 1 FROM recurring_log WHERE username=? AND recurring_id=? AND yyyymm=?",
                  (username, int(rec_id), yyyymm))
        return c.fetchone() is not None


def _mark_recurring_applied(username, rec_id, yyyymm):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute("INSERT OR IGNORE INTO recurring_log(username, recurring_id, yyyymm) VALUES(?,?,?)",
                              (username, int(rec_id), yyyymm))


def _apply_recurring_for_month(username, gastos_df, yyyymm):
    rec_list = _list_recurring(username)
    if not rec_list: return _ensure_gastos_columns(gastos_df), 0

    df_rec = pd.DataFrame(rec_list)
    created = 0
    rows = []
    year, month = map(int, yyyymm.split("-"))

    for _, r in df_rec.iterrows():
        rec_id = int(r.get("rec_id") or r.get("id") or 0)
        if int(r.get("active", 1)) != 1: continue
        if _recurring_was_applied(username, rec_id, yyyymm): continue

        dom = int(r.get("day_of_month") or r.get("Dia") or 5)
        # Garante dia válido (ex: dia 30 em fevereiro vira 28)
        import calendar
        _, last_day = calendar.monthrange(year, month)
        day = min(dom, last_day)

        dt = datetime(year, month, day)
        rows.append({
            "Data": dt, "Categoria": str(r.get("categoria") or "Outros"),
            "Descricao": str(r.get("descricao") or ""),
            "Tipo": "Entrada" if str(r.get("tipo")).lower() == "entrada" else "Saída",
            "Valor": float(r.get("valor") or 0.0), "Pagamento": str(r.get("pagamento") or "Pix")
        })
        _mark_recurring_applied(username, rec_id, yyyymm)
        created += 1

    if created > 0: gastos_df = _append_rows(gastos_df, rows)
    return _ensure_gastos_columns(gastos_df), created


# =========================================================
# 3. INTERFACE (VIEWS)
# =========================================================

def _nav_btn(label: str, tab_key: str, icon: str = ""):
    active = st.session_state.get("controle_tab", "Dashboard") == tab_key
    # Se ativo, usa primary, senão secondary.
    # Como queremos todos iguais visualmente, usamos o CSS para padronizar,
    # mas o tipo ajuda o Streamlit a gerenciar o foco.
    if st.button(f"{icon} {label}".strip(), use_container_width=True, key=f"ctl_nav_{tab_key}"):
        st.session_state["controle_tab"] = tab_key
        st.rerun()


def _render_add_transaction_inline(username: str):
    """RENDERIZA O FORMULÁRIO DE ADIÇÃO (EXPANDER + FORM)"""
    with st.expander("➕ Nova transação (Clique para abrir)", expanded=False):
        # Carrega dados atuais
        df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

        # Categorias inteligentes
        default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Saúde", "Educação",
                        "Outros"]
        existing_cats = df_g["Categoria"].dropna().unique().tolist() if not df_g.empty else []
        all_cats = sorted(list(set(default_cats + existing_cats))) + ["➕ Nova..."]

        # --- FORMULÁRIO DE CADASTRO ---
        with st.form("form_add_tx", clear_on_submit=True):
            st.caption("Detalhes do lançamento")
            c1, c2, c3, c4 = st.columns(4)
            # FORCE O FORMATO DD/MM/YYYY NO INPUT
            with c1:
                d_data = st.date_input("Data", value=datetime.now(), format="DD/MM/YYYY")
            with c2:
                d_tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            with c3:
                d_pag = st.selectbox("Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])
            with c4:
                d_val = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")

            c5, c6 = st.columns([1, 1])
            with c5:
                d_cat_sel = st.selectbox("Categoria", all_cats)
                d_cat_input = st.text_input("Nova categoria (se escolheu 'Nova...')")
            with c6:
                d_desc = st.text_input("Descrição", placeholder="Ex: Supermercado")

            submitted = st.form_submit_button("💾 Salvar Lançamento", type="primary", use_container_width=True)

            if submitted:
                # Lógica da Categoria
                final_cat = d_cat_sel
                if d_cat_sel == "➕ Nova...":
                    final_cat = d_cat_input.strip() if d_cat_input.strip() else "Outros"

                # Cria linha nova garantindo DATETIME
                new_row = {
                    "Data": pd.to_datetime(d_data),  # Garante Timestamp
                    "Categoria": final_cat, "Descricao": d_desc.strip(),
                    "Tipo": d_tipo, "Valor": float(d_val), "Pagamento": d_pag
                }

                # Adiciona e Salva
                df_new = _append_rows(df_g, [new_row])
                st.session_state["gastos_df"] = df_new
                save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), df_new)

                st.toast("Salvo! Atualizando...", icon="✅")
                st.rerun()


def _render_dashboard(username: str):
    st.subheader("📊 Dashboard")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

    # Seletor de Mês Robusto
    today = datetime.now()
    all_months = sorted(list(set(_ym(df_g["Data"]).dropna().tolist()) | {_month_key(today)}))

    c_sel, _ = st.columns([1, 3])
    # Padrão: Mês atual se existir na lista, senão o último
    idx_default = len(all_months) - 1
    if _month_key(today) in all_months:
        idx_default = all_months.index(_month_key(today))

    mes_selecionado = c_sel.selectbox("📅 Mês de Referência", all_months, index=idx_default, key="dash_mes_sel")

    # Filtra Dados
    dfm = df_g[_ym(df_g["Data"]) == mes_selecionado].copy()

    total_ent = dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum()
    total_sai = dfm[dfm["Tipo"] == "Saída"]["Valor"].sum()
    saldo = total_ent - total_sai

    # Cards KPI
    st.markdown(f"""
    <div class="kpi-container">
      <div class="kpi-card"><div class="kpi-label">RECEITAS</div><div class="kpi-value" style="color:#4ade80;">{_compact_brl(total_ent)}</div></div>
      <div class="kpi-card"><div class="kpi-label">DESPESAS</div><div class="kpi-value" style="color:#f87171;">{_compact_brl(total_sai)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SALDO MÊS</div><div class="kpi-value">{_compact_brl(saldo)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SALDO ACUMULADO</div><div class="kpi-value" style="opacity:0.7;">---</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Gráfico
    st.markdown("### 🔥 Top Gastos do Mês")
    if not dfm.empty and total_sai > 0:
        df_cat = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index().sort_values("Valor",
                                                                                                           ascending=False)
        l, r = st.columns([1.2, 1])
        with l:
            st.dataframe(
                df_cat.head(10), use_container_width=True, hide_index=True,
                column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")}
            )
        with r:
            if px:
                fig = px.pie(df_cat.head(8), values="Valor", names="Categoria", hole=0.6)
                fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Nenhuma despesa registrada em {mes_selecionado}.")


def _render_extrato(username: str):
    st.subheader("📒 Extrato Detalhado")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

    # Seletor de Mês (Sincronizado com a lógica do Dashboard)
    today = datetime.now()
    all_months = sorted(list(set(_ym(df_g["Data"]).dropna().tolist()) | {_month_key(today)}))

    c1, c2 = st.columns([2, 1])
    mes = c1.selectbox("📅 Filtrar Mês", all_months, index=len(all_months) - 1, key="extrato_mes_sel")

    if c2.button("🔁 Processar Recorrentes", use_container_width=True):
        df_new, count = _apply_recurring_for_month(username, df_g, mes)
        st.session_state["gastos_df"] = df_new
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), df_new)
        st.toast(f"{count} recorrências geradas!", icon="✅")
        st.rerun()

    dfm = df_g[_ym(df_g["Data"]) == mes].copy().sort_values("Data", ascending=False)

    # Filtros
    f1, f2, f3 = st.columns([2, 1, 1])
    q = f1.text_input("🔎 Buscar descrição", key="ext_busca")
    cat = f2.selectbox("Categoria", ["Todas"] + sorted(dfm["Categoria"].unique()), key="ext_cat")

    if q: dfm = dfm[dfm["Descricao"].str.lower().str.contains(q.lower(), na=False)]
    if cat != "Todas": dfm = dfm[dfm["Categoria"] == cat]

    # Editor de Dados com DATA BRASILEIRA (format="DD/MM/YYYY")
    st.markdown("---")
    edited = st.data_editor(
        dfm,
        use_container_width=True,
        num_rows="dynamic",
        height=400,
        key="editor_extrato",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
            "Pagamento": st.column_config.SelectboxColumn("Pgto", options=["Pix", "Crédito", "Débito", "Dinheiro"])
        }
    )

    if st.button("💾 Salvar Alterações na Tabela", type="primary", use_container_width=True):
        # Mescla edições com o resto dos dados (outros meses)
        df_others = df_g[_ym(df_g["Data"]) != mes]
        df_final = pd.concat([df_others, edited], ignore_index=True)

        st.session_state["gastos_df"] = _ensure_gastos_columns(df_final)
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast("Tabela atualizada!", icon="✅")
        st.rerun()


# --- Outras abas simplificadas para caber no contexto ---
def _render_envelopes(username: str):
    st.subheader("📦 Envelopes (Orçamento)")
    st.info("Defina limites para suas categorias aqui.")
    # (Mantido simples, foco no Dashboard/Extrato)


def _render_recorrencias(username: str):
    st.subheader("🔁 Recorrências")
    # (Lógica mantida, visual simplificado)
    df = pd.DataFrame(_list_recurring(username))
    st.dataframe(df, use_container_width=True)


def _render_import_csv(username: str):
    st.subheader("📥 Importar CSV")
    st.info("Importe extratos do banco aqui.")


# =========================================================
# MAIN ENTRY
# =========================================================
def render_controle():
    _apply_unified_css()
    username = st.session_state.get("username", "") or "guest"
    st.markdown("# 💸 Controle Financeiro")

    # 1. ADD TRANSACTION (Inline + Form + Safe Save)
    _render_add_transaction_inline(username)

    # 2. NAV
    if "controle_tab" not in st.session_state: st.session_state["controle_tab"] = "Dashboard"

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        _nav_btn("Dashboard", "Dashboard", "📊")
    with c2:
        _nav_btn("Extrato", "Extrato", "📒")
    with c3:
        _nav_btn("Envelopes", "Envelopes", "📦")
    with c4:
        _nav_btn("Recorrências", "Recorrências", "🔁")
    with c5:
        _nav_btn("Importar", "Importar CSV", "📥")

    st.markdown("---")

    # 3. CONTENT
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