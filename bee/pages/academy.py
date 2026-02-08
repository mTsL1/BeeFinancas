import streamlit as st
import random

# Mantendo seus imports de lógica
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


# =========================================================
# 1. HELPERS LÓGICOS
# =========================================================
def _username() -> str:
    return st.session_state.get("username", "") or "guest"


def _tip_by_id(tid: str):
    for t in TIPS:
        if t.get("id") == tid: return t
    return None


def _question_by_id(qid: str):
    for q in QUESTIONS:
        if q.get("id") == qid: return q
    return None


def _pick_question(mode: str, username: str) -> dict:
    if not QUESTIONS: return {}
    if mode == "daily":
        qid = daily_question_id(username, [q["id"] for q in QUESTIONS])
        q = _question_by_id(qid)
        return q or QUESTIONS[0]
    return random.choice(QUESTIONS)


# =========================================================
# 2. CSS PREMIUM (ESTILO UNIFICADO)
# =========================================================
def _academy_css():
    st.markdown("""
    <style>
      /* --- HEADER & KPIs --- */
      .academy-header {
        margin-bottom: 20px;
      }
      .academy-title { font-size: 38px; font-weight: 900; background: -webkit-linear-gradient(45deg, #ffd700, #ffae00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
      .academy-sub { font-size: 16px; opacity: 0.8; margin-top: -5px; margin-bottom: 15px; }

      .kpi-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 20px;
      }
      .kpi-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01));
        border-top: 1px solid rgba(255,255,255,0.15);
        border-radius: 14px;
        padding: 12px;
        text-align: center;
        backdrop-filter: blur(10px);
      }
      .kpi-label { font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: rgba(255,255,255,0.6); font-weight: 700; }
      .kpi-value { font-size: 24px; font-weight: 800; color: #fff; }

      /* --- FLASHCARD (DICAS) --- */
      .flash-card {
        background: linear-gradient(135deg, rgba(255,215,0,0.15), rgba(0,0,0,0.4));
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      }
      .fc-topic { font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #ffd700; margin-bottom: 10px; font-weight: 700; }
      .fc-text { font-size: 20px; font-weight: 500; line-height: 1.5; color: #fff; }

      /* --- DICTIONARY CARDS --- */
      .dict-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        transition: all 0.2s;
      }
      .dict-card:hover { transform: translateX(5px); border-color: rgba(255,215,0,0.3); background: rgba(255,255,255,0.06); }
      .dict-term { font-size: 18px; font-weight: 800; color: #ffd700; display: flex; justify-content: space-between; align-items: center; }
      .dict-def { margin-top: 8px; font-size: 14px; line-height: 1.4; color: #ddd; }
      .dict-tag { font-size: 10px; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; color: #aaa; margin-left: 10px; }

      /* --- UI GERAL --- */
      button { border-radius: 10px !important; }

    </style>
    """, unsafe_allow_html=True)


# =========================================================
# 3. COMPONENTES VISUAIS
# =========================================================

