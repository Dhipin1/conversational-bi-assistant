import os

def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v else default

USERS = {
    "admin": {
        "password": _env("ADMIN_PASSWORD", "CHANGE_ME"),
        "role": "admin",
    },
    "demo": {
        "password": _env("DEMO_PASSWORD", "demo123"),
        "role": "analyst",
    },
}