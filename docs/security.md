# Security & Governance

## Goals
The system must allow natural-language analytics while preventing:
- unauthorized data access
- unsafe SQL execution
- accidental database modification
- leakage of sensitive/PII-like fields

## 1) Authentication
- Access is gated behind a login page.
- Session state stores the authenticated user and role.

## 2) Role-Based Access Control (RBAC)
Each user role enforces:
- maximum LIMIT (row cap) to prevent heavy queries
- optional blocked tables
- optional blocked columns (PII governance)

Example:
- executive: LIMIT <= 300
- analyst: LIMIT <= 1000
- admin: LIMIT <= 2000

## 3) SQL Safety Layer
The pipeline validates SQL before execution:
- only SELECT allowed
- disallows INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/etc.
- single-statement enforcement
- LIMIT enforced (default + max cap)

This prevents DDL/DML attacks and accidental writes.

## 4) Safe Execution
- SQL runs through SQLAlchemy and returns results as a DataFrame.
- Any DB execution errors are caught and handled.

## 5) Logging & Audit
- The system logs:
  - question
  - generated SQL
  - role
  - success/failure
  - error message
  - response time
  - retries
- Stored in `logs/queries.jsonl` for traceability.

## Notes (Academic vs Production)
This academic system demonstrates governance at the application level.
In production, stronger controls should be used:
- database views
- row-level security (RLS)
- column masking
- SSO authentication
- secrets management