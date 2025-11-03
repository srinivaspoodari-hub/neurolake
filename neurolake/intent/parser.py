"""
Intent Parser

Parse user intent from natural language using LLMs or rules.
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from neurolake.intent.model import Intent, IntentType
from neurolake.prompts import get_prompt

logger = logging.getLogger(__name__)


class IntentParser:
    """
    Parse user intent from natural language queries.

    Example:
        parser = IntentParser()

        # Parse with LLM (if available)
        intent = parser.parse("Show me all users where age > 25")

        # Parse with rules (fallback)
        intent = parser.parse_with_rules("SELECT * FROM users")
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        """
        Initialize intent parser.

        Args:
            llm_provider: Optional LLM provider for parsing
        """
        self.llm = llm_provider
        self.prompt_template = get_prompt("intent_parser")

    def parse(self, query: str) -> Intent:
        """
        Parse user query to extract intent.

        Args:
            query: Natural language query

        Returns:
            Parsed Intent
        """
        # Try LLM-based parsing if available
        if self.llm:
            try:
                return self.parse_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM parsing failed: {e}. Falling back to rules.")

        # Fall back to rule-based parsing
        return self.parse_with_rules(query)

    def parse_with_llm(self, query: str) -> Intent:
        """
        Parse intent using LLM.

        Args:
            query: Natural language query

        Returns:
            Parsed Intent
        """
        if not self.llm:
            raise ValueError("No LLM provider configured")

        # Render prompt
        prompt = self.prompt_template.render(user_query=query)

        # Get LLM response
        response = self.llm.generate(prompt, temperature=0.3)

        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            result = json.loads(json_match.group())

            # Create Intent object
            intent = Intent(
                intent_type=IntentType(result["intent"].lower()),
                confidence=float(result["confidence"]),
                original_query=query,
                entities=result.get("entities", {}),
                reasoning=result.get("reasoning", "")
            )

            return intent

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fall back to rules
            return self.parse_with_rules(query)

    def parse_with_rules(self, query: str) -> Intent:
        """
        Parse intent using rule-based heuristics.

        Args:
            query: User query (natural language or SQL)

        Returns:
            Parsed Intent
        """
        query_lower = query.lower().strip()

        # Detect intent type using keywords
        intent_type = self._detect_intent_type(query_lower)

        # Extract entities based on intent
        entities = self._extract_entities(query, intent_type)

        # Calculate confidence based on rule matching
        confidence = self._calculate_confidence(query_lower, intent_type, entities)

        # Create intent
        intent = Intent(
            intent_type=intent_type,
            confidence=confidence,
            original_query=query,
            entities=entities,
            reasoning="Rule-based parsing"
        )

        # Detect ambiguity and generate clarifications
        self._detect_ambiguity(intent, query_lower)

        return intent

    def _detect_intent_type(self, query: str) -> IntentType:
        """Detect intent type from query."""
        # Meta intents (check first to avoid conflicts)
        if query.startswith("help") or any(phrase in query for phrase in ["how to use", "guide me"]):
            return IntentType.HELP

        # Management intents (check before analysis intents)
        if query.startswith("create table") or "create table" in query:
            return IntentType.CREATE_TABLE
        if query.startswith("drop table") or "delete table" in query:
            return IntentType.DROP_TABLE
        if query.startswith("update") or "modify" in query:
            return IntentType.UPDATE
        if query.startswith("delete from") or "remove" in query:
            return IntentType.DELETE
        if query.startswith("insert") or "add" in query:
            return IntentType.INSERT

        # Schema queries (check before other "show" queries)
        if any(phrase in query for phrase in ["show me the schema", "describe table", "structure of"]):
            return IntentType.SCHEMA
        if query.startswith("describe") or (query.startswith("what") and "structure" in query):
            return IntentType.SCHEMA

        # Analysis intents (check before query intents to handle "trend" properly)
        if any(word in query for word in ["summarize", "summary", "overview"]):
            return IntentType.SUMMARIZE
        if any(word in query for word in ["compare", "versus", "vs", "difference between"]):
            return IntentType.COMPARE
        if any(word in query for word in ["predict", "forecast", "future", "will"]):
            return IntentType.FORECAST
        if any(word in query for word in ["anomaly", "outlier", "unusual", "abnormal"]):
            return IntentType.ANOMALY

        # Trend detection (more specific - check if not asking about time series)
        if "trend" in query:
            return IntentType.TREND
        if "pattern" in query and "over time" not in query:
            return IntentType.TREND

        # Explain queries (check specific patterns - expanded)
        if any(word in query for word in ["why", "what caused"]) or query.startswith("explain"):
            return IntentType.EXPLAIN
        if query.startswith("how does") or query.startswith("how did"):
            return IntentType.EXPLAIN

        # SQL keywords for queries
        if query.startswith("select"):
            if any(word in query for word in ["group by", "count", "sum", "avg"]):
                return IntentType.AGGREGATE
            elif "join" in query:
                return IntentType.JOIN
            elif "where" in query:
                return IntentType.FILTER
            return IntentType.SELECT

        # Aggregation patterns (check before general query intents)
        if query.startswith("count") or query.startswith("total number"):
            return IntentType.AGGREGATE
        if any(query.startswith(word) for word in ["sum of", "average", "avg", "max", "min", "total"]):
            return IntentType.AGGREGATE

        # Natural language query intents
        if any(word in query for word in ["show", "get", "fetch", "retrieve", "display", "list"]):
            # Check for aggregation first
            if any(word in query for word in ["count", "sum", "avg", "average", "total", "max", "min"]):
                return IntentType.AGGREGATE
            # Check for joins - but be specific to avoid false positives
            elif any(phrase in query for phrase in ["and their", "along with", "users with their"]):
                return IntentType.JOIN
            # Check for filters - be more specific to avoid "with" false positive
            elif "where" in query or "filter" in query or "having" in query:
                return IntentType.FILTER
            # Check "with" pattern - only classify as filter if it's a condition
            elif " with " in query and any(op in query for op in [">", "<", "=", "!="]):
                return IntentType.FILTER
            return IntentType.SELECT

        # Time series patterns (only when not already classified as trend)
        if any(phrase in query for phrase in ["by date", "timeline"]):
            return IntentType.TIME_SERIES
        # "over time" is ambiguous - could be trend or time series
        # If the query doesn't start with an action verb, treat "over time" as trend
        if "over time" in query and not any(query.startswith(word) for word in ["show", "get", "list", "display"]):
            return IntentType.TREND

        return IntentType.UNKNOWN

    def _extract_entities(self, query: str, intent_type: IntentType) -> Dict[str, Any]:
        """Extract entities from query based on intent."""
        entities: Dict[str, Any] = {}
        query_lower = query.lower()

        # Extract table name
        table_patterns = [
            r'from\s+(\w+)',  # SQL FROM clause
            r'table\s+(\w+)',  # "table users"
            r'in\s+(\w+)',  # "in users"
        ]

        for pattern in table_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entities["table"] = match.group(1)
                break

        # Extract columns
        if "select" in query_lower:
            # SQL SELECT
            select_match = re.search(r'select\s+(.*?)\s+from', query_lower)
            if select_match:
                cols_str = select_match.group(1)
                if cols_str.strip() == "*":
                    entities["columns"] = ["*"]
                else:
                    entities["columns"] = [c.strip() for c in cols_str.split(",")]

        # Extract conditions
        conditions = []
        where_match = re.search(r'where\s+(.*?)(?:group|order|limit|$)', query_lower)
        if where_match:
            conditions.append(where_match.group(1).strip())

        # Extract from natural language
        for pattern in [r'where\s+(.*?)(?:\s+and|\s+or|$)', r'with\s+(.*?)(?:\s+and|\s+or|$)']:
            match = re.search(pattern, query_lower)
            if match:
                conditions.append(match.group(1).strip())

        if conditions:
            entities["conditions"] = list(set(conditions))  # Remove duplicates

        # Extract aggregations
        agg_functions = ["count", "sum", "avg", "average", "max", "min", "total"]
        found_aggs = [agg for agg in agg_functions if agg in query_lower]
        if found_aggs:
            entities["aggregations"] = found_aggs

        # Extract limit
        limit_match = re.search(r'limit\s+(\d+)', query_lower)
        if limit_match:
            entities["limit"] = int(limit_match.group(1))
        elif any(word in query_lower for word in ["top", "first"]):
            top_match = re.search(r'(?:top|first)\s+(\d+)', query_lower)
            if top_match:
                entities["limit"] = int(top_match.group(1))

        return entities

    def _calculate_confidence(
        self,
        query: str,
        intent_type: IntentType,
        entities: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for rule-based parsing."""
        confidence = 0.5  # Base confidence

        # Higher confidence for SQL queries
        if query.startswith(("select", "insert", "update", "delete", "create")):
            confidence += 0.3

        # Higher confidence if we found entities
        if entities.get("table"):
            confidence += 0.1
        if entities.get("columns"):
            confidence += 0.05
        if entities.get("conditions"):
            confidence += 0.05

        # Lower confidence for UNKNOWN intent
        if intent_type == IntentType.UNKNOWN:
            confidence = max(0.2, confidence - 0.3)

        return min(1.0, confidence)

    def _detect_ambiguity(self, intent: Intent, query: str):
        """Detect ambiguity and generate clarification questions."""
        # Check for missing table name
        if intent.is_query() and not intent.get_table():
            intent.add_clarification(
                "Which table would you like to query?",
                "Missing table specification"
            )

        # Check for ambiguous column references
        if "it" in query or "that" in query or "this" in query:
            intent.add_clarification(
                "Could you specify which column or value you're referring to?",
                "Ambiguous pronoun reference"
            )

        # Check for vague time references
        if any(word in query for word in ["recently", "lately", "soon", "today"]):
            if not any(word in query for word in ["last", "past", "next", "days", "weeks", "months"]):
                intent.add_clarification(
                    "What time period do you mean exactly? (e.g., last 7 days, past month)",
                    "Vague time reference"
                )

        # Check for ambiguous aggregations
        if intent.intent_type == IntentType.AGGREGATE:
            aggs = intent.get_aggregations()
            if len(aggs) > 0 and not intent.get_columns():
                intent.add_clarification(
                    f"Which column should I {aggs[0]}?",
                    "Missing aggregation column"
                )

        # Check for multiple possible interpretations (low confidence)
        if intent.confidence < 0.6 and intent.intent_type != IntentType.UNKNOWN:
            # Suggest alternatives
            if intent.intent_type == IntentType.SELECT:
                intent.add_alternative(IntentType.FILTER, 0.4, intent.entities)
                intent.add_clarification(
                    "Did you want to filter or select all records?",
                    "Uncertain intent classification"
                )

        # Check for complex queries without clear structure
        words = query.split()
        if len(words) > 15 and intent.confidence < 0.7:
            intent.add_clarification(
                "Could you break this into simpler questions?",
                "Query too complex"
            )

    def parse_with_context(self, query: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """
        Parse query with conversation context.

        Args:
            query: User query
            context: Previous conversation context (previous intents, entities, etc.)

        Returns:
            Parsed Intent with context applied
        """
        # Parse the query normally
        intent = self.parse(query)

        if not context:
            return intent

        # Apply context to resolve references
        previous_intent = context.get("previous_intent")
        if previous_intent:
            # Inherit table if not specified
            if not intent.get_table() and previous_intent.get("table"):
                intent.entities["table"] = previous_intent["table"]

            # Resolve pronouns
            if any(word in query.lower() for word in ["it", "that", "this", "same"]):
                # Inherit relevant entities from previous intent
                if "columns" in previous_intent and "columns" not in intent.entities:
                    intent.entities["columns"] = previous_intent["columns"]

        # Apply accumulated entities from context
        accumulated = context.get("accumulated_entities", {})
        for key, value in accumulated.items():
            if key not in intent.entities:
                intent.entities[key] = value

        # Recalculate confidence with context
        if intent.get_table():
            intent.confidence = min(1.0, intent.confidence + 0.1)

        return intent

    def generate_clarification_response(self, intent: Intent) -> str:
        """
        Generate a natural language clarification response.

        Args:
            intent: Intent with clarification questions

        Returns:
            Human-readable clarification message
        """
        if not intent.needs_clarification():
            return ""

        response = "I need some clarification:\n\n"

        for i, question in enumerate(intent.clarification_questions, 1):
            response += f"{i}. {question}\n"

        if len(intent.alternative_intents) > 0:
            response += "\nOr did you mean:\n"
            for i, alt in enumerate(intent.alternative_intents, 1):
                response += f"{i}. {alt['intent_type']} (confidence: {alt['confidence']:.0%})\n"

        return response.strip()


__all__ = ["IntentParser"]
