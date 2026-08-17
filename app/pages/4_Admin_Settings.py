import os
import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from core.db_factory import get_engine

st.title("Admin Settings")
st.code(f"DB_URL={os.getenv('DB_URL')}\nOLLAMA_MODEL={os.getenv('OLLAMA_MODEL')}")

engine = get_engine()
with engine.connect() as con:
    tables = con.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).fetchall()
st.write("Tables:", [t[0] for t in tables])