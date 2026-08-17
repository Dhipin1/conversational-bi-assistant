import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

db_url = os.getenv("DB_URL")
if not db_url:
    raise ValueError(f"DB_URL not set in {ROOT/'.env'}")

engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})

with engine.connect() as con:
    tables = con.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).fetchall()
    print("DB_URL:", db_url)
    print("Tables:", [t[0] for t in tables])