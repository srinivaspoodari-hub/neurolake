# Natural Language Query Guide

## Introduction

NeuroLake allows you to query your data using natural language instead of SQL. Just ask questions in plain English, and the system will understand what you want and retrieve the data.

## Quick Examples

```python
from neurolake.intent import IntentParser

parser = IntentParser()

# Simple queries
parser.parse("Show me all users")
parser.parse("Get all products")
parser.parse("List customers")

# Filtered queries
parser.parse("Show users where age > 25")
parser.parse("Get products with price > 100")
parser.parse("List active customers")

# Aggregations
parser.parse("Count all users")
parser.parse("Sum of sales")
parser.parse("Average age of customers")

# Analysis
parser.parse("Explain why sales dropped")
parser.parse("Show me the trend")
parser.parse("Compare Q1 vs Q2")
```

## Supported Query Types

### 1. Simple Selection

**Get all data from a table:**
- "Show me all users"
- "Get all products"
- "List customers"
- "Display orders"
- "Retrieve all transactions"

**What it does:**
- Retrieves all records from the specified table
- Similar to `SELECT * FROM table`

### 2. Filtered Queries

**Get specific records based on conditions:**
- "Show users where age > 25"
- "Get products with price > 100"
- "List customers having active status"
- "Display orders from last month"
- "Show users with name like 'John'"

**What it does:**
- Filters data based on your conditions
- Similar to `SELECT * FROM table WHERE condition`

**Supported operators:**
- Greater than: `>`, `greater than`, `above`, `more than`
- Less than: `<`, `less than`, `below`, `fewer than`
- Equal: `=`, `equals`, `is`, `are`
- Not equal: `!=`, `not equal`, `isn't`, `aren't`

### 3. Aggregations

**Calculate statistics:**
- "Count all users"
- "Total number of orders"
- "Sum of sales"
- "Average age of customers"
- "Maximum price"
- "Minimum temperature"

**What it does:**
- Performs calculations across multiple records
- Similar to `SELECT COUNT(*), SUM(column), AVG(column) FROM table`

**Supported aggregations:**
- **Count**: "count", "total number", "how many"
- **Sum**: "sum", "total", "add up"
- **Average**: "average", "avg", "mean"
- **Maximum**: "max", "maximum", "highest", "largest"
- **Minimum**: "min", "minimum", "lowest", "smallest"

### 4. Joins

**Combine data from multiple tables:**
- "Show users with their orders"
- "Get customers and their purchases"
- "List products along with their categories"
- "Display users and their addresses"

**What it does:**
- Combines related data from multiple tables
- Similar to `SELECT * FROM table1 JOIN table2 ON ...`

### 5. Time Series

**Analyze data over time:**
- "Sales over time"
- "Users by date"
- "Revenue timeline"
- "Activity by month"

**What it does:**
- Retrieves data organized by time periods
- Useful for tracking changes and trends

### 6. Sorting

**Order your results:**
- "Show users sorted by age"
- "List products ordered by price"
- "Display customers by name"
- "Get orders from newest to oldest"

**What it does:**
- Sorts results in ascending or descending order
- Similar to `SELECT * FROM table ORDER BY column`

### 7. Limiting Results

**Get top N records:**
- "Show me top 10 users"
- "Get first 5 products"
- "List 20 most recent orders"
- "Display latest 100 transactions"

**What it does:**
- Limits the number of results returned
- Similar to `SELECT * FROM table LIMIT N`

## Advanced Queries

### Combining Multiple Operations

You can combine filtering, aggregation, sorting, and limiting:

**Examples:**
- "Show me top 10 users where age > 25 sorted by name"
- "Count active customers by city"
- "Average price of products with rating > 4"
- "Total sales from last month by region"

**What it does:**
- Creates a pipeline of operations
- Executes them in the correct order: JOIN → FILTER → AGGREGATE → SORT → LIMIT

### Comparisons

**Compare different groups or time periods:**
- "Compare sales vs revenue"
- "Q1 vs Q2 performance"
- "Difference between active and inactive users"
- "This month vs last month"

### Trend Analysis

**Identify patterns:**
- "Show me the trend in sales"
- "What's the pattern in user signups?"
- "Revenue trend over time"
- "Growth rate by quarter"

### Explanations

**Ask why something happened:**
- "Explain why sales dropped"
- "Why did revenue increase?"
- "What caused the spike in orders?"
- "How did this happen?"

### Summaries

