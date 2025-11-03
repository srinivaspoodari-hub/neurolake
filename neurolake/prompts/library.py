"""
Prompt Library

Pre-built prompts for common NeuroLake tasks.
"""

from neurolake.prompts.template import PromptTemplate


def create_intent_parser_prompt() -> PromptTemplate:
    """
    Create intent parsing prompt template.

    Parses natural language queries to determine user intent.
    """
    template = PromptTemplate(
        name="intent_parser",
        description="Parse user intent from natural language queries"
    )

    template.add_version(
        version="v1.0",
        template="""You are an intent parser for a data analytics system.

Given a user's natural language query, classify it into one of these intents:

**Query Intents:**
- SELECT: Retrieve data (e.g., "show me users", "get sales data")
- AGGREGATE: Compute aggregations (e.g., "total revenue", "count users")
- FILTER: Filter with conditions (e.g., "users where age > 25")
- JOIN: Combine tables (e.g., "users with their orders")
- TIME_SERIES: Time-based analysis (e.g., "sales over time")

**Management Intents:**
- CREATE_TABLE: Create new table
- DELETE: Remove data
- UPDATE: Modify data
- SCHEMA: View schema/structure

**Analysis Intents:**
- EXPLAIN: Explain data/patterns
- SUMMARIZE: Summarize data
- TREND: Find trends
- ANOMALY: Detect anomalies

User Query: "$user_query"

Respond in JSON format:
{
  "intent": "<intent_type>",
  "confidence": <0.0-1.0>,
  "entities": {
    "table": "<table_name>",
    "columns": ["<column1>", "<column2>"],
    "conditions": ["<condition1>"],
    "aggregations": ["<agg1>"]
  },
  "reasoning": "<brief explanation>"
}""",
        variables=["user_query"],
        description="Intent parsing with entity extraction"
    )

    return template


def create_sql_generation_prompt() -> PromptTemplate:
    """
    Create SQL generation prompt template.

    Generates SQL queries from natural language.
    """
    template = PromptTemplate(
        name="sql_generator",
        description="Generate SQL from natural language"
    )

    template.add_version(
        version="v1.0",
        template="""You are a SQL query generator for NeuroLake data platform.

**Database Schema:**
$schema

**User Query:**
"$user_query"

**Intent Analysis:**
$intent

**Instructions:**
1. Generate a valid SQL query based on the user's request
2. Use proper table and column names from the schema
3. Add appropriate WHERE clauses for filters
4. Use JOINs when combining tables
5. Include aggregations (COUNT, SUM, AVG) when needed
6. Add GROUP BY for aggregations
7. Use ORDER BY for sorting
8. Add LIMIT for large results

**Output Format:**
```sql
<your SQL query here>
```

**Explanation:**
<Brief explanation of what the query does>

Generate the SQL query now:""",
        variables=["schema", "user_query", "intent"],
        description="SQL generation with schema context"
    )

    template.add_version(
        version="v1.1",
        template="""You are an expert SQL query generator for NeuroLake.

**Available Tables and Columns:**
$schema

**User Request:**
"$user_query"

**Detected Intent:**
$intent

**Task:**
Generate an optimized SQL query that:
- Retrieves exactly what the user needs
- Uses appropriate indexes (if available)
- Minimizes data transfer
- Includes helpful comments

**Previous Queries (for context):**
$query_history

**Response Format:**
```sql
-- Query: $user_query
-- Generated: {timestamp}

<SQL query>
```

**Query Explanation:**
<Explain the query logic>

**Performance Notes:**
<Any optimization notes>

Generate the query:""",
        variables=["schema", "user_query", "intent", "query_history"],
        description="Enhanced SQL generation with optimization hints",
        metadata={"version_improvements": "Added query history and performance notes"}
    )

    return template


