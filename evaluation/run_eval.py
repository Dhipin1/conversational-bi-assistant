import sys
import json
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from dotenv import load_dotenv
from core.pipeline import answer_question

load_dotenv(ROOT / ".env", override=True)

QUESTIONS_PATH = ROOT / "evaluation" / "golden_questions.jsonl"
OUT_CSV = ROOT / "evaluation" / "eval_results.csv"
OUT_MD = ROOT / "evaluation" / "eval_summary.md"

DESTRUCTIVE_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
)


def load_questions() -> list[dict]:
    rows = []

    if not QUESTIONS_PATH.exists():
        raise FileNotFoundError(f"Questions file not found: {QUESTIONS_PATH}")

    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

    return rows


def check_correctness(res, expected: dict) -> dict:
    """
    Check optional expectation fields from golden_questions.jsonl.

    Supported fields:
      expect_clarification
      expect_blocked
      expect_safe_sql
      expect_row_count
      expect_min_rows
      expect_zero_rows
      expect_table
      expect_no_limit
      expect_chart_type
    """
    checks = {}

    sql = res.sql or ""
    sql_upper = sql.upper()
    rows = None if res.df is None else len(res.df)

    # Clarification expectation
    if "expect_clarification" in expected:
        checks["clarification_ok"] = (
            res.needs_clarification == expected["expect_clarification"]
        )

    # Explicit blocking expectation
    if "expect_blocked" in expected:
        blocked = (
            res.error is not None
            and res.df is None
            and not res.needs_clarification
        )

        checks["blocked_ok"] = (
            blocked == expected["expect_blocked"]
        )

    # Final generated SQL must not contain destructive operations.
    #
    # This is more appropriate than expecting the natural-language prompt
    # itself to be blocked. The LLM may safely convert an adversarial-looking
    # prompt into a harmless SELECT query.
    if "expect_safe_sql" in expected:
        generated_sql_is_safe = (
            res.sql is not None
            and not any(
                keyword in sql_upper
                for keyword in DESTRUCTIVE_KEYWORDS
            )
        )

        checks["safe_sql_ok"] = (
            generated_sql_is_safe == expected["expect_safe_sql"]
        )

    # Exact row count
    if "expect_row_count" in expected:
        checks["row_count_ok"] = (
            rows == expected["expect_row_count"]
        )

    # Minimum row count
    if "expect_min_rows" in expected:
        checks["min_rows_ok"] = (
            rows is not None
            and rows >= expected["expect_min_rows"]
        )

    # Empty result expectation
    if "expect_zero_rows" in expected:
        checks["zero_rows_ok"] = (
            (rows == 0) == expected["expect_zero_rows"]
        )

    # Expected table name in generated SQL
    if "expect_table" in expected:
        checks["table_ok"] = (
            expected["expect_table"].upper() in sql_upper
        )

    # Aggregate queries should not have an unnecessary LIMIT
    if "expect_no_limit" in expected:
        has_limit = "LIMIT" in sql_upper

        checks["no_limit_ok"] = (
            has_limit is False
        ) == expected["expect_no_limit"]

    # Expected visualization type
    if "expect_chart_type" in expected:
        chart_type = None

        if isinstance(res.chart_spec, dict):
            chart_type = res.chart_spec.get("chart_type")

        checks["chart_type_ok"] = (
            chart_type == expected["expect_chart_type"]
        )

    return checks


def result_record(
    *,
    qid,
    difficulty,
    role,
    question,
    exec_success,
    correctness_ok,
    correctness_checks,
    res=None,
    elapsed_ms=None,
    error=None,
):
    """
    Build a consistent result dictionary for successful and failed tests.
    """

    if res is not None:
        rows = None if res.df is None else len(res.df)
        chart_type = (
            res.chart_spec.get("chart_type")
            if isinstance(res.chart_spec, dict)
            else None
        )

        return {
            "id": qid,
            "difficulty": difficulty,
            "role": role,
            "question": question,
            "exec_success": exec_success,
            "correctness_ok": correctness_ok,
            "correctness_checks": (
                json.dumps(correctness_checks, ensure_ascii=False)
                if correctness_checks
                else None
            ),
            "needs_clarification": res.needs_clarification,
            "rows": rows,
            "elapsed_ms": res.elapsed_ms,
            "fix_retries": res.fix_retries,
            "error": res.error,
            "sql": res.sql,
            "chart_type": chart_type,
            "t_retrieval_ms": res.t_retrieval_ms,
            "t_sql_gen_ms": res.t_sql_gen_ms,
            "t_exec_ms": res.t_exec_ms,
            "t_viz_ms": res.t_viz_ms,
        }

    return {
        "id": qid,
        "difficulty": difficulty,
        "role": role,
        "question": question,
        "exec_success": exec_success,
        "correctness_ok": correctness_ok,
        "correctness_checks": None,
        "needs_clarification": False,
        "rows": None,
        "elapsed_ms": elapsed_ms,
        "fix_retries": None,
        "error": error,
        "sql": None,
        "chart_type": None,
        "t_retrieval_ms": None,
        "t_sql_gen_ms": None,
        "t_exec_ms": None,
        "t_viz_ms": None,
    }


