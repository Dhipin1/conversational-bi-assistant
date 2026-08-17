import os
import time
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv

try:
    from langdetect import detect
except Exception:
    detect = None

from core.llm_factory import get_llm
from core.db_factory import get_engine, get_sqldb
from core.schema_grounding import schema_text
from core.retrieval import build_retrievers, retrieve_context
from core.prompts import sql_generation_prompt, sql_fix_prompt, viz_prompt
from core.memory import format_chat_history
from core.sql_safety import (
    normalize_sql,
    is_read_only_select,
    enforce_limit,
)
from core.json_utils import extract_json_object
from core.ambiguity import resolve_question
from core.sql_rewrite import fix_table_and_column_qualifiers
from auth.rbac import get_max_limit, validate_sql_for_role


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "queries.jsonl"


@dataclass
class BIResponse:
    assistant_md: str
    sql: str | None
    df: pd.DataFrame | None
    chart_spec: dict | None
    error: str | None
    elapsed_ms: int
    fix_retries: int
    needs_clarification: bool = False

    # Stage-level timing information in milliseconds
    t_retrieval_ms: int | None = None
    t_sql_gen_ms: int | None = None
    t_exec_ms: int | None = None
    t_viz_ms: int | None = None


# ---------------------------------------------------------------------
# Cached process-level resources
# ---------------------------------------------------------------------

_ENGINE = None
_SQLDB = None
_AVAILABLE_TABLES = None
_SCHEMA_INFO = None
_TABLE_RET = None
_SEM_RET = None


def _get_cached_resources():
    """
    Initialize database/schema/retriever resources only once per process.

    Previously these objects were rebuilt for every user question.
    Rebuilding the schema and BM25 indexes caused unnecessary overhead.
    """

    global _ENGINE
    global _SQLDB
    global _AVAILABLE_TABLES
    global _SCHEMA_INFO
    global _TABLE_RET
    global _SEM_RET

    if _ENGINE is None:
        _ENGINE = get_engine()

    if _SQLDB is None:
        _SQLDB = get_sqldb()

    if _SCHEMA_INFO is None:
        _AVAILABLE_TABLES = list(
            _SQLDB.get_usable_table_names()
        )

        _SCHEMA_INFO = schema_text(_SQLDB)

        _TABLE_RET, _SEM_RET = build_retrievers(
            _SCHEMA_INFO,
            ROOT,
        )

    return (
        _ENGINE,
        _SQLDB,
        _AVAILABLE_TABLES,
        _SCHEMA_INFO,
        _TABLE_RET,
        _SEM_RET,
    )


def clear_resource_cache():
    """
    Clear cached database/schema/retriever resources.

    Use this after changing the database or schema.
    """

    global _ENGINE
    global _SQLDB
    global _AVAILABLE_TABLES
    global _SCHEMA_INFO
    global _TABLE_RET
    global _SEM_RET

    _ENGINE = None
    _SQLDB = None
    _AVAILABLE_TABLES = None
    _SCHEMA_INFO = None
    _TABLE_RET = None
    _SEM_RET = None


def log_event(payload: dict):
    LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with LOG_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n"
        )


