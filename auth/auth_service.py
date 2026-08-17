from auth.users_store import USERS

def authenticate(username: str, password: str):
    u = USERS.get(username)
    if not u or u["password"] != password:
        return None
    return {"username": username, "role": u["role"]}

def logout(st_session_state):
    st_session_state.user = None