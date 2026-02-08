import re
import sqlite3
from datetime import datetime, timedelta
import difflib

import pandas as pd
import streamlit as st

# =========================================================
# IMPORTS DO PROJETO
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
# 1. HELPERS E FORMATADORES
# =========================================================
def _to_dt(series: pd.Series) -> pd.Series:
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


def _get_sorted_categories(cats_list):
    """Ordena A-Z, coloca 'Outros' no fim e adiciona 'Nova'."""
    unique = set(cats_list)
    if "Outros" in unique: unique.remove("Outros")
    # Se "Nova..." ou similares existirem, remove pra limpar
    clean_list = [c for c in unique if "Nova" not in c]

    sorted_list = sorted(clean_list)
    return sorted_list + ["Outros", "➕ Nova Categoria..."]


def _apply_unified_css():
    st.markdown("""
        <style>
          /* KPI CARDS */
          .kpi-container {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px;
          }
          .kpi-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 12px; padding: 20px;
            display: flex; flex-direction: column; align-items: flex-start; justify-content: center;
            backdrop-filter: blur(10px); transition: transform 0.2s;
          }
          .kpi-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.1); }

          .kpi-label { font-size: 10px; opacity: 0.5; margin-bottom: 5px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
          .kpi-value { font-size: 26px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }

          /* BOTÕES NAV */
          div[data-testid="column"] > div > div > div > button {
             width: 100% !important; height: 45px !important; border: none !important;
             background: rgba(255, 255, 255, 0.05) !important; border-radius: 8px !important; 
             font-weight: 600 !important; font-size: 13px !important; color: #aaa !important;
          }
          div[data-testid="column"] > div > div > div > button:hover {
             background: rgba(255, 255, 255, 0.1) !important; color: #fff !important;
          }

          /* Barra de Progresso Dourada */
          .stProgress > div > div > div > div { background-color: #FFD700; }

          .streamlit-expanderHeader { background-color: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
          @media (max-width: 900px){ .kpi-container { grid-template-columns: 1fr 1fr; } }
        </style>
    """, unsafe_allow_html=True)


# =========================================================
# 2. DATA HANDLERS E LOGICA
# =========================================================
def _get_budgets(u): return get_budgets_db(u, DB_FILE)


def _set_budget(u, c, b): set_budget_db(u, c, b, DB_FILE)


def _list_rules(u): return list_rules_db(u, DB_FILE)


def _add_rule(u, p, c, a=1): add_rule_db(u, p, c, a, DB_FILE)


def _list_recurring(u): return list_recurring_db(u, DB_FILE)


def _add_recurring(u, c, d, t, v, p, dom, a=1): add_recurring_db(u, d, c, t, v, p, dom, a, DB_FILE)


