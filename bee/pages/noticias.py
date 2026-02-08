import streamlit as st
from ..market_data import get_google_news_items
from ..formatters import human_time_ago


def _apply_news_css():
    st.markdown("""
        <style>
          /* Container da barra de busca para ficar mais elegante */
          .search-container {
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.02);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
          }

          /* Card de Notícia Premium */
          .news-card {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 20px;
            height: 100%; /* Para cards terem mesma altura na linha */
            min-height: 160px;
            transition: all 0.3s ease;
            text-decoration: none !important;
            color: inherit !important;
            backdrop-filter: blur(5px);
          }

          .news-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 215, 0, 0.3); /* Borda dourada suave no hover */
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
          }

          .nc-source-badge {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #ffd700;
            background: rgba(255, 215, 0, 0.1);
            padding: 4px 8px;
            border-radius: 6px;
            width: fit-content;
            margin-bottom: 10px;
            font-weight: 700;
          }

          .nc-title {
            font-size: 16px;
            font-weight: 600;
            color: #f0f0f0;
            line-height: 1.4;
            margin-bottom: 15px;
            /* Limita a 3 linhas */
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
          }

          .nc-footer {
            font-size: 12px;
            color: #888;
            margin-top: auto; /* Empurra para o fundo */
            display: flex;
            align-items: center;
            gap: 5px;
          }
        </style>
    """, unsafe_allow_html=True)


def render_noticias():
    _apply_news_css()

    st.markdown("## 📰 Central de Notícias")
    st.caption("Fique por dentro do que move o mercado.")

    # Área de busca estilizada
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            q = st.text_input("🔍 Pesquisar Tópico", value="Mercado Financeiro Brasil", label_visibility="collapsed",
                              placeholder="Ex: Dividendos, Petrobras, Selic...")
        with c2:
            # Botão de atualizar forçado (trick visual)
            st.markdown("<div style='height: 2px'></div>", unsafe_allow_html=True)  # Espaçamento
            if st.button("Buscar", use_container_width=True, type="primary"):
                pass  # Apenas recarrega a página com o novo termo

    # Busca as notícias
    with st.spinner(f"Buscando as últimas sobre: {q}..."):
        items = get_google_news_items(q, limit=18)  # Aumentei um pouco para preencher o grid

    if items:
        # Layout de Grid (3 colunas)
        cols = st.columns(3)

        for i, n in enumerate(items):
            ago = human_time_ago(n["published_dt"])
            col = cols[i % 3]  # Distribui entre as 3 colunas

            with col:
                st.markdown(
                    f"""
                    <a href="{n['link']}" target="_blank" class="news-card">
                      <div class="nc-source-badge">{n['source']}</div>
                      <div class="nc-title">{n['title']}</div>
                      <div class="nc-footer">
                        <span>🕒 {ago}</span>
                      </div>
                    </a>
                    <div style="margin-bottom: 15px;"></div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info(f"Nenhuma notícia encontrada para '{q}'. Tente outro termo.")

        # Sugestões se não achar nada
        st.markdown("Experimente buscar por:")
        s1, s2, s3, s4 = st.columns(4)
        if s1.button("Fundos Imobiliários", use_container_width=True): pass
        if s2.button("Criptomoedas", use_container_width=True): pass
        if s3.button("Ações Dividendos", use_container_width=True): pass
        if s4.button("Taxa Selic", use_container_width=True): pass