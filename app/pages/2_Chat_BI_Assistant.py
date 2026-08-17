import sys
import json
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from app.session_state import init_session
from core.pipeline import answer_question
from core.favorites import list_favorites, add_favorite, delete_favorite
from core.sql_format import format_sql_pretty
from viz.plotly_factory import (
    chart_from_spec,
    kpi_values,
    render_chart,
    CHART_TYPES,
    fig_to_png_bytes,
    fig_to_html,
)

init_session()

if "run_question" not in st.session_state:
    st.session_state.run_question = None

# Used to create unique keys for "live" charts
if "turn_id" not in st.session_state:
    st.session_state.turn_id = 0

st.set_page_config(page_title="Chat BI Assistant", layout="wide")
st.title("Chat BI Assistant (Advanced)")

if not st.session_state.user:
    st.warning("Please login first: Pages → Login")
    st.stop()

username = st.session_state.user["username"]
role = st.session_state.user["role"]


# -------------------------
# Helpers
# -------------------------
def df_to_store(df: pd.DataFrame, max_rows: int = 200):
    if df is None:
        return None
    df_small = df.head(max_rows).copy()
    return df_small.to_json(orient="split")


def df_from_store(value):
    if not value:
        return None
    try:
        payload = json.loads(value) if isinstance(value, str) else value
        return pd.DataFrame(
            data=payload.get("data", []),
            columns=payload.get("columns", []),
            index=payload.get("index", None),
        )
    except Exception as error:
        st.warning(f"Could not restore saved results: {error}")
        return None


def default_xy(df: pd.DataFrame):
    if df is None or df.empty:
        return None, None
    numeric, non_numeric = [], []
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        (numeric if s.notna().any() else non_numeric).append(c)
    x = non_numeric[0] if non_numeric else df.columns[0]
    y = numeric[0] if numeric else (df.columns[1] if len(df.columns) > 1 else None)
    return x, y


def is_date_like(series: pd.Series) -> bool:
    try:
        dt = pd.to_datetime(series, errors="coerce")
        return dt.notna().mean() >= 0.8
    except Exception:
        return False


def apply_df_controls(df: pd.DataFrame, x_col: str | None, y_col: str | None,
                      top_n: int | None, sort_order: str, date_range: tuple | None):
    if df is None:
        return df
    out = df.copy()
    if out.empty:
        return out

    if x_col and x_col in out.columns and date_range and is_date_like(out[x_col]):
        dt = pd.to_datetime(out[x_col], errors="coerce")
        start, end = date_range
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        mask = (dt >= start_dt) & (dt <= end_dt)
        out = out.loc[mask].copy()

    if y_col and y_col in out.columns and sort_order in ("ASC", "DESC"):
        y_num = pd.to_numeric(out[y_col], errors="coerce")
        if y_num.notna().any():
            out = out.assign(_y=y_num).sort_values("_y", ascending=(sort_order == "ASC")).drop(columns=["_y"])

    if top_n and top_n > 0 and len(out) > top_n:
        out = out.head(top_n).copy()

    return out


def render_sql_block(sql: str, expanded: bool, unique_key: str):
    """Pretty SQL + wrapped view + download."""
    if not sql:
        return
    pretty = format_sql_pretty(sql)

    with st.expander("Generated SQL", expanded=expanded):
        st.code(pretty, language="sql")
        st.text_area("SQL (wrapped)", pretty, height=220, key=f"sql_wrap_{unique_key}")
        st.download_button(
            "Download SQL",
            data=pretty.encode("utf-8"),
            file_name="generated.sql",
            mime="text/plain",
            key=f"sql_dl_{unique_key}",
        )


