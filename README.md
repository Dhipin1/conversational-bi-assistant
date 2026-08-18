# Conversational BI Assistant (Advanced)

A Conversational BI (Business Intelligence) assistant that turns natural-language questions into **safe, read-only SQL**, executes them on the **Northwind** database, and returns **tables + visualizations**. Includes **RBAC**, **query history**, **favorites**, and a **self-correction loop** for SQL errors.

---

## Live Demo (Public)
- **Render (Docker)**: https://conversational-bi-assistant.onrender.com  
  > Note: Render free tier may “sleep” when idle. First load can take ~30–60 seconds.

## Demo Credentials
- **Demo user**: `demo`  
- **Password**: `demo123`  
> Admin credentials are intentionally not shown publicly.

---

## Key Features
- Natural Language → SQL (SQLite)
- SQL safety layer (read-only `SELECT` / blocks DDL+DML)
- RBAC governance (role-based limits / restrictions)
- Self-correction loop (retries SQL generation using DB error feedback)
- Auto visualizations (Plotly) + basic customization
- Exports:
  - CSV results
  - Chart HTML
  - Chart PNG (uses Kaleido + Chromium inside Docker)

---

## Tech Stack
- **Frontend:** Streamlit (multi-page)
- **Database:** SQLite (Northwind)
- **LLM Providers:** Groq (recommended for public), Ollama (local), OpenAI (optional)
- **SQL Execution:** SQLAlchemy + Pandas
- **Visualization:** Plotly (+ Kaleido for PNG export)
- **Deployment:** Docker + Render

---

## Project Structure (high-level)
- `app/` — Streamlit pages (Home/Login/Chat/History/Admin)
- `core/` — pipeline (retrieval, prompts, safety, correction)
- `auth/` — authentication + RBAC
- `db/` — `northwind.db`
- `docs/` — architecture, methodology, security, demo queries, limitations
- `logs/` — query history / favorites (may reset on free hosting)

---

## Run Locally (Recommended: Groq)
### 1) Create venv + install deps
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt