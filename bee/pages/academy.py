# bee/pages/academy.py
import streamlit as st

from bee.academy.questions import QUESTIONS
from bee.academy.tips import TIPS
from bee.academy.engine import calc_level, daily_question_id
from bee.academy.progress import (
    get_progress,
    add_quiz_result,
    toggle_favorite,
    is_favorite,
    list_favorites,
)
from bee.academy.dictionary import DICTIONARY, search_dictionary, topics_in_dictionary


def _username() -> str:
    return st.session_state.get("username", "") or "guest"


def _tip_by_id(tid: str):
    for t in TIPS:
        if t.get("id") == tid:
            return t
    return None


def _question_by_id(qid: str):
    for q in QUESTIONS:
        if q.get("id") == qid:
            return q
    return None


def _pick_question(mode: str, username: str) -> dict:
    if not QUESTIONS:
        return {}
    if mode == "daily":
        qid = daily_question_id(username, [q["id"] for q in QUESTIONS])
        q = _question_by_id(qid)
        return q or QUESTIONS[0]
    import random
    return random.choice(QUESTIONS)


def _academy_css():
    st.markdown("""
    <style>
      /* --- Correções de layout pra não sobrepor botões --- */
      .academy-wrap { margin-top: 4px; }
      .academy-title { font-size: 42px; font-weight: 900; line-height: 1.05; }
      .academy-sub { opacity: 0.85; margin-top: 6px; }
      .academy-level { margin-top: 10px; font-weight: 800; }

      .academy-card {
        border-radius: 18px;
        padding: 18px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(0,0,0,0.22);
        backdrop-filter: blur(6px);
        margin-bottom: 12px;
      }
      .academy-card .topic {
        font-size: 12px;
        opacity: 0.85;
        font-weight: 900;
        letter-spacing: .06em;
        text-transform: uppercase;
      }
      .academy-card .h {
        font-size: 22px;
        font-weight: 900;
        margin-top: 6px;
      }
      .academy-card .t {
        margin-top: 10px;
        font-size: 16px;
        line-height: 1.35;
      }

      /* Tabs */
      div[data-baseweb="tab-list"] { gap: 10px; flex-wrap: wrap; }
      button[data-baseweb="tab"] {
        padding: 8px 14px !important;
        border-radius: 999px !important;
      }

      /* Botões Streamlit: força altura e evita sobreposição */
      .stButton { width: 100%; }
      .stButton > button {
        width: 100%;
        min-height: 44px !important;
        padding: 10px 14px !important;
        border-radius: 14px !important;
        white-space: normal !important;
        line-height: 1.15 !important;
        position: static !important;   /* mata qualquer position estranho */
        margin: 0 !important;
      }

      /* Colunas com espaço */
      div[data-testid="column"] { padding-top: 4px; padding-bottom: 4px; }

      /* Alguns temas mexem no footer/containers; aqui garantimos fluxo normal */
      section.main > div { padding-bottom: 30px; }

      /* Dicionário */
      .dict-term { font-size: 18px; font-weight: 900; }
      .dict-tag { font-size: 12px; opacity: 0.8; font-weight: 800; }
      .dict-def { margin-top: 8px; line-height: 1.35; }
      .dict-why { margin-top: 10px; opacity: 0.95; }
      .dict-formula { margin-top: 10px; font-family: monospace; opacity: 0.9; }
    </style>
    """, unsafe_allow_html=True)