**Get high-level overviews:**
- "Summarize quarterly results"
- "Give me a summary of user activity"
- "Overview of sales performance"
- "Summarize the data"

## Natural Language Tips

### 1. Be Specific About Tables

**Good:**
- "Show me all **users**"
- "Count **products**"
- "Get **orders** from last week"

**Needs Clarification:**
- "Show me all data" ❌ (Which table?)
- "Count everything" ❌ (Count what?)

### 2. Use Clear Time References

**Good:**
- "Last 7 days"
- "Past month"
- "Yesterday"
- "This year"

**Vague:**
- "Recently" ⚠️ (How recent?)
- "Lately" ⚠️ (How long?)
- "Soon" ⚠️ (When?)

### 3. Specify Columns for Aggregations

**Good:**
- "Count **users**"
- "Sum of **sales amount**"
- "Average **age** of customers"

**Needs Clarification:**
- "Count all" ❌ (Count what?)
- "Sum everything" ❌ (Sum which column?)

### 4. Use Simple Language

**Good:**
- "Show users where age > 25"
- "Get active customers"
- "List products under $50"

**Too Complex:**
- "I would like to see the comprehensive dataset of all user entities that satisfy the condition where their chronological age metric exceeds the threshold value of 25" ❌

### 5. Break Complex Queries

Instead of:
- "Show me users with age > 25 and city = NYC and active status from last month sorted by name with their orders and total purchase amount" ❌

Do this:
1. "Show users where age > 25 and city = NYC"
2. "Filter for active users"
3. "From last month"
4. "Show their orders"
5. "Calculate total purchase amount"

## SQL vs Natural Language

You can use either SQL or natural language - both work!

| Natural Language | SQL Equivalent |
|-----------------|----------------|
| "Show me all users" | `SELECT * FROM users` |
| "Get users where age > 25" | `SELECT * FROM users WHERE age > 25` |
| "Count all orders" | `SELECT COUNT(*) FROM orders` |
| "Show top 10 products" | `SELECT * FROM products LIMIT 10` |
| "Average price of products" | `SELECT AVG(price) FROM products` |
| "Users and their orders" | `SELECT * FROM users JOIN orders ON ...` |

**When to use SQL:**
- You know SQL well
- Complex joins or subqueries
- Specific column selections
- Advanced filtering logic

**When to use Natural Language:**
- You're not familiar with SQL
- Quick, simple queries
- Exploratory data analysis
- Talking to data conversationally

## Conversational Queries

NeuroLake remembers context in conversations:

```python
# Turn 1
"Show me users where age > 25"

# Turn 2 - remembers we're talking about users
"Show me their names"

# Turn 3 - still remembers
"Sort by age"

# Turn 4
"Show top 10"
```

**Pronouns that work:**
- "Show **their** names" (refers to previous table/results)
- "Sort **it** by date" (refers to previous query)
- "Count **those**" (refers to previous selection)

## Handling Ambiguity

If your query is unclear, NeuroLake will ask for clarification:

**Example 1:**
```
You: "Count all"
NeuroLake: "I need some clarification:
1. Which table would you like to query?"

You: "Count all users"
NeuroLake: ✓ Executes query
```

**Example 2:**
```
You: "Show me data from recently"
NeuroLake: "I need some clarification:
1. What time period do you mean exactly? (e.g., last 7 days, past month)"

You: "Last 30 days"
NeuroLake: ✓ Executes query
```

## Common Patterns

### Pattern 1: Simple Exploration
```
1. "Show me all users"
2. "How many are there?"
3. "What's the average age?"
4. "Show me the oldest 10"
```

### Pattern 2: Filtered Analysis
```
1. "Get orders from last month"
2. "Count them"
3. "What's the total revenue?"
4. "Show top 5 customers by amount"
```

### Pattern 3: Comparative Analysis
```
1. "Show sales by month"
2. "Compare this year vs last year"
3. "What's the growth rate?"
4. "Explain why Q2 increased"
```

### Pattern 4: Multi-Table Exploration
```
1. "Show users with their orders"
2. "Filter for active users only"
3. "Count orders per user"
4. "Show users with more than 5 orders"
```

## Examples by Industry

### E-Commerce
- "Show products under $50"
- "Count orders from last week"
- "Top 10 bestselling products"
- "Average order value by customer"
- "Customers with abandoned carts"
- "Revenue trend by category"

