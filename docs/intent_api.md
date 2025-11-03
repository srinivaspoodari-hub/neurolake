# Intent Parsing API Documentation

## Overview

The Intent module provides natural language understanding for data queries. It parses user queries (both natural language and SQL) into structured intent objects that can be executed by the query engine.

## Quick Start

```python
from neurolake.intent import IntentParser

# Create parser
parser = IntentParser()

# Parse a query
intent = parser.parse("Show me all users where age > 25")

# Check intent type
print(intent.intent_type)  # IntentType.FILTER

# Get entities
print(intent.get_table())  # "users"
print(intent.get_conditions())  # ["age > 25"]
```

## Core Classes

### IntentType

Enumeration of all supported intent types:

**Query Intents:**
- `SELECT` - Simple data retrieval
- `FILTER` - Filtered data retrieval
- `AGGREGATE` - Aggregation queries (COUNT, SUM, AVG, etc.)
- `JOIN` - Multi-table queries
- `TIME_SERIES` - Time-based queries
- `SORT` - Sorting operations
- `LIMIT` - Limited result sets

**Management Intents:**
- `CREATE_TABLE` - Table creation
- `DROP_TABLE` - Table deletion
- `UPDATE` - Data updates
- `DELETE` - Data deletion
- `INSERT` - Data insertion
- `SCHEMA` - Schema inspection

**Analysis Intents:**
- `EXPLAIN` - Explanatory analysis
- `SUMMARIZE` - Data summarization
- `TREND` - Trend analysis
- `ANOMALY` - Anomaly detection
- `COMPARE` - Comparative analysis
- `FORECAST` - Predictive analysis

**Meta Intents:**
- `HELP` - User assistance
- `UNKNOWN` - Unrecognized intent

### Intent

The core data structure representing a parsed intent.

#### Attributes

```python
@dataclass
class Intent:
    intent_type: IntentType          # Type of intent
    confidence: float                # Confidence score (0-1)
    original_query: str             # Original user query
    entities: Dict[str, Any]        # Extracted entities
    subintent: Optional[str]        # Subtype of intent
    reasoning: str                  # Parsing reasoning
    metadata: Dict[str, Any]        # Additional metadata
    ambiguous: bool                 # Is ambiguous?
    ambiguity_reasons: List[str]    # Why ambiguous
    clarification_questions: List[str]  # Questions for user
    alternative_intents: List[Dict]     # Alternative interpretations
```

#### Methods

**Query Type Checks:**
```python
intent.is_query() -> bool          # Is a data query?
intent.is_management() -> bool     # Is a management operation?
intent.is_analysis() -> bool       # Is an analysis request?
```

**Entity Extraction:**
```python
intent.get_table() -> Optional[str]        # Get table name
intent.get_columns() -> List[str]          # Get column names
intent.get_conditions() -> List[str]       # Get filter conditions
intent.get_aggregations() -> List[str]     # Get aggregation functions
intent.get_joins() -> List[Dict]           # Get join specifications
```

**Pipeline Detection:**
```python
intent.is_pipeline() -> bool               # Is a multi-stage query?
intent.get_pipeline_stages() -> List[str]  # Get pipeline stages
```

**Ambiguity Handling:**
```python
intent.is_ambiguous() -> bool              # Needs clarification?
intent.needs_clarification() -> bool       # Has clarification questions?
intent.add_clarification(question, reason) # Add clarification
intent.add_alternative(type, conf, ents)   # Add alternative
```

**Serialization:**
```python
intent.to_dict() -> Dict[str, Any]         # Convert to dictionary
```

### IntentParser

Main parser for converting queries to intents.

#### Constructor

```python
parser = IntentParser(llm_provider=None)
```

**Parameters:**
- `llm_provider` (Optional): LLM provider for advanced parsing. If not provided, uses rule-based parsing.

#### Methods

**Basic Parsing:**
```python
parser.parse(query: str) -> Intent
```
Parse a query using LLM (if available) with fallback to rules.

**Example:**
```python
intent = parser.parse("SELECT * FROM users WHERE age > 25")
```

**Rule-Based Parsing:**
```python
parser.parse_with_rules(query: str) -> Intent
```
Parse using only rule-based heuristics (no LLM).

**Context-Aware Parsing:**
```python
parser.parse_with_context(
    query: str,
    context: Optional[Dict[str, Any]] = None
) -> Intent
```
Parse with conversation context for multi-turn dialogues.

**Example:**
```python
# First query
intent1 = parser.parse("SELECT * FROM users")

# Second query uses context
context = {"previous_intent": intent1.to_dict()}
intent2 = parser.parse_with_context("Show their ages", context)
# Inherits table="users" from context
```

**Clarification Generation:**
```python
parser.generate_clarification_response(intent: Intent) -> str
```
Generate human-readable clarification message.

**Example:**
```python
intent = parser.parse("Count all")
response = parser.generate_clarification_response(intent)
# Returns: "I need some clarification:\n1. Which table would you like to query?"
```

## Usage Patterns

### Pattern 1: Simple Query Parsing

```python
from neurolake.intent import IntentParser

parser = IntentParser()
intent = parser.parse("Show me all products")

if intent.is_query():
    table = intent.get_table()
    columns = intent.get_columns()
    # Execute query...
```

### Pattern 2: Handling Ambiguity

```python
parser = IntentParser()
intent = parser.parse("Count all records")

if intent.needs_clarification():
    # Ask user for clarification
    message = parser.generate_clarification_response(intent)
    print(message)
    # Get user response...
else:
    # Execute query
    pass
```

### Pattern 3: Multi-Turn Conversation

