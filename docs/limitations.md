# Limitations

## 1) LLM Accuracy (NL → SQL)
- LLMs can generate syntactically valid SQL that is **semantically incorrect** (wrong joins, wrong revenue formula, wrong grouping).
- Complex multi-join questions may still fail or require self-correction retries.
- Different models/providers may behave differently (Groq vs Ollama).

## 2) Ambiguity in Business Questions
- Terms like “top”, “best”, “recent”, “least” need clarification.
- The assistant asks clarifying questions, but may still misinterpret user intent in edge cases.

## 3) Schema Variants / Northwind Differences
- Northwind dataset variants differ:
  - “OrderDetails” vs “Order Details”
  - column naming differences
- SQL rewrite helps, but edge cases remain.

## 4) Performance (Especially on Free Hosting)
- Render Free instances may **sleep** when idle (cold start), causing first request delays (~30–60 seconds).
- CPU/RAM on free tier is limited; heavy operations (large prompts, multiple LLM calls, PNG export) may be slow.
- Increasing MAX_FIX_RETRIES improves robustness but increases latency.

## 5) Visualization & Export
- Automatic chart selection may not always match user intent.
- PNG export uses Plotly/Kaleido + Chromium and can be expensive on small servers.
  - HTML export is typically faster.

## 6) Security Scope (Demo Auth vs Production)
- Application-level RBAC helps but is not equivalent to database-native security.
- Production deployments should use:
  - SSO/OAuth
  - database roles/permissions
  - row-level security (RLS) / masking for sensitive columns
  - rate limiting and audit logging

---

## Known Limitation: Time-series simplification edge case
In rare cases where SQL self-correction simplifies a time-series query into a single aggregate (e.g., a plain COUNT with a year filter instead of GROUP BY month), the visualization layer may fall back to a KPI card instead of a line chart. The returned data can still be correct — only the chart selection is affected.

---

## Future Improvements
- Stronger semantic layer (metrics/dimensions/time-intelligence)
- Caching for repeated questions
- More visualization types (heatmaps, pivots)
- Move logs/history to Postgres for persistence on cloud deployments
- Add streaming responses / progress indicators for better UX