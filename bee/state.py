import streamlit as st
import pandas as pd
from .config import CARTEIRA_COLS, GASTOS_COLS

def init_session_state():
    defaults = {
        "user_logged_in": False,
        "username": "",
        "user_name_display": "",
        "wallet_mode": False,
        "gastos_mode": False,
        "page": "🏠 Home",
        "patrimonio_meta": 100000.0,
        "gasto_meta": 3000.0,
        "bee_light": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "carteira_df" not in st.session_state:
        st.session_state["carteira_df"] = pd.DataFrame(columns=CARTEIRA_COLS)

    if "gastos_df" not in st.session_state:
        st.session_state["gastos_df"] = pd.DataFrame(columns=GASTOS_COLS)
