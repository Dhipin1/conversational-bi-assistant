import sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.session_state import init_session
from auth.auth_service import authenticate, logout

init_session()
st.title("Login")

if st.session_state.user:
    st.success(
        f"Logged in: {st.session_state.user['username']} ({st.session_state.user['role']})"
    )
    if st.button("Logout"):
        logout(st.session_state)
        st.rerun()
else:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        u = authenticate(username, password)
        if not u:
            st.error("Invalid credentials")
        else:
            st.session_state.user = u
            st.rerun()

# Public demo hint (do NOT show admin credentials publicly)
st.caption("Demo login: demo / demo123")
