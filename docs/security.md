# Security

This project includes practical security controls for a demo-scale conversational BI assistant. It focuses on preventing unsafe SQL execution and limiting access by user role.

---

## 1) Secrets Management
### What to do
- Never commit `.env` to GitHub.
- Keep secrets in deployment platform environment variables:
  - `GROQ_API_KEY`
  - `ADMIN_PASSWORD`
  - `DEMO_PASSWORD`
- `.env.example` should contain keys with empty values (template only).

### Why it matters
- Prevents API key leakage (GitHub push protection will block exposed secrets).
- Enables safe rotation of keys without code changes.

---

## 2) Authentication (Demo Scope)
- This project uses simple username/password authentication for demonstration.
- Recommended for public demo:
  - expose only a non-admin demo user (e.g., `demo/demo123`)
  - keep admin password private (set via env var)
- Do not display admin credentials on the login page UI.

> Production recommendation: use OAuth/SSO (Google/Microsoft), MFA, and audit logging.

---

## 3) Role-Based Access Control (RBAC)
- Roles: admin / analyst / exec
- Enforced constraints:
  - max row limits per role
  - optional blocked tables/columns
- Admin-only pages should be protected with role checks (server-side guard).

---

## 4) SQL Safety Layer (Critical Control)
The assistant must never execute destructive queries.

Controls:
- Allow only read-only SQL: `SELECT` (and optionally `WITH ... SELECT`)
- Block DDL/DML keywords:
  - INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA, ATTACH/DETACH, VACUUM, etc.
- Enforce single statement
- Enforce LIMIT to reduce data leakage and load

Outcome:
- Even if an LLM is prompted to “delete all rows”, execution is blocked.

---

## 5) Prompt Injection / Jailbreak Resistance
- User messages are treated as untrusted input.
- Safety checks occur after LLM output generation and before execution.
- Schema grounding reduces hallucination risk.

---

## 6) Logging & Privacy
- Logs store questions + generated SQL + success/failure for debugging and evaluation.
- Avoid storing sensitive information in logs in real deployments.
- On free hosting, logs may reset due to ephemeral disk; production should use persistent storage.

---

## 7) Production Hardening (Future)
If deploying to real business data:
- Use database-native roles/permissions
- Apply row-level security (RLS) or masking
- Add rate limiting / abuse detection
- Add allowlist-based table access for each role
- Add monitoring/alerting for unusual query patterns