def _header(username: str):
    prog = get_progress(username)
    level_name, next_xp, progress = calc_level(prog["xp"])

    st.markdown("<div class='academy-header'>", unsafe_allow_html=True)
    c_title, c_lvl = st.columns([2, 1])
    with c_title:
        st.markdown("<div class='academy-title'>🎓 Bee Academy</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='academy-sub'>Nível Atual: <b>{level_name}</b></div>", unsafe_allow_html=True)
    with c_lvl:
        if next_xp is None:
            st.progress(100)
            st.caption("Nível Máximo! 🐝👑")
        else:
            pct = int(progress * 100)
            st.progress(progress)
            st.caption(f"Próximo nível: {pct}% ({max(0, next_xp - prog['xp'])} XP restantes)")
    st.markdown("</div>", unsafe_allow_html=True)

    # KPIs Cards
    streak = prog["streak"]
    xp = prog["xp"]
    total = max(1, prog["total"])
    acc = (prog["correct"] / total) * 100

    st.markdown(f"""
    <div class="kpi-container">
      <div class="kpi-card">
        <div class="kpi-label">XP TOTAL</div>
        <div class="kpi-value">{xp}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">OFENSIVA (DIAS)</div>
        <div class="kpi-value">🔥 {streak}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">PRECISÃO</div>
        <div class="kpi-value">{acc:.0f}%</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _tab_study(username: str):
    st.subheader("📖 Flashcards")

    if "academy_tip_index" not in st.session_state:
        st.session_state["academy_tip_index"] = 0

    if not TIPS: return st.info("Sem dicas cadastradas.")

    idx = st.session_state["academy_tip_index"] % len(TIPS)
    tip = TIPS[idx]
    tip_id = tip.get("id", f"tip_{idx}")
    fav = is_favorite(username, "tip", tip_id)

    # CARD VISUAL
    st.markdown(f"""
    <div class="flash-card">
      <div class="fc-topic">{tip.get('topic', 'DICA RÁPIDA')}</div>
      <div class="fc-text">"{tip.get('text', '')}"</div>
    </div>
    """, unsafe_allow_html=True)

    # CONTROLES
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⬅ Anterior", use_container_width=True):
            st.session_state["academy_tip_index"] -= 1
            st.rerun()
    with c2:
        icon = "❤️" if fav else "🤍"
        label = "Favoritado" if fav else "Favoritar"
        if st.button(f"{icon} {label}", use_container_width=True, key=f"fav_tip_{tip_id}"):
            toggle_favorite(username, "tip", tip_id)
            st.rerun()
    with c3:
        if st.button("Próxima ➡", type="primary", use_container_width=True):
            st.session_state["academy_tip_index"] += 1
            st.rerun()

    # LISTA FAVORITOS
    with st.expander("⭐ Minhas Dicas Favoritas"):
        fav_ids = list_favorites(username, "tip")
        if not fav_ids:
            st.caption("Nenhuma dica favoritada.")
        else:
            for tid in fav_ids:
                t = _tip_by_id(tid)
                if t: st.markdown(f"• **{t.get('topic')}**: {t.get('text')}")


def _tab_quiz(username: str):
    st.subheader("🧠 Quiz Rápido")

    # Seletor de modo mais limpo
    mode = st.segmented_control("Modo de Jogo", ["Pergunta do dia", "Aleatório"], default="Pergunta do dia")
    qmode = "daily" if mode == "Pergunta do dia" else "random"

    if "academy_current_qid" not in st.session_state or st.session_state.get("academy_qmode") != qmode:
        q = _pick_question(qmode, username)
        st.session_state["academy_current_qid"] = q.get("id", "")
        st.session_state["academy_qmode"] = qmode

    q = _question_by_id(st.session_state.get("academy_current_qid", "")) or _pick_question(qmode, username)
    if not q: return st.warning("Sem perguntas.")

    qid = q.get("id", "q_unknown")
    fav = is_favorite(username, "question", qid)

    # Card da Pergunta
    with st.container(border=True):
        st.markdown(f"**Tema:** {q.get('topic', 'Geral')} | **Dificuldade:** {'⭐' * q.get('difficulty', 1)}")
        st.markdown(f"### {q.get('question', '')}")

        choice = st.radio("Sua resposta:", q.get("options", []), key=f"rad_{qid}")

        c_check, c_fav, c_next = st.columns([2, 1, 1])
        with c_check:
            if st.button("Confirmar Resposta", type="primary", use_container_width=True, key=f"btn_{qid}"):
                idx = q["options"].index(choice)
                correct = (idx == q["answer"])
                add_quiz_result(username, correct, xp_gain_correct=10)
                if correct:
                    st.balloons()
                    st.success(f"✅ Correto! {q.get('explanation', '')}")
                else:
                    st.error(f"❌ Incorreto. {q.get('explanation', '')}")
        with c_fav:
            label = "Desfavoritar" if fav else "Favoritar"
            if st.button(f"⭐ {label}", use_container_width=True, key=f"fav_q_{qid}"):
                toggle_favorite(username, "question", qid)
                st.rerun()
        with c_next:
            if st.button("Pular ➡", use_container_width=True, key=f"skip_{qid}"):
                q2 = _pick_question("random", username)
                st.session_state["academy_current_qid"] = q2.get("id", "")
                st.rerun()


def _tab_ideas():
    st.subheader("💡 Princípios do Investidor")
    principles = [
        ("Reserva de Emergência", "Antes de investir, tenha de 3 a 12 meses do seu custo de vida em liquidez diária."),
        ("Diversificação", "Não coloque todos os ovos na mesma cesta. Misture Renda Fixa, Ações, FIIs e Exterior."),
        ("Rebalanceamento",
         "Defina % alvo para cada classe. Se um ativo subir muito, venda um pouco e compre o que ficou para trás."),
        ("Aporte Constante", "O tempo no mercado ganha do 'timing' de mercado. Aporte todo mês sagradamente."),
        ("Risco vs Retorno", "Não existe retorno alto sem risco alto. Desconfie de promessas de dinheiro fácil.")
    ]

    for title, desc in principles:
        st.markdown(f"""
        <div class="dict-card">
            <div class="dict-term">{title}</div>
            <div class="dict-def">{desc}</div>
        </div>
        """, unsafe_allow_html=True)


def _tab_dictionary(username: str):
    st.subheader("📚 Glossário Financeiro")

    # Busca
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar termo", placeholder="Ex: SELIC, IPCA, ROI...", label_visibility="collapsed")
    with c2:
        topic = st.selectbox("Filtrar", ["Todos"] + topics_in_dictionary(), label_visibility="collapsed")

    results = search_dictionary(query=q, topic=None if topic == "Todos" else topic)

    if not results:
        st.info("Nenhum termo encontrado.")
        return

    for item in results[:100]:  # Limitando para não travar
        iid = item["id"]
        fav = is_favorite(username, "dict", iid)
        icon_fav = "★" if fav else "☆"

        # HTML Card customizado com botão invisível do Streamlit por cima ou lógica separada
        # Aqui vamos usar containers nativos com markdown customizado dentro para manter interatividade

        st.markdown(f"""
        <div class="dict-card">
            <div class="dict-term">
                {item['term']} <span class="dict-tag">{item.get('topic', '')}</span>
            </div>
            <div class="dict-def">{item.get('definition', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Botões de ação discretos abaixo do card
        col_act, _ = st.columns([1, 4])
        with col_act:
            label = "Remover Favorito" if fav else "Favoritar"
            if st.button(f"{icon_fav} {label}", key=f"dict_btn_{iid}", help="Salvar termo"):
                toggle_favorite(username, "dict", iid)
                st.rerun()


# =========================================================
# MAIN RENDER
# =========================================================
def render_academy():
    _academy_css()
    username = _username()

    # Header unificado
    _header(username)

    st.markdown("---")

    # Abas com ícones
    tab1, tab2, tab3, tab4 = st.tabs(["📖 Estudar", "🧠 Quiz", "💡 Princípios", "📚 Glossário"])

    with tab1: _tab_study(username)
    with tab2: _tab_quiz(username)
    with tab3: _tab_ideas()
    with tab4: _tab_dictionary(username)