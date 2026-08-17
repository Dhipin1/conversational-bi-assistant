import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from langchain_community.utilities import SQLDatabase

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

# Fix for LangChain + SQLite + SQLAlchemy materialized view inspection
def _sqlite_get_mat_views(self, connection, schema=None, **kw):
    return []

SQLiteDialect.get_materialized_view_names = _sqlite_get_mat_views


def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL is not set in .env")

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)


def get_sqldb():
    engine = get_engine()
    return SQLDatabase(
        engine=engine,
        sample_rows_in_table_info=3,
        view_support=False,
    )