```python
parser = IntentParser()
context = {}

# Turn 1
intent1 = parser.parse("SELECT * FROM users WHERE age > 25")
context["previous_intent"] = intent1.to_dict()

# Turn 2 - uses context
intent2 = parser.parse_with_context("Show me their names", context)
# Automatically inherits table="users"

context["previous_intent"] = intent2.to_dict()

# Turn 3
intent3 = parser.parse_with_context("Sort by age", context)
# Still remembers table="users"
```

### Pattern 4: Pipeline Queries

```python
parser = IntentParser()
intent = parser.parse(
    "SELECT COUNT(*) FROM users WHERE active = true GROUP BY city LIMIT 10"
)

if intent.is_pipeline():
    stages = intent.get_pipeline_stages()
    # stages = ["filter", "aggregate", "limit"]

    # Execute stages in order
    for stage in stages:
        if stage == "filter":
            # Apply filter...
        elif stage == "aggregate":
            # Apply aggregation...
        # ...
```

### Pattern 5: Confidence-Based Routing

```python
parser = IntentParser()
intent = parser.parse(user_query)

if intent.confidence > 0.8:
    # High confidence - execute directly
    execute_query(intent)
elif intent.confidence > 0.5:
    # Medium confidence - confirm with user
    print(f"Did you mean: {intent.intent_type}?")
    # Wait for confirmation...
else:
    # Low confidence - ask for clarification
    message = parser.generate_clarification_response(intent)
    print(message)
```

## Entity Extraction

The parser extracts the following entities from queries:

- **table**: Primary table name
- **columns**: List of column names
- **conditions**: List of filter conditions
- **aggregations**: List of aggregation functions (count, sum, avg, etc.)
- **joins**: List of join specifications
- **sort**: Sort column and direction
- **limit**: Result limit
- **group_by**: Grouping columns

**Example:**
```python
intent = parser.parse("SELECT name, age FROM users WHERE age > 25 LIMIT 10")

intent.get_table()        # "users"
intent.get_columns()      # ["name", "age"]
intent.get_conditions()   # ["age > 25"]
intent.entities["limit"]  # 10
```

## Confidence Scoring

Confidence scores indicate how certain the parser is about the intent:

- **0.8 - 1.0**: High confidence (SQL queries, clear patterns)
- **0.5 - 0.8**: Medium confidence (natural language with clear keywords)
- **0.0 - 0.5**: Low confidence (ambiguous, unclear, or unknown)

Factors affecting confidence:
- SQL syntax → Higher confidence
- Clear keywords → Higher confidence
- Extracted entities → Higher confidence
- Ambiguous pronouns → Lower confidence
- Missing table/column names → Lower confidence
- Complex or long queries → Lower confidence

## Ambiguity Detection

The parser automatically detects ambiguity and generates clarification questions for:

1. **Missing table name**: "Which table would you like to query?"
2. **Ambiguous pronouns** (it, that, this): "Could you specify which column or value?"
3. **Vague time references** (recently, soon): "What time period do you mean exactly?"
4. **Missing aggregation column**: "Which column should I count?"
5. **Complex queries**: "Could you break this into simpler questions?"
6. **Low confidence**: "Did you want to filter or select all records?"

**Example:**
```python
intent = parser.parse("Show me data from recently")

print(intent.is_ambiguous())  # True
print(intent.clarification_questions)
# ["What time period do you mean exactly? (e.g., last 7 days, past month)"]
```

## Error Handling

```python
from neurolake.intent import IntentParser, Intent, IntentType

parser = IntentParser()

try:
    intent = parser.parse(user_query)

    if intent.intent_type == IntentType.UNKNOWN:
        print("Sorry, I didn't understand that query")
    elif intent.needs_clarification():
        print(parser.generate_clarification_response(intent))
    else:
        # Execute query
        pass

except Exception as e:
    print(f"Error parsing query: {e}")
```

## Best Practices

1. **Always check confidence**: Don't execute low-confidence queries without confirmation
2. **Handle ambiguity**: Use `needs_clarification()` to detect when to ask follow-up questions
3. **Use context**: For conversational interfaces, maintain context between turns
4. **Validate entities**: Check that required entities (table, columns) are present
5. **Handle UNKNOWN intents**: Provide helpful error messages or suggestions
6. **Test with diverse queries**: Use both SQL and natural language queries
7. **Monitor pipeline queries**: Complex queries may need special handling

## Performance Considerations

- **Rule-based parsing**: Fast (~1ms), but less accurate for complex natural language
- **LLM-based parsing**: More accurate (~100-500ms), but requires LLM provider
- **Caching**: Parser is stateless, so results can be cached by query hash
- **Context overhead**: Minimal - only stores previous intent entities

## Integration with LLM

```python
from neurolake.llm import create_llm_provider
from neurolake.intent import IntentParser

# Create LLM provider
llm = create_llm_provider(
    provider="openai",
    api_key="your-api-key"
)

# Create parser with LLM
parser = IntentParser(llm_provider=llm)

# Will use LLM for parsing, with rule-based fallback
intent = parser.parse("Show me users who purchased something last month")
```

## API Reference Summary

### Classes
- `IntentType` - Enumeration of intent types
- `Intent` - Parsed intent data structure
- `IntentParser` - Main parser class

### Key Methods
- `IntentParser.parse(query)` - Parse query to intent
- `IntentParser.parse_with_context(query, context)` - Context-aware parsing
- `IntentParser.generate_clarification_response(intent)` - Generate clarification
- `Intent.is_pipeline()` - Check if pipeline query
- `Intent.needs_clarification()` - Check if clarification needed
- `Intent.to_dict()` - Serialize to dictionary

### Entities
- table, columns, conditions, aggregations, joins, sort, limit, group_by

### Confidence Levels
- High (0.8-1.0), Medium (0.5-0.8), Low (0-0.5)