def create_optimization_prompt() -> PromptTemplate:
    """
    Create query optimization prompt template.

    Suggests optimizations for SQL queries.
    """
    template = PromptTemplate(
        name="query_optimizer",
        description="Suggest optimizations for SQL queries"
    )

    template.add_version(
        version="v1.0",
        template="""You are a query optimization expert for NeuroLake.

**Original Query:**
```sql
$query
```

**Query Execution Plan:**
$execution_plan

**Performance Metrics:**
- Execution time: $execution_time ms
- Rows scanned: $rows_scanned
- Rows returned: $rows_returned
- Memory used: $memory_used MB

**Task:**
Analyze the query and suggest optimizations.

**Focus Areas:**
1. Index usage - Are appropriate indexes being used?
2. Join order - Is the join order optimal?
3. Filter pushdown - Can filters be applied earlier?
4. Unnecessary columns - Are we selecting too many columns?
5. Aggregation efficiency - Can aggregations be optimized?

**Response Format:**
{
  "optimizations": [
    {
      "type": "<optimization_type>",
      "current": "<current approach>",
      "suggested": "<suggested approach>",
      "impact": "<low|medium|high>",
      "explanation": "<why this helps>"
    }
  ],
  "optimized_query": "<SQL>",
  "expected_improvement": "<percentage>",
  "reasoning": "<overall analysis>"
}

Provide your analysis:""",
        variables=[
            "query", "execution_plan", "execution_time",
            "rows_scanned", "rows_returned", "memory_used"
        ],
        description="Query optimization with execution plan analysis"
    )

    return template


def create_error_diagnosis_prompt() -> PromptTemplate:
    """
    Create error diagnosis prompt template.

    Diagnoses and fixes SQL errors.
    """
    template = PromptTemplate(
        name="error_diagnostician",
        description="Diagnose and fix SQL query errors"
    )

    template.add_version(
        version="v1.0",
        template="""You are a SQL error diagnosis expert.

**Failed Query:**
```sql
$query
```

**Error Message:**
```
$error_message
```

**Database Schema:**
$schema

**Task:**
1. Identify the root cause of the error
2. Explain what went wrong in simple terms
3. Provide a corrected query
4. Suggest how to avoid this error in the future

**Response Format:**
{
  "error_type": "<syntax|semantic|runtime|permission>",
  "root_cause": "<what caused the error>",
  "explanation": "<user-friendly explanation>",
  "corrected_query": "<fixed SQL>",
  "prevention_tips": [
    "<tip1>",
    "<tip2>"
  ]
}

Diagnose the error:""",
        variables=["query", "error_message", "schema"],
        description="SQL error diagnosis and correction"
    )

    return template


def create_summarization_prompt() -> PromptTemplate:
    """
    Create data summarization prompt template.

    Generates natural language summaries of query results.
    """
    template = PromptTemplate(
        name="data_summarizer",
        description="Generate natural language summaries of data"
    )

    template.add_version(
        version="v1.0",
        template="""You are a data analyst creating insights from query results.

**User Query:**
"$user_query"

**SQL Query:**
```sql
$sql_query
```

**Query Results:**
$results

**Task:**
Create a clear, concise summary of the results for a non-technical user.

**Guidelines:**
1. Start with the key finding
2. Include specific numbers and percentages
3. Highlight interesting patterns or outliers
4. Keep it under 3-4 sentences
5. Use natural language, not technical jargon

**Summary:**""",
        variables=["user_query", "sql_query", "results"],
        description="Natural language data summarization"
    )

    template.add_version(
        version="v1.1",
        template="""You are a data storyteller creating insights.

**Original Question:**
"$user_query"

**Data Retrieved:**
$results

**Context:**
$context

**Create a Summary:**

**Key Findings:**
- <Main insight with numbers>
- <Secondary insight>

**Notable Patterns:**
- <Pattern 1>
- <Pattern 2>

**Recommendation:**
<What action should be taken based on this data?>

Keep it clear and actionable:""",
        variables=["user_query", "results", "context"],
        description="Enhanced summarization with recommendations",
        metadata={"improvements": "Added patterns and recommendations"}
    )

    return template


def create_schema_explainer_prompt() -> PromptTemplate:
    """
    Create schema explanation prompt template.

    Explains database schema in natural language.
    """
    template = PromptTemplate(
        name="schema_explainer",
        description="Explain database schema in natural language"
    )

    template.add_version(
        version="v1.0",
        template="""You are a database schema documentation expert.

**Schema:**
$schema

**Task:**
Explain this database schema in clear, non-technical language.

**Include:**
1. What each table represents
2. Key columns and their purpose
3. Relationships between tables
4. Common use cases

**Format:**
**Table: `$table_name`**
- Purpose: <what this table stores>
- Key columns:
  - `column1`: <description>
  - `column2`: <description>
- Relationships: <links to other tables>
- Use cases: <when to query this table>

Provide the explanation:""",
        variables=["schema"],
        description="Schema explanation for non-technical users"
    )

    return template


__all__ = [
    "create_intent_parser_prompt",
    "create_sql_generation_prompt",
    "create_optimization_prompt",
    "create_error_diagnosis_prompt",
    "create_summarization_prompt",
    "create_schema_explainer_prompt",
]
