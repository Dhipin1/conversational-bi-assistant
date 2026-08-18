# Architecture — Conversational BI Assistant (Advanced)

## Overview
This project is a Conversational BI (Business Intelligence) Assistant that lets users query a SQL database using natural language. It generates **read-only safe SQL**, validates it using a **safety layer + RBAC**, executes it, and returns:
- an answer summary
- generated SQL (transparency)
- a result table
- interactive visualizations

It supports multi-turn follow-ups using conversation context and includes query history/favorites for BI workflows.

---

## High-level System Flow
1. User logs in (role-based access)
2. User asks a BI question in natural language
3. System resolves ambiguity (may ask clarification)
4. System retrieves relevant schema + semantic context (RAG-style)
5. LLM generates SQL (SQLite dialect)
6. SQL is normalized/cleaned and corrected for schema/table-name variants
7. Safety layer validates SQL (read-only SELECT / single statement / limit)
8. RBAC validates allowed tables/columns and maximum rows per role
9. SQL executes against Northwind SQLite database
10. If SQL fails, a self-correction loop retries using DB error feedback
11. Results are displayed as:
   - natural-language summary
   - SQL (transparent)
   - data table
   - chart/graph
12. Logs are stored for query history and evaluation

---

## Main Components

### A) Frontend (Streamlit)
- Multi-page Streamlit app:
  - Home
  - Login
  - Chat BI Assistant
  - Query History
  - Admin Settings (admin only)
- Chat interface:
  - multi-turn conversation
  - shows generated SQL + results + visualization
- Visualization customization (UI controls may vary by page):
  - chart type
  - axis selection
  - sorting
  - Top-N filtering
- Export:
  - results CSV
  - chart HTML
  - chart PNG (requires Kaleido + Chromium in Docker)

### B) Auth + RBAC
- Authentication via username/password (demo-style)
- Role attached to the session (`admin`, `analyst`, `exec`)
- RBAC policies enforce:
  - per-role max row limits
  - optional table/column access control
- Admin Settings page should be blocked for non-admin roles.

### C) Core BI Pipeline
- Memory/context: uses conversation history to handle follow-up questions
- Ambiguity handling: asks clarification when question is underspecified
- Schema grounding:
  - reads actual DB schema
  - retrieves relevant schema snippets
- Semantic layer:
  - business definitions/metrics (e.g., revenue formula)
  - naming conventions (sales/revenue/orders)
- SQL generation:
  - LLM provider is configurable:
    - **Groq (cloud)** recommended for public demo deployment
    - Ollama (local) supported for private/local runs
- Safety layer:
  - allows only read-only `SELECT` / `WITH ... SELECT`
  - blocks DDL/DML (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA/etc.)
  - enforces LIMIT and role-based maximum rows
- SQL rewrite:
  - fixes common schema variants
  - normalizes table/column qualifiers
- Execution + self-correction:
  - executes SQL using SQLAlchemy/Pandas
  - if execution fails, retries with corrected SQL (configurable retries)

### D) Database
- Northwind SQLite database (`db/northwind.db`)
- Query execution via SQLAlchemy + Pandas

### E) Observability & Logs
- Query logs stored in `logs/queries.jsonl`
- Favorites stored in `logs/favorites.json`
- Used by Query History page and evaluation scripts

> Note: On some free deployments (e.g., Render free), filesystem can be ephemeral on restarts/redeploys, so logs/history may reset.

---

## Deployment Architecture
### Public Demo (Recommended)
- **Render (Docker)** hosts Streamlit app
- **Groq API** provides the LLM (cloud)
- Secrets (API keys, passwords) stored as **Render Environment Variables**

### Local/Private Mode
- Streamlit app runs locally
- Optional: **Ollama** runs locally as the LLM provider

---

## Diagram (Text)
User
  → Streamlit UI (Chat + Dashboard)
    → Auth / RBAC
      → Pipeline (Memory + Ambiguity Handling)
        → Context Retrieval (Schema + Semantic Layer)
          → LLM Provider (Groq / Ollama / OpenAI)
            → SQL Normalization + Safety + Limit + RBAC checks
              → SQLite Northwind DB Execution
                → Self-Correction (if needed)
                  → Results (DataFrame)
                    → Summary + Plotly Visualization + Export
                      → Logs (History/Evaluation)