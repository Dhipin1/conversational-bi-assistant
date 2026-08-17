# Methodology

This project follows an agent-like Conversational BI workflow inspired by modern NL-to-SQL and conversational analytics systems.

## Step 1: User Access (Authentication + Roles)
- Users login using credentials.
- Each user has a role (admin / analyst / executive).
- Role is used to enforce governance rules like max returned rows and access restrictions.

## Step 2: Conversational Dashboard
- User interacts through a Streamlit chat interface.
- System displays:
  - answer summary
  - generated SQL (transparency)
  - results table
  - chart/graph
- Supports follow-up questions (multi-turn).

## Step 3: Context-Aware Memory (Multi-turn Conversation)
- Conversation history is included in prompts.
- Follow-up queries are resolved using previous context.
  Example:
  - “Revenue by country”
  - “Only Germany”
  - “Top 5”

## Step 4: Enhanced Schema Understanding (Grounding)
- System retrieves:
  - relevant table schemas
  - sample rows (to reduce incorrect column mapping)
- Uses a semantic layer (YAML) for business meaning.

## Step 5: Natural Language → SQL (LLM)
- Ollama local model generates SQLite SQL.
- Prompts include:
  - schema snippets
  - semantic metrics definitions
  - conversation history

## Step 6: Safety + Governance
- SQL Safety:
  - only read-only SELECT allowed
  - blocks DDL/DML keywords
  - ensures single statement
  - enforces LIMIT
- RBAC:
  - role-based max rows
  - optional blocked tables/columns (PII governance)

## Step 7: Execution + Self-Correction
- SQL executes against SQLite.
- If execution fails:
  - database error message is used to re-prompt the model
  - system retries with corrected SQL
- Improves robustness.

## Step 8: Visualization + Reporting
- System generates charts using Plotly.
- Chart selection:
  - automatic (from model spec)
  - user-customizable in UI (chart type, x/y, sort, top-N)
- Export:
  - CSV result
  - chart PNG + HTML

## Step 9: Logging and Evaluation
- Logs written to JSONL file for history and evaluation.
- Golden questions dataset can be used to compute:
  - execution success rate
  - average latency
  - self-correction rate