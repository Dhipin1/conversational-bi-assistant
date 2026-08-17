import pandas as pd
import plotly.express as px

CHART_TYPES = ["auto", "bar", "barh", "line", "area", "scatter", "pie", "donut"]


def kpi_values(df: pd.DataFrame):
    kpis = {}
    if df is None or df.empty:
        return kpis

    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().any():
            kpis[str(c)] = float(s.sum()) if len(df) > 1 else float(s.iloc[0])
            break

    kpis["Rows"] = int(len(df))
    return kpis


def _is_numeric_col(df: pd.DataFrame, col: str) -> bool:
    s = pd.to_numeric(df[col], errors="coerce")
    return s.notna().any()


def _is_time_col(df: pd.DataFrame, col: str) -> bool:
    name = str(col).lower()
    if any(k in name for k in ["date", "month", "year", "time", "period"]):
        return True
    # also try parsing values to datetime
    try:
        dt = pd.to_datetime(df[col], errors="coerce")
        return dt.notna().mean() >= 0.6
    except Exception:
        return False


def _suggest_xy(df: pd.DataFrame):
    if df is None or df.empty or len(df.columns) < 2:
        return None, None

    cols = df.columns.tolist()

    # prefer time-like column as x
    for c in cols:
        if _is_time_col(df, c):
            x = c
            y = next((cc for cc in cols if cc != x and _is_numeric_col(df, cc)), None)
            if y:
                return x, y

    # else prefer first non-numeric as x and first numeric as y
    non_num = [c for c in cols if not _is_numeric_col(df, c)]
    num = [c for c in cols if _is_numeric_col(df, c)]
    x = non_num[0] if non_num else cols[0]
    y = num[0] if num else (cols[1] if len(cols) > 1 else None)
    return x, y


def render_chart(df: pd.DataFrame, chart_type: str, x: str | None, y: str | None, title: str = "Chart"):
    if df is None or df.empty:
        return None

    chart_type = (chart_type or "bar").lower()
    cols = df.columns.tolist()

    if x not in cols:
        x = None
    if y not in cols:
        y = None

    if x is None or (chart_type not in {"pie", "donut"} and y is None):
        x2, y2 = _suggest_xy(df)
        x = x or x2
        y = y or y2

    if x is None:
        return None

    if chart_type == "bar":
        fig = px.bar(df, x=x, y=y, title=title)
    elif chart_type == "barh":
        fig = px.bar(df, x=y, y=x, orientation="h", title=title)
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, markers=True, title=title)
    elif chart_type == "area":
        fig = px.area(df, x=x, y=y, title=title)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, title=title)
    elif chart_type == "pie":
        fig = px.pie(df, names=x, values=y, title=title, hole=0.0)
    elif chart_type == "donut":
        fig = px.pie(df, names=x, values=y, title=title, hole=0.4)
    else:
        return None

    fig.update_layout(template="plotly_white")
    return fig


def auto_chart(df: pd.DataFrame, title: str = "Chart"):
    """
    Deterministic fallback chart chooser:
    - time-series -> line
    - small categories -> pie
    - otherwise -> bar
    """
    if df is None or df.empty or len(df.columns) < 2:
        return None

    x, y = _suggest_xy(df)
    if not x or not y:
        return None

    # time-series -> line
    if _is_time_col(df, x) and _is_numeric_col(df, y):
        return render_chart(df, "line", x, y, title)

    # pie if small category set
    if len(df) <= 8 and (not _is_numeric_col(df, x)) and _is_numeric_col(df, y):
        return render_chart(df, "donut", x, y, title)

    # default -> bar
    return render_chart(df, "bar", x, y, title)


def chart_from_spec(df: pd.DataFrame, spec: dict):
    """
    Uses LLM chart spec when possible; falls back to rule-based auto_chart.
    """
    if df is None or df.empty:
        return None

    if not isinstance(spec, dict) or not spec:
        return auto_chart(df, "Result")

    chart_type = (spec.get("chart_type") or "table").lower()
    x = spec.get("x")
    y = spec.get("y")
    title = spec.get("title") or "Result"

    if chart_type in {"table", "kpi", "none"}:
        # fallback instead of None
        return auto_chart(df, title)

    fig = render_chart(df, chart_type, x, y, title=title)
    if fig is None:
        # fallback if spec columns don't match
        fig = auto_chart(df, title)

    return fig


def fig_to_png_bytes(fig) -> bytes:
    return fig.to_image(format="png", scale=2)


def fig_to_html(fig) -> str:
    return fig.to_html(include_plotlyjs="cdn")