def _set_recurring_active(u, rid, a): set_recurring_active_db(u, rid, a, DB_FILE)


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

    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Data"])

    if df["Valor"].dtype == object:
        df["Valor"] = df["Valor"].astype(str).str.replace(r"[R$ ]", "", regex=True).str.replace(".", "",
                                                                                                regex=False).str.replace(
            ",", ".", regex=False)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    df["Tipo"] = df["Tipo"].astype(str).str.strip().str.capitalize()
    df.loc[~df["Tipo"].isin(["Entrada", "Saída"]), "Tipo"] = "Saída"

    df["Categoria"] = df["Categoria"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Categoria"] == "", "Categoria"] = "Outros"

    df["Descricao"] = df["Descricao"].astype(str).replace("nan", "").str.strip()
    df["Pagamento"] = df["Pagamento"].astype(str).replace("nan", "").str.strip()
    df.loc[df["Pagamento"] == "", "Pagamento"] = "Outros"

    return df


def _append_rows(gastos_df: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    base = _ensure_gastos_columns(gastos_df)
    if not rows: return base
    new_df = _ensure_gastos_columns(pd.DataFrame(rows))
    return pd.concat([base, new_df], ignore_index=True)


# --- FUNÇÃO RESTAURADA ---
def _spent_by_category_month(gastos_df: pd.DataFrame, month_key: str) -> dict:
    df = _ensure_gastos_columns(gastos_df)
    if df.empty: return {}
    # Filtra mês e apenas saídas
    dfm = df[(_ym(df["Data"]) == month_key) & (df["Tipo"] == "Saída")]
    if dfm.empty: return {}
    return dfm.groupby("Categoria")["Valor"].sum().to_dict()


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
        import calendar
        _, last_day = calendar.monthrange(year, month)
        day = min(int(r.get("day_of_month") or 5), last_day)
        rows.append({
            "Data": datetime(year, month, day),
            "Categoria": str(r.get("categoria") or "Outros"), "Descricao": str(r.get("descricao") or ""),
            "Tipo": "Entrada" if str(r.get("tipo")).lower() == "entrada" else "Saída",
            "Valor": float(r.get("valor") or 0.0), "Pagamento": str(r.get("pagamento") or "Pix")
        })
        _mark_recurring_applied(username, rec_id, yyyymm)
        created += 1
    if created > 0: gastos_df = _append_rows(gastos_df, rows)
    return _ensure_gastos_columns(gastos_df), created


# --- IMPORTAÇÃO ---
def _guess_column_mapping(df_columns):
    mapping = {col: None for col in GASTOS_COLS}
    keywords = {
        "Data": ["data", "date", "dia", "dt"],
        "Categoria": ["categoria", "cat", "grupo"],
        "Descricao": ["descrição", "desc", "nome", "histórico", "loja"],
        "Valor": ["valor", "preço", "total", "amount"],
        "Tipo": ["tipo", "entrada/saída", "movimento"],
        "Pagamento": ["pagamento", "forma"]
    }
    cols_lower = [c.lower().strip() for c in df_columns]
    for target_col, keys in keywords.items():
        match = None
        for k in keys:
            if k in cols_lower:
                match = df_columns[cols_lower.index(k)]
                break
        if not match:
            matches = difflib.get_close_matches(target_col.lower(), cols_lower, n=1, cutoff=0.6)
            if matches: match = df_columns[cols_lower.index(matches[0])]
        mapping[target_col] = match
    return mapping


# =========================================================
# 3. INTERFACE (VIEWS)
# =========================================================

def _nav_btn(label: str, tab_key: str, icon: str = ""):
    if st.button(f"{icon} {label}".strip(), use_container_width=True, key=f"ctl_nav_{tab_key}"):
        st.session_state["controle_tab"] = tab_key
        st.rerun()


def _render_add_transaction_inline(username: str):
    with st.expander("➕ Nova Transação", expanded=False):
        df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))

        default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Investimento", "Salário", "Saúde", "Educação"]
        existing_cats = df_g["Categoria"].dropna().unique().tolist()

        # USA O ORDENADOR INTELIGENTE
        all_cats = _get_sorted_categories(default_cats + existing_cats)

        with st.form("form_add_tx", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                d_data = st.date_input("Data", value=datetime.now(), format="DD/MM/YYYY", label_visibility="collapsed")
            with c2:
                d_tipo = st.selectbox("Tipo", ["Saída", "Entrada"], label_visibility="collapsed")
            with c3:
                d_pag = st.selectbox("Pgto", ["Pix", "Crédito", "Débito", "Dinheiro"], label_visibility="collapsed")
            with c4:
                d_val = st.number_input("Valor", min_value=0.0, step=10.0, format="%.2f", label_visibility="collapsed")

            c5, c6 = st.columns([1, 1])
            with c5:
                d_cat_sel = st.selectbox("Categoria", all_cats, label_visibility="collapsed")
                d_cat_input = st.text_input("Nome", placeholder="Nova Categoria...", label_visibility="collapsed")
            with c6:
                d_desc = st.text_input("Descrição", placeholder="Descrição (Opcional)", label_visibility="collapsed")

            if st.form_submit_button("Salvar", type="primary", use_container_width=True):
                final_cat = d_cat_input.strip() if (
                            d_cat_sel == "➕ Nova Categoria..." and d_cat_input.strip()) else d_cat_sel
                if final_cat == "➕ Nova Categoria...": final_cat = "Outros"

                new_row = {
                    "Data": pd.to_datetime(d_data), "Categoria": final_cat,
                    "Descricao": d_desc.strip(), "Tipo": d_tipo,
                    "Valor": float(d_val), "Pagamento": d_pag
                }
                df_new = _append_rows(df_g, [new_row])
                st.session_state["gastos_df"] = df_new
                save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), df_new)
                st.toast("Salvo", icon="✅")
                st.rerun()


