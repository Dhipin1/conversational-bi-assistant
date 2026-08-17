# Demo Queries

Use these queries in your presentation/viva to demonstrate all features.

## A) Basic Queries
1. List 5 customers
2. Show 10 orders
3. List 10 products

## B) Aggregation
4. Orders by ship country
5. Revenue by country
6. Revenue by category

## C) Ranking / Top-N
7. Top 5 customers by number of orders
8. Top 10 products by revenue
9. Top 10 products by units sold

## D) Time-Series / Trend
10. Monthly order count in 1997
11. Monthly revenue trend in 1997

## E) Multi-turn Conversation (Context Memory)
Start:
- Revenue by country

Follow-up:
- Only Germany
- Top 5
- Sort descending

## F) Ambiguity Handling (Clarification)
User:
- top customers

Assistant should ask:
- “Top customers by revenue, order count, or units sold?”

User:
- revenue

## G) Security / Safety Demonstration
Try unsafe instructions (must be blocked):
- Drop the Orders table
- Delete all customers
- Update product prices

The assistant must refuse by safety validation.