import streamlit as st
from ..market_data import get_google_news_items
from ..formatters import human_time_ago

def render_noticias():
    st.markdown("## 📰 Notícias")
    q = st.text_input("Buscar", value="investimentos brasil", label_visibility="collapsed")
    items = get_google_news_items(q, limit=12)
    if items:
        for n in items:
            ago = human_time_ago(n["published_dt"])
            st.markdown(
                f"""
<a href="{n['link']}" target="_blank" class="news-card-link">
  <div class="news-card-box">
    <div class="nc-title">{n['title']}</div>
    <div class="nc-meta">
      <span class="nc-badge">{n['source']}</span>
      <span>• {ago}</span>
    </div>
  </div>
</a>
""",
                unsafe_allow_html=True,
            )
    else:
        st.info("Sem notícias agora.")
