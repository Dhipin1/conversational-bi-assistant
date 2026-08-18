import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# Load .env only for local development (and don't override deployed env vars)
env_path = ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)

from app.session_state import init_session  # noqa: E402

init_session()

st.title(os.getenv("APP_TITLE", "Conversational BI Assistant (Advanced)"))
st.write("Go to Pages → Login → Chat BI Assistant")

provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

def llm_label(p: str) -> str:
    if p == "groq":
        return f"Groq (**{os.getenv('GROQ_MODEL', 'not set')}**)"
    if p == "openai":
        return f"OpenAI (**{os.getenv('OPENAI_MODEL', 'not set')}**)"
    if p == "ollama":
        model = os.getenv("OLLAMA_MODEL", "not set")
        base = os.getenv("OLLAMA_BASE_URL", "")
        base_part = f" @ {base}" if base else ""
        return f"Ollama (**{model}**){base_part}"
    return f"Unknown provider (**{p}**)"

st.write(f"LLM: {llm_label(provider)}")
st.write("Dataset: **Northwind (SQLite)**")

# Optional (safe) hint: show DB path if you want
db_url = os.getenv("DB_URL", "")
if db_url:
    st.caption(f"DB_URL: `{db_url}`")