def run_query(engine, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(
        text(sql),
        engine,
    )


def language_hint_from_question(question: str) -> str:
    if detect is None:
        return "en"

    try:
        return detect(question)
    except Exception:
        return "en"


def df_preview_text(df: pd.DataFrame) -> str:
    if df is None:
        return ""

    small = df.head(12)

    try:
        return small.to_markdown(index=False)
    except Exception:
        return small.to_csv(index=False)


def fallback_chart_spec(
    df: pd.DataFrame,
    user_question: str,
) -> dict:
    if df is None or df.empty:
        return {
            "summary_md": "No rows were returned.",
            "chart_type": "table",
            "x": None,
            "y": None,
            "title": "No Results",
        }

    columns = df.columns.tolist()

    # Single-value result: KPI
    if df.shape == (1, 1):
        return {
            "summary_md": (
                f"Returned a single KPI value for "
                f"**{columns[0]}**."
            ),
            "chart_type": "kpi",
            "x": None,
            "y": columns[0],
            "title": str(columns[0]),
        }

    # Two or more columns: basic category/value chart
    if len(columns) >= 2:
        x = columns[0]
        y = columns[1]

        x_lower = str(x).lower()

        chart_type = (
            "line"
            if any(
                keyword in x_lower
                for keyword in [
                    "date",
                    "month",
                    "year",
                    "time",
                    "period",
                ]
            )
            else "bar"
        )

        return {
            "summary_md": (
                f"Returned **{len(df)} rows** "
                "for the requested analysis."
            ),
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "title": user_question[:80],
        }

    return {
        "summary_md": f"Returned **{len(df)} rows**.",
        "chart_type": "table",
        "x": None,
        "y": None,
        "title": "Result",
    }


def _needs_llm_chart_decision(df: pd.DataFrame) -> bool:
    """
    Return True only when visualization selection requires an LLM.

    Rule-based chart selection is sufficient for:
      - Empty results
      - One-column results
      - Two-column results
      - Single KPI results

    Results with three or more columns may require semantic decisions,
    so they are sent to the visualization LLM.
    """

    if df is None or df.empty:
        return False

    return df.shape[1] > 2


def _is_time_series_question(question: str) -> bool:
    question = (question or "").lower()

    return any(
        keyword in question
        for keyword in [
            "trend",
            "over time",
            "time series",
            "monthly",
            "yearly",
            "weekly",
            "daily",
            "by month",
            "by year",
            "by week",
            "by day",
        ]
    )


def _pick_time_x_column(
    df: pd.DataFrame,
) -> str | None:
    if df is None or df.empty:
        return None

    for column in df.columns:
        name = str(column).lower()

        if any(
            keyword in name
            for keyword in [
                "date",
                "month",
                "year",
                "time",
                "period",
            ]
        ):
            return column

    return None


def _pick_numeric_y_column(
    df: pd.DataFrame,
    exclude: str | None = None,
) -> str | None:
    if df is None or df.empty:
        return None

    for column in df.columns:
        if exclude and column == exclude:
            continue

        numeric_values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if numeric_values.notna().any():
            return column

    return None


def force_timeseries_chart_if_needed(
    user_question: str,
    df: pd.DataFrame,
    chart_spec: dict | None,
) -> dict | None:
    """
    Ensure time-series questions use a line chart.
    """

    if df is None or df.empty:
        return chart_spec

    if not _is_time_series_question(user_question):
        return chart_spec

    spec = (
        chart_spec
        if isinstance(chart_spec, dict)
        else {}
    )

    columns = df.columns.tolist()

    chart_x = spec.get("x")
    chart_y = spec.get("y")

    if chart_x not in columns:
        chart_x = None

    if chart_y not in columns:
        chart_y = None

    if chart_x is None:
        chart_x = (
            _pick_time_x_column(df)
            or (columns[0] if columns else None)
        )

    if chart_y is None:
        chart_y = (
            _pick_numeric_y_column(
                df,
                exclude=chart_x,
            )
            or (columns[1] if len(columns) > 1 else None)
        )

    if not chart_x or not chart_y:
        return spec or chart_spec

    spec["chart_type"] = "line"
    spec["x"] = chart_x
    spec["y"] = chart_y
    spec["title"] = (
        spec.get("title")
        or user_question[:80]
    )
    spec["summary_md"] = (
        spec.get("summary_md")
        or f"Returned **{len(df)} rows**."
    )

    return spec


def _timing_dict(
    t_setup: float,
    t_retrieval: float,
    t_sql_gen: float,
    t_exec: float,
    t_viz: float | None = None,
) -> dict:
    """
    Convert internal timestamps into millisecond timings.
    """

    timings = {
        "t_retrieval_ms": int(
            (t_retrieval - t_setup) * 1000
        ),
        "t_sql_gen_ms": int(
            (t_sql_gen - t_retrieval) * 1000
        ),
        "t_exec_ms": int(
            (t_exec - t_sql_gen) * 1000
        ),
        "t_viz_ms": (
            int((t_viz - t_exec) * 1000)
            if t_viz is not None
            else 0
        ),
    }

    return timings


def answer_question(
    user_question: str,
    chat_messages: list,
    role: str = "executive",
    source: str = "app",
) -> BIResponse:
    """
    Execute one conversational BI question.

    source:
      - app: normal application traffic
      - eval: evaluation traffic
    """

    load_dotenv(
        ROOT / ".env",
        override=True,
    )

    t0 = time.time()

    # ---------------------------------------------------------------
    # 1. Resolve conversation ambiguity
    # ---------------------------------------------------------------

    decision = resolve_question(
        user_question,
        chat_messages,
    )

    resolved_question = decision.resolved_question

    if decision.needs_clarification:
        elapsed = int(
            (time.time() - t0) * 1000
        )

        log_event(
            {
                "source": source,
                "role": role,
                "question": resolved_question,
                "sql": None,
                "success": False,
                "error": "clarification_required",
                "rows": None,
                "elapsed_ms": elapsed,
                "fix_retries": 0,
            }
        )

        return BIResponse(
            assistant_md=(
                decision.message
                or "Please clarify your request."
            ),
            sql=None,
            df=None,
            chart_spec=None,
            error=None,
            elapsed_ms=elapsed,
            fix_retries=0,
            needs_clarification=True,
        )

    # ---------------------------------------------------------------
    # 2. Load cached resources
    # ---------------------------------------------------------------

    llm = get_llm()

    (
        engine,
        _sqldb,
        available_tables,
        _schema_info,
        table_ret,
        sem_ret,
    ) = _get_cached_resources()

    t_setup = time.time()

    context = retrieve_context(
        resolved_question,
        table_ret,
        sem_ret,
        k_tables=8,
        k_sem=3,
    )

    history = format_chat_history(
        chat_messages,
        max_turns=10,
    )

    language_hint = language_hint_from_question(
        resolved_question
    )

    t_retrieval = time.time()

    default_limit = 200
    role_max_limit = get_max_limit(role)

    max_fix_retries = int(
        os.getenv(
            "MAX_FIX_RETRIES",
            "2",
        )
    )

    # ---------------------------------------------------------------
    # 3. Generate SQL
    # ---------------------------------------------------------------

    generation_prompt = sql_generation_prompt(
        user_question=resolved_question,
        chat_history=history,
        retrieved_tables=context.table_snippets,
        retrieved_semantic=context.semantic_snippets,
        language_hint=language_hint,
        default_limit=default_limit,
        max_limit=role_max_limit,
    )

    raw_sql_response = llm.invoke(
        generation_prompt
    )

    raw_sql = getattr(
        raw_sql_response,
        "content",
        str(raw_sql_response),
    )

    sql = normalize_sql(raw_sql)

    sql = enforce_limit(
        sql,
        default_limit=default_limit,
        max_limit=role_max_limit,
    )

    sql = fix_table_and_column_qualifiers(
        sql,
        available_tables,
    )

    t_sql_gen = time.time()

    timings_before_execution = {
        "t_retrieval_ms": int(
            (t_retrieval - t_setup) * 1000
        ),
        "t_sql_gen_ms": int(
            (t_sql_gen - t_retrieval) * 1000
        ),
    }

    # ---------------------------------------------------------------
    # 4. Safety and RBAC validation
    # ---------------------------------------------------------------

    if not is_read_only_select(sql):
        elapsed = int(
            (time.time() - t0) * 1000
        )

        error_message = (
            "Blocked unsafe SQL. "
            "Only read-only SELECT queries are allowed."
        )

        log_event(
            {
                "source": source,
                "role": role,
                "question": resolved_question,
                "sql": sql,
                "success": False,
                "error": error_message,
                "rows": None,
                "elapsed_ms": elapsed,
                "fix_retries": 0,
                **timings_before_execution,
            }
        )

        return BIResponse(
            assistant_md=error_message,
            sql=sql,
            df=None,
            chart_spec=None,
            error=error_message,
            elapsed_ms=elapsed,
            fix_retries=0,
            **timings_before_execution,
        )

    allowed, rbac_error = validate_sql_for_role(
        sql,
        role,
    )

    if not allowed:
        elapsed = int(
            (time.time() - t0) * 1000
        )

        error_message = (
            rbac_error
            or "Access denied."
        )

        log_event(
            {
                "source": source,
                "role": role,
                "question": resolved_question,
                "sql": sql,
                "success": False,
                "error": error_message,
                "rows": None,
                "elapsed_ms": elapsed,
                "fix_retries": 0,
                **timings_before_execution,
            }
        )

        return BIResponse(
            assistant_md=error_message,
            sql=sql,
            df=None,
            chart_spec=None,
            error=error_message,
            elapsed_ms=elapsed,
            fix_retries=0,
            **timings_before_execution,
        )

    # ---------------------------------------------------------------
    # 5. Execute SQL and self-correct if needed
    # ---------------------------------------------------------------

    df = None
    last_error = None
    fix_retries = 0

    for attempt in range(max_fix_retries + 1):
        try:
            df = run_query(
                engine,
                sql,
            )

            last_error = None
            fix_retries = attempt
            break

        except Exception as exc:
            last_error = str(exc)

            if attempt >= max_fix_retries:
                break

            fix_prompt = sql_fix_prompt(
                user_question=resolved_question,
                bad_sql=sql,
                error=last_error,
                retrieved_tables=context.table_snippets,
                retrieved_semantic=context.semantic_snippets,
                default_limit=default_limit,
                max_limit=role_max_limit,
            )

            fixed_response = llm.invoke(
                fix_prompt
            )

            fixed_raw = getattr(
                fixed_response,
                "content",
                str(fixed_response),
            )

            fixed_sql = normalize_sql(
                fixed_raw
            )

            fixed_sql = enforce_limit(
                fixed_sql,
                default_limit=default_limit,
                max_limit=role_max_limit,
            )

            fixed_sql = fix_table_and_column_qualifiers(
                fixed_sql,
                available_tables,
            )

            if not is_read_only_select(fixed_sql):
                last_error = (
                    "The self-correction model generated "
                    "unsafe SQL."
                )
                break

            allowed, rbac_error = validate_sql_for_role(
                fixed_sql,
                role,
            )

            if not allowed:
                last_error = (
                    rbac_error
                    or "Corrected SQL was denied by RBAC."
                )
                break

            sql = fixed_sql

    t_exec = time.time()

    timings_after_execution = _timing_dict(
        t_setup=t_setup,
        t_retrieval=t_retrieval,
        t_sql_gen=t_sql_gen,
        t_exec=t_exec,
    )

    if last_error is not None or df is None:
        elapsed = int(
            (time.time() - t0) * 1000
        )

        log_event(
            {
                "source": source,
                "role": role,
                "question": resolved_question,
                "sql": sql,
                "success": False,
                "error": last_error,
                "rows": None,
                "elapsed_ms": elapsed,
                "fix_retries": fix_retries,
                **timings_after_execution,
            }
        )

        return BIResponse(
            assistant_md=(
                "Could not execute the query.\n\n"
                f"Error:\n\n`{last_error}`"
            ),
            sql=sql,
            df=None,
            chart_spec=None,
            error=last_error,
            elapsed_ms=elapsed,
            fix_retries=fix_retries,
            **timings_after_execution,
        )

    # ---------------------------------------------------------------
    # 6. Visualization
    # ---------------------------------------------------------------

    # Use fast deterministic chart selection for simple result shapes.
    # This avoids a second 4-second Ollama call for most questions.
    if _needs_llm_chart_decision(df):
        preview = df_preview_text(df)

        visualization_prompt = viz_prompt(
            user_question=resolved_question,
            df_head_md=preview,
            columns=df.columns.tolist(),
            language_hint=language_hint,
        )

        visualization_response = llm.invoke(
            visualization_prompt
        )

        visualization_raw = getattr(
            visualization_response,
            "content",
            str(visualization_response),
        )

        chart_spec = extract_json_object(
            visualization_raw
        )

        if not isinstance(chart_spec, dict):
            chart_spec = fallback_chart_spec(
                df,
                resolved_question,
            )
    else:
        chart_spec = fallback_chart_spec(
            df,
            resolved_question,
        )

    chart_spec = force_timeseries_chart_if_needed(
        resolved_question,
        df,
        chart_spec,
    )

    t_viz = time.time()

    final_timings = _timing_dict(
        t_setup=t_setup,
        t_retrieval=t_retrieval,
        t_sql_gen=t_sql_gen,
        t_exec=t_exec,
        t_viz=t_viz,
    )

    assistant_md = None

    if isinstance(chart_spec, dict):
        assistant_md = chart_spec.get(
            "summary_md"
        )

    assistant_md = (
        assistant_md
        or f"Returned **{len(df)} rows**."
    )

    elapsed = int(
        (time.time() - t0) * 1000
    )

    log_event(
        {
            "source": source,
            "role": role,
            "question": resolved_question,
            "sql": sql,
            "success": True,
            "error": None,
            "rows": len(df),
            "elapsed_ms": elapsed,
            "fix_retries": fix_retries,
            "chart_type": (
                chart_spec.get("chart_type")
                if isinstance(chart_spec, dict)
                else None
            ),
            **final_timings,
        }
    )

    return BIResponse(
        assistant_md=assistant_md,
        sql=sql,
        df=df,
        chart_spec=chart_spec,
        error=None,
        elapsed_ms=elapsed,
        fix_retries=fix_retries,
        needs_clarification=False,
        **final_timings,
    )