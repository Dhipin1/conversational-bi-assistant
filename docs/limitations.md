# Limitations

## 1) LLM Accuracy
- Local 7B/8B models may produce incorrect SQL for complex multi-join queries.
- Execution success does not guarantee semantic correctness.

## 2) Ambiguity
- Business terms like “top”, “recent”, “best” require clarification.
- System asks clarifying questions, but may still misinterpret intent.

## 3) Schema Variants
- Northwind dataset versions differ:
  - “OrderDetails” vs “Order Details”
  - column naming differences
- The project includes SQL rewriting to reduce these issues, but edge cases can remain.

## 4) Performance
- Running locally is private and free, but slower than cloud APIs.
- Large queries may be slower; LIMIT caps mitigate this.

## 5) Visualization Heuristics
- Automatic chart selection may not always match user preference.
- Manual chart customization is provided to overcome this.

## 6) Security Scope
- Application-level RBAC is helpful but not as strong as database-native controls.
- Production deployments need RLS/masking/enterprise auth.

## Future Improvements
- Fine-tune / domain-adapt LLM for higher SQL accuracy.
- Add caching for repeated questions.
- Add richer visualization types (heatmaps, pivot tables).
- Add advanced semantic layer (metrics + dimensions + time intelligence).

# Known Limitations

## Visualization edge case for simplified time-series queries

In rare cases where SQL self-correction simplifies a time-series query into a
single aggregate (e.g., a plain `COUNT` with a `WHERE year filter` instead of a
`GROUP BY month`), the visualization layer falls back to a KPI card instead of
a line chart. The underlying data returned is still correct — only the
chart type selection is affected. Observed in ~5% of evaluation cases.