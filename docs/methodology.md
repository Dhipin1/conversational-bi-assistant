# Methodology — Conversational BI Workflow

This project follows an agent-like Conversational BI workflow inspired by modern NL-to-SQL and conversational analytics systems.

---

## Step 1: User Access (Authentication + Roles)
- Users log in using credentials.
- Each user has a role (admin / analyst / exec).
- Role is used to enforce governance:
  - max returned rows
  - access restrictions for tables/columns
- Demo deployments should avoid exposing admin passwords in the UI.

---

## Step 2: Conversational Dashboard (Streamlit)
- User interacts through a Streamlit chat interface.
- System displays:
  - answer summary
  - generated SQL (transparency)
  - result table
  - chart/graph
- Supports follow-up questions (multi-turn).

---

## Step 3: Context-Aware Memory (Multi-turn)
- Recent conversation turns are included in prompts.
- Follow-up queries use previous context.
  Example:
  - “Revenue by country”
  - “Only Germany”
  - “Top 5”

---

## Step 4: Enhanced Schema Understanding (Grounding)
- Retrieves relevant schema snippets to reduce hallucinations:
  - table/column names
  - relationships
- Uses a semantic layer (metrics definitions / business glossary) to stabilize meaning.

---

## Step 5: Natural Language → SQL (LLM)
- Provider is configurable by environment variables:
  - **Groq**: recommended for public demos (fast, hosted)
  - **Ollama**: local/private mode
  - OpenAI optional fallback
- Prompts include:
  - schema snippets
  - semantic definitions
  - conversation history
  - limit rules (default + role max)

---

## Step 6: SQL Safety + Governance
- SQL Safety:
  - only read-only SELECT allowed (or WITH ... SELECT)
  - blocks DDL/DML keywords
  - enforces LIMIT
  - denies multiple statements
- RBAC:
  - role-based max rows
  - optional blocked tables/columns for governance

---

## Step 7: Execution + Self-Correction
- SQL executes against SQLite (Northwind).
- On error:
  - DB error message is used to re-prompt the model
  - the model attempts to fix SQL
  - retry count is configurable (`MAX_FIX_RETRIES`)

---

## Step 8: Visualization + Reporting
- Results visualized using Plotly.
- Chart selection uses:
  - rule-based heuristics for simple result shapes
  - optional LLM-based chart spec for more complex results
- Export:
  - CSV results
  - chart HTML
  - chart PNG (requires Chromium/Kaleido; slower on small servers)

---

## Step 9: Logging and Evaluation
- Logs written to JSONL for history/evaluation.
- Evaluation suite can measure:
  - execution success rate
  - latency per stage
  - self-correction usage and success