def _render_dashboard(username: str):
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()
    all_months = sorted(list(set(_ym(df_g["Data"]).dropna().tolist()) | {_month_key(today)}))

    c_tit, c_sel = st.columns([3, 1])
    with c_tit:
        st.subheader("Visão Geral")
    with c_sel:
        idx_def = all_months.index(_month_key(today)) if _month_key(today) in all_months else len(all_months) - 1
        mes_sel = st.selectbox("Mês", all_months, index=idx_def, key="dash_mes", label_visibility="collapsed")

    dfm = df_g[_ym(df_g["Data"]) == mes_sel].copy()

    total_ent = dfm[dfm["Tipo"] == "Entrada"]["Valor"].sum()
    total_sai = dfm[dfm["Tipo"] == "Saída"]["Valor"].sum()
    saldo = total_ent - total_sai

    st.markdown(f"""
    <div class="kpi-container">
      <div class="kpi-card"><div class="kpi-label">ENTRADAS</div><div class="kpi-value" style="color:#4ade80;">{_compact_brl(total_ent)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SAÍDAS</div><div class="kpi-value" style="color:#f87171;">{_compact_brl(total_sai)}</div></div>
      <div class="kpi-card"><div class="kpi-label">SALDO</div><div class="kpi-value">{_compact_brl(saldo)}</div></div>
      <div class="kpi-card"><div class="kpi-label">STATUS</div><div class="kpi-value" style="font-size:18px;">{'🟢 Positivo' if saldo >= 0 else '🔴 Negativo'}</div></div>
    </div>
    """, unsafe_allow_html=True)

    if not dfm.empty and total_sai > 0:
        df_cat = dfm[dfm["Tipo"] == "Saída"].groupby("Categoria")["Valor"].sum().reset_index().sort_values("Valor",
                                                                                                           ascending=False)
        l, r = st.columns([1.5, 1])
        with l:
            st.dataframe(df_cat.head(10), use_container_width=True, hide_index=True,
                         column_config={"Categoria": "Categoria",
                                        "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
        with r:
            if px:
                fig = px.pie(df_cat.head(6), values="Valor", names="Categoria", hole=0.7,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0), showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  annotations=[dict(text=mes_sel, x=0.5, y=0.5, font_size=14, showarrow=False)])
                fig.update_traces(textposition='outside', textinfo='label+percent')
                st.plotly_chart(fig, use_container_width=True)
    elif total_ent > 0:
        st.info(f"Apenas receitas em {mes_sel}.")
    else:
        st.info(f"Sem dados em {mes_sel}.")


def _render_extrato(username: str):
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    today = datetime.now()
    all_months = sorted(list(set(_ym(df_g["Data"]).dropna().tolist()) | {_month_key(today)}))

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Movimentações")
    with c2:
        mes = st.selectbox("Mês", all_months, index=len(all_months) - 1, key="ext_mes", label_visibility="collapsed")

    df_new, count = _apply_recurring_for_month(username, df_g, mes)
    if count > 0:
        st.session_state["gastos_df"] = df_new
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), df_new)
        st.toast(f"Recorrências lançadas.", icon="✅")
        st.rerun()

    dfm = df_g[_ym(df_g["Data"]) == mes].copy().sort_values("Data", ascending=False)

    f1, f2 = st.columns([2, 1])
    q = f1.text_input("Buscar", placeholder="Filtrar...", label_visibility="collapsed", key="ext_busca")
    cat = f2.selectbox("Categoria", ["Todas"] + sorted(dfm["Categoria"].unique()), label_visibility="collapsed",
                       key="ext_cat")

    if q: dfm = dfm[dfm["Descricao"].str.lower().str.contains(q.lower(), na=False)]
    if cat != "Todas": dfm = dfm[dfm["Categoria"] == cat]

    edited = st.data_editor(
        dfm, use_container_width=True, num_rows="dynamic", height=450, key="editor_extrato",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Entrada", "Saída"]),
            "Pagamento": st.column_config.SelectboxColumn("Pgto", options=["Pix", "Crédito", "Débito", "Dinheiro"])
        }
    )

    if st.button("Atualizar Tabela", type="primary", use_container_width=True):
        df_others = df_g[_ym(df_g["Data"]) != mes]
        df_final = pd.concat([df_others, edited], ignore_index=True)
        st.session_state["gastos_df"] = _ensure_gastos_columns(df_final)
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), st.session_state["gastos_df"])
        st.toast("Atualizado", icon="✅")
        st.rerun()


