import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.title("Query History")

p = Path("logs/queries.jsonl")
if not p.exists():
    st.info("No logs yet. Run some queries first.")
    st.stop()

rows = []
for line in p.read_text(encoding="utf-8").splitlines():
    if line.strip():
        rows.append(json.loads(line))

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="queries.csv",
    mime="text/csv"
)