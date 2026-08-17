import streamlit as st


def init_session():
    defaults = {
        "user": None,
        "chat_messages": [],
        "pending_question": None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value