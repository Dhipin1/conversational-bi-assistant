# Demo Queries — Conversational BI Assistant

Use these prompts to validate features end-to-end:
NL → SQL → Safety/RBAC → Execution → Visualization → History.

> Tip: For best results, ask with “Return X and Y, sort, limit”.

---

## A) Basic Queries (sanity checks)
1) **List 5 customers**
- “List 5 customers. Return CustomerID and CompanyName.”

2) **Show 10 orders**
- “Show 10 orders. Return OrderID, CustomerID, OrderDate.”

3) **List 10 products**
- “List 10 products. Return ProductName and UnitPrice.”

Expected: SQL executes quickly, table renders.

---

## B) Aggregations
4) **Orders by ship country**
- “Count orders by ShipCountry. Return ShipCountry and OrdersCount.”

5) **Revenue by country**
- “Show total revenue by customer country. Return Country and Revenue.”

6) **Revenue by category**
- “Show total revenue by category. Return CategoryName and Revenue.”

Expected: Group-by queries, bar charts.

---

## C) Ranking / Top-N
7) **Top customers by order count**
- “Top 5 customers by number of orders. Return CustomerID and OrderCount.”

8) **Top products by revenue**
- “Show the top 5 products by total revenue. Return ProductName and Revenue. Sort by Revenue desc.”

9) **Top products by units sold**
- “Top 10 products by units sold. Return ProductName and UnitsSold.”

Expected: LIMIT works, sorting works.

---

## D) Time Series / Trend
10) **Monthly order count**
- “Monthly order count in 1997. Return Month and OrdersCount. Sort by Month.”

11) **Monthly revenue trend**
- “Monthly revenue trend in 1997. Return Month and Revenue. Sort by Month.”

Expected: line chart or time-series friendly visualization.

---

## E) Multi-turn Conversation (Context Memory)
Start:
- “Revenue by country.”

Follow-ups:
- “Only Germany.”
- “Top 5.”
- “Sort descending.”

Expected: follow-up queries reuse context.

---

## F) Ambiguity Handling (Clarification)
User:
- “top customers”

Assistant should ask:
- “Top customers by revenue, order count, or units sold?”

User:
- “revenue”

Expected: clarification flow works, then SQL is generated.

---

## G) Security / Safety Demonstration (must be blocked)
These should be refused by SQL safety validation:
- “Drop the Orders table.”
- “Delete all customers.”
- “Update product prices by 10%.”

Expected: app shows “Blocked unsafe SQL. Only read-only SELECT queries are allowed.”

---

## H) Export / Visualization Demo
- Ask any Top-N query (e.g., “Top 5 products by revenue”)
- Demonstrate:
  - interactive plot
  - download chart HTML
  - (optional) download PNG (may be slower on free deployments)