def _render_envelopes(username: str):
    st.subheader("Metas de Gasto")
    df_g = _ensure_gastos_columns(st.session_state.get("gastos_df", pd.DataFrame(columns=GASTOS_COLS)))
    budgets = _get_budgets(username)
    spent = _spent_by_category_month(df_g, _month_key(datetime.now()))  # Função Restaurada!

    # Categorias com ordenação correta
    default_cats = ["Moradia", "Alimentação", "Transporte", "Lazer", "Educação", "Saúde"]
    user_cats = list(spent.keys()) + list(budgets.keys())
    all_cats = _get_sorted_categories(default_cats + user_cats)

    # --- INPUT DE METAS CORRIGIDO ---
    with st.expander("Definir Meta", expanded=True):
        c1, c2 = st.columns([1.5, 1])
        with c1:
            sel_cat = st.selectbox("Categoria", all_cats, key="env_cat")
            if sel_cat == "➕ Nova Categoria...":
                new_cat_txt = st.text_input("Nome da nova meta", placeholder="Ex: Viagem")
            else:
                new_cat_txt = None

        with c2:
            current_val = float(budgets.get(sel_cat, 0.0)) if sel_cat != "➕ Nova Categoria..." else 0.0
            lim = st.number_input("Limite (R$)", value=current_val, step=50.0, key="env_lim")

        # BOTÃO FORA DAS COLUNAS (FULL WIDTH) PARA NÃO FICAR TORTO
        if st.button("Salvar Meta", type="primary", use_container_width=True):
            final_cat = new_cat_txt.strip() if (sel_cat == "➕ Nova Categoria..." and new_cat_txt) else sel_cat
            if final_cat and final_cat != "➕ Nova Categoria...":
                _set_budget(username, final_cat, lim)
                st.toast(f"Meta para {final_cat} definida!", icon="✅")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Renderiza barras
    displayed_cats = sorted(set(list(budgets.keys()) + list(spent.keys())))
    if "Outros" in displayed_cats:
        displayed_cats.remove("Outros")
        displayed_cats.append("Outros")

    if not displayed_cats:
        st.info("Nenhuma meta ou gasto registrado ainda.")

    for cat in displayed_cats:
        lim = float(budgets.get(cat, 0.0))
        sp = float(spent.get(cat, 0.0))

        if lim <= 0 and sp <= 0: continue

        pct = min(1.0, sp / lim) if lim > 0 else 1.0 if sp > 0 else 0.0

        c_tit, c_prog, c_val = st.columns([1.2, 2, 1])
        c_tit.markdown(f"**{cat}**")
        c_prog.progress(pct)

        val_str = f"{_compact_brl(sp)} / {_compact_brl(lim)}"
        if sp > lim and lim > 0:
            c_val.markdown(f":red[{val_str}] ⚠️")
        else:
            c_val.caption(val_str)