def run_eval():
    questions = load_questions()
    results = []

    for item in questions:
        qid = item.get("id")
        question = item["question"]
        difficulty = item.get("difficulty", "unknown")
        role = item.get("role", "admin")

        # Each evaluation case can provide its own conversation context.
        context = item.get("context", [])

        expected = {
            key: value
            for key, value in item.items()
            if key.startswith("expect_")
        }

        print(f"\n[{qid}] {question}  (role={role})")

        t0 = time.time()

        try:
            response = answer_question(
                user_question=question,
                chat_messages=context,
                role=role,
                source="eval",
            )

             # Clarification is a valid, intentional outcome — not a failure.
            exec_success = (
                response.error is None
                and (response.needs_clarification or response.df is not None)
            )

            correctness_checks = check_correctness(
                response,
                expected,
            )

            correctness_ok = (
                all(correctness_checks.values())
                if correctness_checks
                else None
            )

            rows = (
                None
                if response.df is None
                else len(response.df)
            )

            print("Execution success:", exec_success)
            print("SQL:", response.sql)
            print("Rows:", rows)
            print("Clarification:", response.needs_clarification)
            print("Error:", response.error)

            if correctness_checks:
                print("Correctness checks:", correctness_checks)

            results.append(
                result_record(
                    qid=qid,
                    difficulty=difficulty,
                    role=role,
                    question=question,
                    exec_success=exec_success,
                    correctness_ok=correctness_ok,
                    correctness_checks=correctness_checks,
                    res=response,
                )
            )

        except Exception as exc:
            elapsed_ms = int((time.time() - t0) * 1000)

            print("FAILED:", repr(exc))

            results.append(
                result_record(
                    qid=qid,
                    difficulty=difficulty,
                    role=role,
                    question=question,
                    exec_success=False,
                    correctness_ok=False,
                    correctness_checks={},
                    elapsed_ms=elapsed_ms,
                    error=str(exc),
                )
            )

    if not results:
        print("No evaluation questions found.")
        return

    df = pd.DataFrame(results)
    df.to_csv(OUT_CSV, index=False)

    total = len(df)

    execution_success_count = int(
        df["exec_success"].fillna(False).sum()
    )

    execution_success_rate = (
        round(execution_success_count / total * 100, 2)
        if total
        else 0
    )

    scored = df[df["correctness_ok"].notna()]

    correctness_rate = (
        round(scored["correctness_ok"].mean() * 100, 2)
        if len(scored)
        else None
    )

    average_latency = (
        round(df["elapsed_ms"].mean(), 2)
        if total
        else 0
    )

    retry_rate = (
        round(
            (df["fix_retries"].fillna(0) > 0).mean() * 100,
            2,
        )
        if total
        else 0
    )

    by_difficulty = (
        df.groupby("difficulty")["exec_success"]
        .mean()
        .mul(100)
        .round(2)
        .to_dict()
    )

    stage_columns = [
        "t_retrieval_ms",
        "t_sql_gen_ms",
        "t_exec_ms",
        "t_viz_ms",
    ]

    stage_averages = {}

    for column in stage_columns:
        values = df[column].dropna()

        stage_averages[column] = (
            round(values.mean(), 2)
            if not values.empty
            else None
        )

    failed_rows = df[
        df["exec_success"] == False
    ][
        ["id", "question", "error"]
    ]

    incorrect_rows = df[
        df["correctness_ok"] == False
    ][
        ["id", "question", "correctness_checks"]
    ]

    summary_lines = [
        "# Evaluation Summary",
        "",
        f"Total questions: {total}",
        "",
        (
            f"Execution success: "
            f"{execution_success_count}/{total} "
            f"({execution_success_rate}%)"
        ),
        "",
        (
            "Correctness rate "
            f"(scored questions only, n={len(scored)}): "
            f"{correctness_rate if correctness_rate is not None else 'N/A'}%"
        ),
        "",
        f"Average latency: {average_latency} ms",
        "",
        f"Self-correction retry rate: {retry_rate}%",
        "",
        "## Latency by stage (average, ms)",
        "",
        (
            "- Retrieval/schema/BM25: "
            f"{stage_averages['t_retrieval_ms']}"
        ),
        (
            "- SQL generation LLM call: "
            f"{stage_averages['t_sql_gen_ms']}"
        ),
        (
            "- SQL execution: "
            f"{stage_averages['t_exec_ms']}"
        ),
        (
            "- Visualization LLM call: "
            f"{stage_averages['t_viz_ms']}"
        ),
        "",
        "## Execution success by difficulty",
        "",
    ]

    for difficulty_name, rate in by_difficulty.items():
        summary_lines.append(
            f"- {difficulty_name}: {rate}%"
        )

    if not failed_rows.empty:
        summary_lines.extend(
            [
                "",
                "## Failed questions",
                "",
            ]
        )

        for _, row in failed_rows.iterrows():
            summary_lines.append(
                f"- [{row['id']}] "
                f"{row['question']} — `{row['error']}`"
            )

    if not incorrect_rows.empty:
        summary_lines.extend(
            [
                "",
                "## Incorrect expectation checks",
                "",
            ]
        )

        for _, row in incorrect_rows.iterrows():
            summary_lines.append(
                f"- [{row['id']}] "
                f"{row['question']} — "
                f"{row['correctness_checks']}"
            )

    summary_lines.extend(
        [
            "",
            f"Results file: `{OUT_CSV.relative_to(ROOT)}`",
        ]
    )

    summary = "\n".join(summary_lines)

    OUT_MD.write_text(
        summary,
        encoding="utf-8",
    )

    print("\n" + summary)


if __name__ == "__main__":
    run_eval()