def _header(username: str):
    prog = get_progress(username)
    level_name, next_xp, progress = calc_level(prog["xp"])

    left, m1, m2, m3 = st.columns([1.6, 1, 1, 1], vertical_alignment="center")
    with left:
        st.markdown("<div class='academy-wrap'>", unsafe_allow_html=True)
        st.markdown("<div class='academy-title'>🎓 Bee Academy</div>", unsafe_allow_html=True)
        st.markdown("<div class='academy-sub'>Estudo rápido, prático e gamificado — 5 a 10 min por dia.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with m1:
        st.metric("XP", prog["xp"])
    with m2:
        st.metric("🔥 Streak", prog["streak"])
    with m3:
        total = max(1, prog["total"])
        acc = (prog["correct"] / total) * 100
        st.metric("✅ Acerto", f"{acc:.0f}%")

    st.markdown(f"<div class='academy-level'>Nível: {level_name}</div>", unsafe_allow_html=True)
    if next_xp is None:
        st.progress(1.0)
        st.caption("Nível máximo 🐝👑")
    else:
        st.progress(progress)
        st.caption(f"Próximo nível em **{max(0, next_xp - prog['xp'])} XP**")


def _tab_study(username: str):
    st.subheader("📖 Estudar (Cards)")

    if "academy_tip_index" not in st.session_state:
        st.session_state["academy_tip_index"] = 0

    if not TIPS:
        st.info("Sem dicas cadastradas ainda.")
        return

    idx = st.session_state["academy_tip_index"] % len(TIPS)
    tip = TIPS[idx]
    tip_id = tip.get("id", f"tip_{idx}")

    st.markdown(
        f"""
        <div class="academy-card">
          <div class="topic">{tip.get('topic','')}</div>
          <div class="h">Dica Bee</div>
          <div class="t">{tip.get('text','')}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    fav = is_favorite(username, "tip", tip_id)

    with st.container():
        c1, c2, c3 = st.columns([1, 1, 1], gap="small")
        with c1:
            if st.button("✅ Entendi", use_container_width=True, key=f"academy_tip_ok_{tip_id}"):
                st.session_state["academy_tip_index"] += 1
                st.rerun()
        with c2:
            label = "⭐ Favoritar" if not fav else "★ Favoritado"
            if st.button(label, use_container_width=True, key=f"academy_tip_fav_{tip_id}"):
                toggle_favorite(username, "tip", tip_id)
                st.rerun()
        with c3:
            if st.button("➡ Próxima", use_container_width=True, key=f"academy_tip_next_{tip_id}"):
                st.session_state["academy_tip_index"] += 1
                st.rerun()

    st.divider()
    st.markdown("### ⭐ Favoritos (Dicas)")
    fav_ids = list_favorites(username, "tip")
    if not fav_ids:
        st.caption("Você ainda não favoritou nenhuma dica.")
    else:
        for tid in fav_ids[:50]:
            t = _tip_by_id(tid)
            if t:
                st.write(f"• **{t.get('topic','')}** — {t.get('text','')}")


def _tab_quiz(username: str):
    st.subheader("🧠 Quiz")

    mode = st.radio(
        "Modo",
        ["Pergunta do dia", "Aleatório"],
        horizontal=True,
        key="academy_quiz_mode_radio"
    )
    qmode = "daily" if mode == "Pergunta do dia" else "random"

    if "academy_current_qid" not in st.session_state or st.session_state.get("academy_qmode") != qmode:
        q = _pick_question(qmode, username)
        st.session_state["academy_current_qid"] = q.get("id", "")
        st.session_state["academy_qmode"] = qmode

    q = _question_by_id(st.session_state.get("academy_current_qid", "")) or _pick_question(qmode, username)
    if not q:
        st.warning("Sem perguntas cadastradas.")
        return

    qid = q.get("id", "q_unknown")

    st.markdown(f"**Tópico:** `{q.get('topic','')}` &nbsp;&nbsp; | &nbsp;&nbsp; **Dificuldade:** {q.get('difficulty',1)}/3")
    st.markdown(f"### {q.get('question','')}")

    choice = st.radio(
        "Escolha:",
        q.get("options", []),
        key=f"academy_choice_radio_{qid}"
    )

    fav = is_favorite(username, "question", qid)

    with st.container():
        colA, colB, colC = st.columns([1.2, 1, 1], gap="small")

        with colA:
            if st.button("Responder", type="primary", use_container_width=True, key=f"academy_answer_{qid}"):
                idx = q["options"].index(choice)
                correct = (idx == q["answer"])
                add_quiz_result(username, correct, xp_gain_correct=10)

                if correct:
                    st.success("✅ Correto! +10 XP")
                else:
                    st.error("❌ Errado! (sem XP)")
                st.info(q.get("explanation", ""))

        with colB:
            label = "⭐ Favoritar" if not fav else "★ Favoritado"
            if st.button(label, use_container_width=True, key=f"academy_q_fav_{qid}"):
                toggle_favorite(username, "question", qid)
                st.rerun()

        with colC:
            if st.button("Nova pergunta", use_container_width=True, key=f"academy_new_q_{qid}"):
                q2 = _pick_question(qmode, username)
                st.session_state["academy_current_qid"] = q2.get("id", "")
                st.rerun()

    st.divider()
    st.markdown("### ⭐ Favoritos (Perguntas)")
    fav_qids = list_favorites(username, "question")
    if not fav_qids:
        st.caption("Nenhuma pergunta favoritada ainda.")
    else:
        for qid2 in fav_qids[:50]:
            qq = _question_by_id(qid2)
            if qq:
                st.write(f"• **{qq.get('topic','')}** — {qq.get('question','')}")


def _tab_ideas():
    st.subheader("💡 Ideias (Prático)")
    st.write("• Reserva de emergência primeiro (liquidez + segurança).")
    st.write("• Defina alocação alvo (ex.: 60% RF / 40% RV).")
    st.write("• Crie regras: aportar todo mês e rebalancear 1x por trimestre.")
    st.write("• Diversifique, mas sem virar bagunça.")
    st.write("• Imposto, risco, taxa e liquidez: olhe SEMPRE.")


def _tab_dictionary(username: str):
    st.subheader("📚 Dicionário (Abreviações e indicadores)")
    st.caption("Digite um termo (ex: P/L, P/VP, ROE, RSI) ou navegue por temas.")

    q = st.text_input("Buscar termo", key="dict_search")
    topics = ["Todos"] + topics_in_dictionary()

    col1, col2 = st.columns([1, 1])
    with col1:
        topic = st.selectbox("Tema", topics, key="dict_topic")
    with col2:
        only_fav = st.toggle("⭐ Só favoritos", value=False, key="dict_only_fav")

    results = search_dictionary(query=q, topic=None if topic == "Todos" else topic)

    # filtro favoritos
    if only_fav:
        fav_ids = set(list_favorites(username, "dict"))
        results = [d for d in results if d["id"] in fav_ids]

    if not results:
        st.info("Nada encontrado. Tenta outro termo (ex: 'pl', 'roe', 'rsi').")
        return

    st.markdown(f"**Resultados:** {len(results)}")

    for item in results[:200]:
        term = item["term"]
        iid = item["id"]
        fav = is_favorite(username, "dict", iid)

        with st.container(border=True):
            top = st.columns([1.2, 1])
            with top[0]:
                st.markdown(f"<div class='dict-term'>{term}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dict-tag'>{item.get('topic','')}</div>", unsafe_allow_html=True)
            with top[1]:
                label = "⭐ Favoritar" if not fav else "★ Favoritado"
                if st.button(label, use_container_width=True, key=f"dict_fav_{iid}"):
                    toggle_favorite(username, "dict", iid)
                    st.rerun()

            st.markdown(f"<div class='dict-def'><b>O que é:</b> {item.get('definition','')}</div>", unsafe_allow_html=True)

            if item.get("why_it_matters"):
                st.markdown(f"<div class='dict-why'><b>Por que importa:</b> {item['why_it_matters']}</div>", unsafe_allow_html=True)

            if item.get("how_to_use"):
                st.markdown(f"<div class='dict-why'><b>Como usar:</b> {item['how_to_use']}</div>", unsafe_allow_html=True)

            if item.get("formula"):
                st.markdown(f"<div class='dict-formula'><b>Fórmula:</b> {item['formula']}</div>", unsafe_allow_html=True)

            if item.get("notes"):
                st.caption(item["notes"])


def render_academy():
    _academy_css()
    username = _username()
    _header(username)

    tab1, tab2, tab3, tab4 = st.tabs(["📖 Estudar", "🧠 Quiz", "💡 Ideias", "📚 Dicionário"])
    with tab1:
        _tab_study(username)
    with tab2:
        _tab_quiz(username)
    with tab3:
        _tab_ideas()
    with tab4:
        _tab_dictionary(username)
