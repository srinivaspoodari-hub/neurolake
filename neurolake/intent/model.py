"""
Intent Data Models

Define intent types and data structures.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class IntentType(Enum):
    """Types of user intents."""

    # Query intents
    SELECT = "select"
    AGGREGATE = "aggregate"
    FILTER = "filter"
    JOIN = "join"
    TIME_SERIES = "time_series"
    SORT = "sort"
    LIMIT = "limit"

    # Management intents
    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    UPDATE = "update"
    DELETE = "delete"
    INSERT = "insert"
    SCHEMA = "schema"

    # Analysis intents
    EXPLAIN = "explain"
    SUMMARIZE = "summarize"
    TREND = "trend"
    ANOMALY = "anomaly"
    COMPARE = "compare"
    FORECAST = "forecast"

    # Meta intents
    HELP = "help"
    UNKNOWN = "unknown"


class QueryIntent(Enum):
    """Specific query intent subtypes."""
    SIMPLE_SELECT = "simple_select"
    AGGREGATION = "aggregation"
    GROUP_BY = "group_by"
    MULTI_TABLE = "multi_table"
    SUBQUERY = "subquery"
    WINDOW_FUNCTION = "window_function"


class ManagementIntent(Enum):
    """Specific management intent subtypes."""
    DDL = "ddl"  # Data Definition Language
    DML = "dml"  # Data Manipulation Language
    DCL = "dcl"  # Data Control Language


class AnalysisIntent(Enum):
    """Specific analysis intent subtypes."""
    DESCRIPTIVE = "descriptive"  # What happened?
    DIAGNOSTIC = "diagnostic"    # Why did it happen?
    PREDICTIVE = "predictive"    # What will happen?
    PRESCRIPTIVE = "prescriptive"  # What should we do?


@dataclass
class Intent:
    """
    Parsed user intent.

    Example:
        intent = Intent(
            intent_type=IntentType.SELECT,
            confidence=0.95,
            original_query="Show me all users",
            entities={
                "table": "users",
                "columns": ["*"]
            }
        )
    """

    intent_type: IntentType
    confidence: float
    original_query: str
    entities: Dict[str, Any] = field(default_factory=dict)
    subintent: Optional[str] = None
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    ambiguous: bool = False
    ambiguity_reasons: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    alternative_intents: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Validate intent."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")

    def is_query(self) -> bool:
        """Check if this is a query intent."""
        query_intents = {
            IntentType.SELECT,
            IntentType.AGGREGATE,
            IntentType.FILTER,
            IntentType.JOIN,
            IntentType.TIME_SERIES,
            IntentType.SORT,
            IntentType.LIMIT
        }
        return self.intent_type in query_intents

    def is_management(self) -> bool:
        """Check if this is a management intent."""
        management_intents = {
            IntentType.CREATE_TABLE,
            IntentType.DROP_TABLE,
            IntentType.UPDATE,
            IntentType.DELETE,
            IntentType.INSERT,
            IntentType.SCHEMA
        }
        return self.intent_type in management_intents

    def is_analysis(self) -> bool:
        """Check if this is an analysis intent."""
        analysis_intents = {
            IntentType.EXPLAIN,
            IntentType.SUMMARIZE,
            IntentType.TREND,
            IntentType.ANOMALY,
            IntentType.COMPARE,
            IntentType.FORECAST
        }
        return self.intent_type in analysis_intents

    def get_table(self) -> Optional[str]:
        """Get the primary table name."""
        return self.entities.get("table")

    def get_columns(self) -> List[str]:
        """Get the requested columns."""
        return self.entities.get("columns", [])

    def get_conditions(self) -> List[str]:
        """Get filter conditions."""
        return self.entities.get("conditions", [])

    def get_aggregations(self) -> List[str]:
        """Get aggregation functions."""
        return self.entities.get("aggregations", [])

    def get_joins(self) -> List[Dict[str, str]]:
        """Get join specifications."""
        return self.entities.get("joins", [])

    def is_ambiguous(self) -> bool:
        """Check if this intent is ambiguous."""
        return self.ambiguous or self.confidence < 0.5

    def needs_clarification(self) -> bool:
        """Check if this intent needs clarification."""
        return len(self.clarification_questions) > 0 or self.is_ambiguous()

    def add_clarification(self, question: str, reason: str = ""):
        """Add a clarification question."""
        if question not in self.clarification_questions:
            self.clarification_questions.append(question)
        if reason and reason not in self.ambiguity_reasons:
            self.ambiguity_reasons.append(reason)
        self.ambiguous = True

    def add_alternative(self, intent_type: IntentType, confidence: float, entities: Dict[str, Any]):
        """Add an alternative interpretation."""
        self.alternative_intents.append({
            "intent_type": intent_type.value,
            "confidence": confidence,
            "entities": entities
        })

    def is_pipeline(self) -> bool:
        """Check if this is a pipeline query (multiple operations)."""
        # A query is a pipeline if it has multiple operation types
        has_filter = len(self.get_conditions()) > 0
        has_aggregation = len(self.get_aggregations()) > 0
        has_join = len(self.get_joins()) > 0
        has_sort = self.entities.get("sort") is not None
        has_limit = self.entities.get("limit") is not None

        operations = sum([has_filter, has_aggregation, has_join, has_sort, has_limit])
        return operations >= 2

    def get_pipeline_stages(self) -> List[str]:
        """Get the stages of a pipeline query."""
        stages = []

        if len(self.get_joins()) > 0:
            stages.append("join")
        if len(self.get_conditions()) > 0:
            stages.append("filter")
        if len(self.get_aggregations()) > 0:
            stages.append("aggregate")
        if self.entities.get("sort"):
            stages.append("sort")
        if self.entities.get("limit"):
            stages.append("limit")

        return stages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent_type": self.intent_type.value,
            "confidence": self.confidence,
            "original_query": self.original_query,
            "entities": self.entities,
            "subintent": self.subintent,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "ambiguous": self.ambiguous,
            "ambiguity_reasons": self.ambiguity_reasons,
            "clarification_questions": self.clarification_questions,
            "alternative_intents": self.alternative_intents,
            "is_pipeline": self.is_pipeline(),
            "pipeline_stages": self.get_pipeline_stages() if self.is_pipeline() else []
        }


__all__ = [
    "Intent",
    "IntentType",
    "QueryIntent",
    "ManagementIntent",
    "AnalysisIntent",
]
