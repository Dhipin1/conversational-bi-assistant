import os
import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from app.session_state import init_session

init_session()

st.title(os.getenv("APP_TITLE", "Conversational BI Assistant"))
st.write("Go to Pages → Login → Chat BI Assistant")
st.write("LLM: Ollama local (GPU if available). Dataset: Northwind SQLite.")