def render_saved_result(message_index: int, m: dict):
    df_prev = df_from_store(m.get("df_preview_json"))
    if df_prev is None:
        return

    st.subheader("Results (preview)")
    st.caption(f"Rows returned (preview): {len(df_prev)}")
    st.dataframe(df_prev, use_container_width=True)

    st.download_button(
        label="Download Results CSV (preview)",
        data=df_prev.to_csv(index=False).encode("utf-8"),
        file_name="bi_result_preview.csv",
        mime="text/csv",
        key=f"csv_saved_{message_index}",
    )

    # Save favorite
    source_q = m.get("source_question") or ""
    with st.expander("Save as favorite", expanded=False):
        fav_name = st.text_input(
            "Favorite name",
            value=(source_q or "Favorite")[:40],
            key=f"fav_name_saved_{message_index}",
        )
        if st.button("Save favorite", key=f"fav_save_saved_{message_index}"):
            if not source_q.strip():
                st.warning("No source question stored for this result.")
            else:
                add_favorite(username, fav_name.strip() or "Favorite", source_q)
                st.success("Saved to favorites.")
                st.rerun()

    if df_prev.empty:
        st.info("This query returned 0 rows. Try a different year/time range or remove filters.")
        return

    # KPI
    if (m.get("chart_spec") or {}).get("chart_type") == "kpi":
        kpis = kpi_values(df_prev)
        cols = st.columns(max(1, min(len(kpis), 4)))
        for i, (name, value) in enumerate(kpis.items()):
            cols[i % len(cols)].metric(name, value)

    cols_list = df_prev.columns.tolist()
    x_def, y_def = default_xy(df_prev)

    override = m.get("chart_override") or {}
    override_type = override.get("chart_type", "auto")
    override_x = override.get("x", x_def)
    override_y = override.get("y", y_def)
    override_topn = int(override.get("top_n", 10))
    override_sort = override.get("sort_order", "DESC")
    override_date = override.get("date_range", None)

    with st.expander("Customize chart (Top N / Sort / Date filter / Type)", expanded=False):
        chart_type = st.selectbox(
            "Chart type",
            CHART_TYPES,
            index=CHART_TYPES.index(override_type) if override_type in CHART_TYPES else 0,
            key=f"chart_type_{message_index}"
        )
        x_col = st.selectbox(
            "X column",
            cols_list,
            index=cols_list.index(override_x) if override_x in cols_list else 0,
            key=f"x_col_{message_index}"
        )

        y_col = None
        if len(cols_list) >= 2:
            y_col = st.selectbox(
                "Y column",
                cols_list,
                index=cols_list.index(override_y) if override_y in cols_list else 1,
                key=f"y_col_{message_index}"
            )

        sort_order = st.selectbox(
            "Sort order (by Y)",
            ["DESC", "ASC", "NONE"],
            index=["DESC", "ASC", "NONE"].index(override_sort) if override_sort in ["DESC", "ASC", "NONE"] else 0,
            key=f"sort_{message_index}"
        )

        top_n = st.slider(
            "Top N (for chart/table preview)",
            min_value=3, max_value=50, value=override_topn, step=1,
            key=f"topn_{message_index}"
        )

        date_range = None
        if x_col and x_col in cols_list and is_date_like(df_prev[x_col]):
            dt = pd.to_datetime(df_prev[x_col], errors="coerce")
            dmin = dt.min().date()
            dmax = dt.max().date()
            start_default, end_default = override_date if override_date else (dmin, dmax)
            picked = st.date_input(
                "Date range filter (uses X column)",
                value=(start_default, end_default),
                min_value=dmin,
                max_value=dmax,
                key=f"daterange_{message_index}"
            )
            if isinstance(picked, tuple) and len(picked) == 2:
                date_range = (picked[0], picked[1])

        if st.button("Apply settings", key=f"apply_{message_index}"):
            m["chart_override"] = {
                "chart_type": chart_type,
                "x": x_col,
                "y": y_col,
                "sort_order": sort_order,
                "top_n": top_n,
                "date_range": date_range,
            }
            st.session_state.chat_messages[message_index] = m
            st.rerun()

        if st.button("Reset to Auto", key=f"reset_{message_index}"):
            m["chart_override"] = {
                "chart_type": "auto",
                "x": x_def,
                "y": y_def,
                "sort_order": "DESC",
                "top_n": 10,
                "date_range": None
            }
            st.session_state.chat_messages[message_index] = m
            st.rerun()

    override = m.get("chart_override") or {}
    chart_type = (override.get("chart_type") or "auto").lower()
    x_col = override.get("x", x_def)
    y_col = override.get("y", y_def)
    top_n = int(override.get("top_n", 10))
    sort_order = override.get("sort_order", "DESC")
    date_range = override.get("date_range", None)

    df_work = apply_df_controls(df_prev, x_col, y_col, top_n, sort_order, date_range)
    if df_work.empty:
        st.info("After filters/sorting/top-N, there are 0 rows to chart.")
        return

    if chart_type == "auto":
        fig = chart_from_spec(df_work, m.get("chart_spec") or {})
    else:
        fig = render_chart(df_work, chart_type, x_col, y_col, title=m.get("chart_title") or "Custom chart")

    if fig is not None:
        st.subheader("Visualization")
        st.plotly_chart(fig, use_container_width=True, key=f"chart_saved_{message_index}")

        colA, colB = st.columns(2)
        with colA:
            st.download_button(
                "Download chart PNG",
                data=fig_to_png_bytes(fig),
                file_name="chart.png",
                mime="image/png",
                key=f"png_{message_index}"
            )
        with colB:
            st.download_button(
                "Download chart HTML",
                data=fig_to_html(fig).encode("utf-8"),
                file_name="chart.html",
                mime="text/html",
                key=f"html_{message_index}"
            )


# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.subheader("User")
    st.write(f"Username: `{username}`")
    st.write(f"Role: `{role}`")

    expand_sql = st.checkbox("Auto-expand SQL", value=True)

    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()

    st.divider()
    st.subheader("Saved favorites")
    favs = list_favorites(username)
    if favs:
        for i, f in enumerate(favs):
            c1, c2 = st.columns([0.85, 0.15])
            with c1:
                if st.button(f"▶ {f['name']}", key=f"fav_run_{i}"):
                    st.session_state.run_question = f["question"]
                    st.rerun()
            with c2:
                if st.button("✕", key=f"fav_del_{i}"):
                    delete_favorite(username, i)
                    st.rerun()
    else:
        st.caption("No favorites saved yet.")

    st.divider()
    st.subheader("Example Queries")
    st.caption("Try these:")
    st.code("Revenue by country")
    st.code("Top 10 products by revenue")


# -------------------------
# Render chat history
# -------------------------
for idx, m in enumerate(st.session_state.chat_messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

        # Generated SQL block (pretty + wrap + download)
        if m.get("sql"):
            render_sql_block(m["sql"], expanded=expand_sql, unique_key=f"hist_{idx}")

        if m["role"] == "assistant" and m.get("df_preview_json") is not None:
            render_saved_result(idx, m)


# -------------------------
# Input question
# -------------------------
question = st.session_state.run_question or st.chat_input("Ask a BI question about Northwind...")
if st.session_state.run_question:
    st.session_state.run_question = None

if question:
    st.session_state.turn_id += 1
    st.session_state.chat_messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Thinking, generating SQL, executing query..."):
            res = answer_question(
                user_question=question,
                chat_messages=st.session_state.chat_messages,
                role=role,
            )

        st.markdown(res.assistant_md)

        if res.sql:
            # Show formatted SQL as expander
            render_sql_block(res.sql, expanded=True, unique_key=f"live_{st.session_state.turn_id}")

        if res.error:
            st.error(res.error)

        df_preview_json = None
        chart_override = None
        chart_title = None

        if res.df is not None:
            st.subheader("Results")
            st.caption(f"Rows returned: {len(res.df)}")
            st.dataframe(res.df, use_container_width=True)

            st.download_button(
                label="Download Results CSV",
                data=res.df.to_csv(index=False).encode("utf-8"),
                file_name="bi_result.csv",
                mime="text/csv",
                key=f"csv_live_{st.session_state.turn_id}",
            )

            if not res.df.empty:
                fig = chart_from_spec(res.df, res.chart_spec or {})
                if fig is not None:
                    st.subheader("Visualization")
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_live_{st.session_state.turn_id}")

            df_preview_json = df_to_store(res.df, max_rows=200)

            if not res.df.empty:
                x_def, y_def = default_xy(res.df)
                chart_override = {"chart_type": "auto", "x": x_def, "y": y_def, "sort_order": "DESC", "top_n": 10, "date_range": None}
                chart_title = res.chart_spec.get("title") if isinstance(res.chart_spec, dict) else "Chart"

            st.caption(f"Elapsed: {res.elapsed_ms} ms | Self-correction retries: {res.fix_retries}")

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": res.assistant_md,
            "sql": res.sql,
            "df_preview_json": df_preview_json,
            "chart_spec": res.chart_spec or {},
            "chart_override": chart_override,
            "chart_title": chart_title,
            "source_question": question,
        })

    st.rerun()