### SaaS/Analytics
- "Active users this month"
- "Signup conversion rate"
- "Users by subscription tier"
- "Churn rate by cohort"
- "Feature usage over time"
- "Compare free vs paid users"

### Finance
- "Total transactions today"
- "Sum of deposits by account"
- "Average transaction amount"
- "Flagged transactions above $10,000"
- "Monthly revenue trend"
- "Compare Q1 vs Q2 profit"

### Healthcare
- "Count patients by age group"
- "Average wait time by department"
- "Appointments for next week"
- "Patients with condition X"
- "Medication usage trends"
- "Compare treatment outcomes"

## Troubleshooting

### "I don't understand that query"

**Problem:** Query is too ambiguous or uses unfamiliar phrasing

**Solutions:**
- Be more specific about the table name
- Use simpler language
- Try SQL syntax instead
- Break into smaller queries

### "Which table would you like to query?"

**Problem:** Table name not specified

**Solutions:**
- Include the table name: "Show users..."
- Use context from previous query
- Specify explicitly: "From the users table, show..."

### "Low confidence - please confirm"

**Problem:** Query could have multiple interpretations

**Solutions:**
- Add more details
- Use SQL for precision
- Confirm the suggested interpretation
- Rephrase more clearly

### Results are not what you expected

**Problem:** Query was interpreted differently than intended

**Solutions:**
- Check the confidence score
- Review the extracted entities (table, columns, conditions)
- Add more specific keywords
- Use SQL for complex queries

## Best Practices

1. **Start Simple**: Begin with basic queries before trying complex ones
2. **Check Understanding**: Review what was extracted before executing
3. **Use Context**: Let earlier queries inform later ones
4. **Be Specific**: Name tables, columns, and time periods clearly
5. **Iterate**: Refine queries based on results
6. **Mix SQL and NL**: Use what works best for each query
7. **Test First**: Try queries on small datasets first

## Confidence Levels

NeuroLake shows how confident it is about understanding your query:

- **High (80-100%)**: Clear query, ready to execute
  - "SELECT * FROM users"
  - "Show me all products"

- **Medium (50-80%)**: Likely correct, may want to confirm
  - "Get users older than 25"
  - "Show recent orders"

- **Low (<50%)**: Needs clarification
  - "Show me that data"
  - "Count everything from yesterday"

**Recommendation**: Execute high confidence queries directly, confirm medium confidence queries, and clarify low confidence queries.

## Learning Resources

### Start Here
1. Try simple SELECT queries
2. Add basic filters (WHERE)
3. Use aggregations (COUNT, SUM, AVG)
4. Combine operations
5. Try conversational queries

### Practice Queries

**Beginner:**
```
1. "Show me all users"
2. "Count all products"
3. "Get orders from today"
```

**Intermediate:**
```
1. "Show users where age > 25"
2. "Count active customers by city"
3. "Average price of products in stock"
```

**Advanced:**
```
1. "Top 10 customers by total purchase amount from last quarter"
2. "Compare average order value between premium and basic users"
3. "Show trending products with sales growth > 20% month over month"
```

## API Integration

```python
from neurolake.intent import IntentParser

# Initialize parser
parser = IntentParser()

# Parse query
intent = parser.parse("Show me all users")

# Check confidence
if intent.confidence > 0.8:
    print("High confidence - executing")
elif intent.needs_clarification():
    # Get clarification
    response = parser.generate_clarification_response(intent)
    print(response)
else:
    print(f"Intent: {intent.intent_type}")
    print(f"Table: {intent.get_table()}")
    print(f"Confidence: {intent.confidence:.0%}")
```

## Getting Help

If you're stuck:
1. Type "help" to see available commands
2. Ask "Show me the schema" to see table structures
3. Try SQL syntax for complex queries
4. Check the examples above for similar queries
5. Review confidence scores and clarifications

## Summary

**Key Points:**
- Natural language queries are easy and intuitive
- Be specific about tables, columns, and time periods
- NeuroLake will ask for clarification when needed
- You can use SQL or natural language interchangeably
- Context is remembered in conversations
- Check confidence scores before executing

**Common Keywords:**
- Selection: show, get, list, display, retrieve
- Filtering: where, with, having, filter
- Aggregation: count, sum, average, max, min, total
- Sorting: sort, order, sorted by, ordered by
- Limiting: top, first, limit, latest
- Time: today, yesterday, last week, past month
- Comparison: vs, versus, compare, difference between

Happy querying! 🚀
