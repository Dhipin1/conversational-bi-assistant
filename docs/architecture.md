# Architecture (Conversational BI Assistant)

## Overview
This project is a Conversational BI (Business Intelligence) Assistant that allows users to query a SQL database using natural language. It generates safe read-only SQL, executes it, and returns results as both tables and visualizations. It also supports multi-turn follow-up questions using conversation context.

## High-level System Flow
1. User logs in (role-based access)
2. User asks a question in natural language
3. System retrieves relevant schema + semantic context (RAG-style)
4. LLM generates SQL (SQLite dialect)
5. Safety layer validates the SQL (read-only SELECT + LIMIT)
6. RBAC policy validates tables/columns allowed for the user role
7. SQL is executed on the Northwind SQLite database
8. If execution fails, a self-correction loop repairs SQL using DB error feedback
9. Results are displayed as:
   - natural-language summary
   - SQL (transparent)
   - table output
   - chart/graph output
10. Logs are stored for query history and evaluation

## Main Components

### A) Frontend (Streamlit)
- Pages:
  - Login
  - Chat BI Assistant
  - Query History
  - Admin Settings
- Chat interface for user questions and multi-turn follow-ups
- Visualization customization:
  - chart type
  - axis selection
  - sorting
  - Top-N filtering
  - date filtering (when applicable)
- Export:
  - results CSV
  - chart image (PNG)
  - chart HTML

### B) Core BI Pipeline
- Context-aware memory: uses conversation history to handle follow-up queries
- Ambiguity handling: asks clarification when the question is incomplete (e.g., "top customers")
- Schema grounding:
  - uses live database schema and sample rows to reduce hallucinations
- Semantic layer:
  - metrics definitions (e.g., revenue formula)
  - business glossary (meaning of “sales”, “top”, “recent”)
- SQL generation: Ollama LLM generates SQL from the natural language request
- Safety layer:
  - allows only SELECT statements
  - blocks DDL/DML (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE)
  - enforces LIMIT and role-based maximum rows
- SQL rewrite:
  - fixes table name variants (e.g., "OrderDetails" vs "Order Details")
  - fixes column qualifiers after rewrite
- Execution + self-correction:
  - runs SQL
  - if error occurs, re-prompts the LLM with the DB error and retries

### C) Database
- Northwind SQLite database (`db/northwind.db`)
- Query execution via SQLAlchemy + Pandas

### D) Observability & Logs
- Query logs stored in `logs/queries.jsonl`
- Favorites stored in `logs/favorites.json`
- Used by Query History page and evaluation scripts

## Diagram (Text)
User
  → Streamlit UI (Chat + Dashboard)
    → Auth / RBAC
      → Pipeline (Memory + Ambiguity Handling)
        → Context Retrieval (Schema + Semantic Layer)
          → Ollama LLM (SQL Generation)
            → SQL Safety + Limit + RBAC checks
              → SQLite Northwind DB Execution
                → Self-Correction (if needed)
                  → Results (DF)
                    → Summary + Plotly Visualization + Export
                      → Logs (History/Evaluation)