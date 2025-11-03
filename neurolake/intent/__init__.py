"""
NeuroLake Intent Module

Parse user intent from natural language queries.

Example:
    from neurolake.intent import IntentParser, IntentType

    parser = IntentParser()

    # Parse query
    intent = parser.parse("Show me all users where age > 25")

    print(f"Intent: {intent.intent_type}")
    print(f"Table: {intent.entities['table']}")
    print(f"Conditions: {intent.entities['conditions']}")
"""

from neurolake.intent.model import (
    Intent,
    IntentType,
    QueryIntent,
    ManagementIntent,
    AnalysisIntent
)
from neurolake.intent.parser import IntentParser

__all__ = [
    "Intent",
    "IntentType",
    "QueryIntent",
    "ManagementIntent",
    "AnalysisIntent",
    "IntentParser",
]