def _render_recorrencias(username: str):
    st.subheader("Recorrências")
    with st.expander("Nova Recorrência"):
        c1, c2, c3, c4 = st.columns(4)
        cat = c1.text_input("Categoria", value="Moradia")
        desc = c2.text_input("Descrição")
        kind = c3.selectbox("Tipo", ["Saída", "Entrada"])
        dom = c4.number_input("Dia", 1, 28, 5)
        val = st.number_input("Valor", 0.0, step=10.0)
        if st.button("Criar", type="primary", use_container_width=True):
            _add_recurring(username, cat, desc, kind, float(val), "Pix", int(dom))
            st.rerun()

    df = pd.DataFrame(_list_recurring(username))
    if not df.empty:
        st.dataframe(df[["descricao", "categoria", "valor", "day_of_month", "active"]], use_container_width=True,
                     hide_index=True)
        cA, cB, cC = st.columns([1, 1, 2])
        rid = cA.number_input("ID", 1, step=1)
        act = cB.selectbox("Estado", ["Ativar", "Desativar"])
        if cC.button("Alterar", use_container_width=True):
            _set_recurring_active(username, rid, 1 if act == "Ativar" else 0)
            st.rerun()


def _render_import_excel(username: str):
    st.subheader("📥 Importar Excel / CSV")
    up = st.file_uploader("Arraste o arquivo aqui", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
    if not up: return

    try:
        if up.name.endswith('.csv'):
            df_raw = pd.read_csv(up)
        else:
            df_raw = pd.read_excel(up)
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    st.markdown("##### 🔎 Verifique as colunas")
    colunas_excel = list(df_raw.columns)
    sugestao = _guess_column_mapping(colunas_excel)
    col_mapping = {}
    cols = st.columns(len(GASTOS_COLS))

    for i, nossa_col in enumerate(GASTOS_COLS):
        index_sugestao = 0
        if sugestao[nossa_col] in colunas_excel:
            index_sugestao = colunas_excel.index(sugestao[nossa_col])
        opcoes = colunas_excel + ["(Vazio/Manual)"]
        if sugestao[nossa_col] is None: index_sugestao = len(opcoes) - 1
        escolha = cols[i].selectbox(f"Para '{nossa_col}'", options=opcoes, index=index_sugestao)
        if escolha != "(Vazio/Manual)": col_mapping[nossa_col] = escolha

    if st.button("🚀 Processar e Importar", type="primary", use_container_width=True):
        rows = []
        for _, row in df_raw.iterrows():
            data_val = row[col_mapping["Data"]] if "Data" in col_mapping else datetime.now()
            valor_val = row[col_mapping["Valor"]] if "Valor" in col_mapping else 0.0
            desc_val = row[col_mapping["Descricao"]] if "Descricao" in col_mapping else "Importado"
            cat_val = row[col_mapping["Categoria"]] if "Categoria" in col_mapping else "Outros"
            tipo_val = row[col_mapping["Tipo"]] if "Tipo" in col_mapping else "Saída"

            try:
                if isinstance(valor_val, str):
                    valor_val = float(valor_val.replace("R$", "").replace(".", "").replace(",", ".").strip())
            except:
                valor_val = 0.0

            rows.append({
                "Data": pd.to_datetime(data_val, errors='coerce'),
                "Categoria": str(cat_val), "Descricao": str(desc_val), "Tipo": str(tipo_val),
                "Valor": abs(float(valor_val)), "Pagamento": "Outros"
            })

        df_new = _append_rows(st.session_state.get("gastos_df", pd.DataFrame()), rows)
        st.session_state["gastos_df"] = df_new
        save_user_data_db(username, st.session_state.get("carteira_df", pd.DataFrame()), df_new)
        st.success(f"{len(rows)} linhas importadas!")
        st.rerun()


# =========================================================
# MAIN ENTRY
# =========================================================
def render_controle():
    _apply_unified_css()
    username = st.session_state.get("username", "") or "guest"

    st.markdown("## 💸 Controle")

    _render_add_transaction_inline(username)

    if "controle_tab" not in st.session_state: st.session_state["controle_tab"] = "Dashboard"

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        _nav_btn("Dashboard", "Dashboard", "📊")
    with c2:
        _nav_btn("Extrato", "Extrato", "📒")
    with c3:
        _nav_btn("Metas", "Envelopes", "🎯")
    with c4:
        _nav_btn("Fixos", "Recorrências", "🔁")
    with c5:
        _nav_btn("Importar", "Importar", "📥")

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
        _render_import_excel(username)