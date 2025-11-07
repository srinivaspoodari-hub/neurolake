"""
Autonomous Transformation Tracker - Automatically captures and learns transformations
"""

import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class TransformationType(Enum):
    """Types of transformations"""
    COLUMN_DERIVATION = "column_derivation"  # Creating new column from existing
    AGGREGATION = "aggregation"  # GROUP BY operations
    FILTER = "filter"  # WHERE conditions
    JOIN = "join"  # JOIN operations
    UNION = "union"  # UNION operations
    WINDOW = "window"  # Window functions
    PIVOT = "pivot"  # Pivot operations
    UNPIVOT = "unpivot"  # Unpivot operations
    DEDUPLICATION = "deduplication"  # Removing duplicates
    NORMALIZATION = "normalization"  # Data normalization
    ENRICHMENT = "enrichment"  # Adding external data
    CLEANSING = "cleansing"  # Data quality improvements


class AutonomousTransformationTracker:
    """
    Automatically captures, catalogs, and learns from transformations

    Features:
    - Auto-capture all DataFrame/SQL transformations
    - Learn transformation patterns using AI
    - Suggest transformations based on context
    - Build reusable transformation library
    - Track transformation lineage
    - Performance profiling
    """

    def __init__(self, storage_path: str = "./transformations", llm_client=None):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.llm_client = llm_client

        self.transformations: Dict[str, Dict] = {}
        self.patterns: Dict[str, List[str]] = {}  # pattern_hash -> transformation_ids
        self.suggestions: Dict[str, List[Dict]] = {}  # context -> suggested transformations

        self._load_transformations()

    def _load_transformations(self):
        """Load transformations from storage"""
        trans_file = self.storage_path / "transformations.json"
        if trans_file.exists():
            try:
                with open(trans_file, 'r') as f:
                    data = json.load(f)
                    self.transformations = data.get('transformations', {})
                    self.patterns = data.get('patterns', {})
                logger.info(f"Loaded {len(self.transformations)} transformations")
            except Exception as e:
                logger.error(f"Error loading transformations: {e}")

    def _save_transformations(self):
        """Save transformations to storage"""
        trans_file = self.storage_path / "transformations.json"
        try:
            with open(trans_file, 'w') as f:
                json.dump({
                    'transformations': self.transformations,
                    'patterns': self.patterns
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving transformations: {e}")

    def capture_transformation(
        self,
        transformation_name: str,
        transformation_type: TransformationType,
        input_columns: List[str],
        output_columns: List[str],
        logic: str,
        code: str = "",
        language: str = "python",
        metadata: Dict = None
    ) -> str:
        """
        Automatically capture a transformation

        Args:
            transformation_name: Human-readable name
            transformation_type: Type of transformation
            input_columns: Input column names
            output_columns: Output column names
            logic: Transformation logic description
            code: Actual code executed
            language: Programming language
            metadata: Additional metadata
        """
        trans_id = f"trans_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        transformation = {
            'transformation_id': trans_id,
            'name': transformation_name,
            'type': transformation_type.value,
            'input_columns': input_columns,
            'output_columns': output_columns,
            'logic': logic,
            'code': code,
            'language': language,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'usage_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'avg_execution_time_ms': 0
        }

        self.transformations[trans_id] = transformation

        # Extract and index pattern
        pattern_hash = self._extract_pattern(transformation)
        if pattern_hash not in self.patterns:
            self.patterns[pattern_hash] = []
        self.patterns[pattern_hash].append(trans_id)

        self._save_transformations()
        logger.info(f"Captured transformation: {trans_id}")

        # Learn from this transformation (async in production)
        self._learn_pattern(trans_id)

        return trans_id

    def _extract_pattern(self, transformation: Dict) -> str:
        """
        Extract a pattern signature from transformation

        Pattern includes: type + input column types + output column types
        """
        pattern_str = f"{transformation['type']}"

        # Add input/output column count
        pattern_str += f"_in{len(transformation['input_columns'])}"
        pattern_str += f"_out{len(transformation['output_columns'])}"

        # Hash for indexing
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]

    def _learn_pattern(self, transformation_id: str):
        """
        Learn from transformation pattern using AI

        Analyzes:
        - Common column name patterns
        - Transformation logic patterns
        - Context patterns (when is this useful)
        """
        if not self.llm_client:
            return

        transformation = self.transformations.get(transformation_id)
        if not transformation:
            return

        try:
            prompt = f"""Analyze this data transformation:

Name: {transformation['name']}
Type: {transformation['type']}
Input Columns: {transformation['input_columns']}
Output Columns: {transformation['output_columns']}
Logic: {transformation['logic']}

Provide:
1. When should this transformation be used? (context)
2. What are common variations of this transformation?
3. What column name patterns indicate this transformation is needed?

Format as JSON.
"""

            response = self.llm_client.generate(prompt)

            # Parse and store learning
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                learning = json.loads(json_match.group())
                transformation['ai_learning'] = learning
                self._save_transformations()

        except Exception as e:
            logger.error(f"Error learning pattern: {e}")

    def suggest_transformations(
        self,
        context: Dict,
        available_columns: List[str],
        limit: int = 5
    ) -> List[Dict]:
        """
        Suggest relevant transformations based on context

        Args:
            context: Current context (table name, column names, data types, etc.)
            available_columns: Columns available for transformation
            limit: Maximum suggestions to return

        Returns:
            List of suggested transformations with confidence scores
        """
        suggestions = []

        # Rule-based suggestions
        suggestions.extend(self._rule_based_suggestions(available_columns))

        # Pattern-based suggestions
        suggestions.extend(self._pattern_based_suggestions(context, available_columns))

        # AI-based suggestions (if LLM available)
        if self.llm_client:
            suggestions.extend(self._ai_based_suggestions(context, available_columns))

        # Rank by confidence and return top N
        suggestions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return suggestions[:limit]

    def _rule_based_suggestions(self, available_columns: List[str]) -> List[Dict]:
        """Suggest transformations using rules"""
        suggestions = []

        col_names_lower = [col.lower() for col in available_columns]

        # Revenue calculation
        if 'price' in col_names_lower and 'quantity' in col_names_lower:
            if 'revenue' not in col_names_lower:
                suggestions.append({
                    'transformation_name': 'Calculate Revenue',
                    'type': TransformationType.COLUMN_DERIVATION.value,
                    'logic': 'revenue = price * quantity',
                    'input_columns': ['price', 'quantity'],
                    'output_columns': ['revenue'],
                    'confidence': 0.9,
                    'reason': 'Found price and quantity columns without revenue'
                })

        # Full name creation
        if 'first_name' in col_names_lower and 'last_name' in col_names_lower:
            if 'full_name' not in col_names_lower:
                suggestions.append({
                    'transformation_name': 'Create Full Name',
                    'type': TransformationType.COLUMN_DERIVATION.value,
                    'logic': "full_name = CONCAT(first_name, ' ', last_name)",
                    'input_columns': ['first_name', 'last_name'],
                    'output_columns': ['full_name'],
                    'confidence': 0.85,
                    'reason': 'Found first_name and last_name without full_name'
                })

        # Date extraction
        for col in col_names_lower:
            if 'timestamp' in col or 'datetime' in col:
                date_col = col.replace('timestamp', 'date').replace('datetime', 'date')
                if date_col not in col_names_lower:
                    suggestions.append({
                        'transformation_name': f'Extract Date from {col}',
                        'type': TransformationType.COLUMN_DERIVATION.value,
                        'logic': f'{date_col} = DATE({col})',
                        'input_columns': [col],
                        'output_columns': [date_col],
                        'confidence': 0.75,
                        'reason': f'Timestamp column {col} can be converted to date'
                    })

        return suggestions

    def _pattern_based_suggestions(self, context: Dict, available_columns: List[str]) -> List[Dict]:
        """Suggest transformations based on learned patterns"""
        suggestions = []

        # Find similar transformations from history
        for trans_id, transformation in self.transformations.items():
            input_cols = transformation['input_columns']

            # Check if input columns are available
            if all(col in available_columns for col in input_cols):
                # Check if output columns don't exist yet
                output_cols = transformation['output_columns']
                if not any(col in available_columns for col in output_cols):
                    # Calculate confidence based on usage success rate
                    total = transformation['success_count'] + transformation['failure_count']
                    confidence = transformation['success_count'] / total if total > 0 else 0.5

                    suggestions.append({
                        'transformation_id': trans_id,
                        'transformation_name': transformation['name'],
                        'type': transformation['type'],
                        'logic': transformation['logic'],
                        'input_columns': input_cols,
                        'output_columns': output_cols,
                        'confidence': min(confidence, 0.8),  # Cap at 0.8 for pattern-based
                        'reason': f"Similar transformation used successfully {transformation['success_count']} times"
                    })

        return suggestions

    def _ai_based_suggestions(self, context: Dict, available_columns: List[str]) -> List[Dict]:
        """Use AI to suggest transformations"""
        if not self.llm_client:
            return []

        try:
            prompt = f"""Given these columns: {available_columns}

Context: {context}

Suggest 3-5 useful transformations that would add value to this dataset.
For each transformation, provide:
- name: transformation name
- logic: transformation logic
- input_columns: list of input columns
- output_columns: list of output columns
- reason: why this transformation is useful

Format as JSON array.
"""

            response = self.llm_client.generate(prompt)

            # Parse JSON response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                ai_suggestions = json.loads(json_match.group())

                # Add confidence and type
                for sugg in ai_suggestions:
                    sugg['confidence'] = 0.7  # AI suggestions get 0.7 confidence
                    sugg['type'] = TransformationType.COLUMN_DERIVATION.value
                    sugg['source'] = 'ai'

                return ai_suggestions

        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")

        return []

    def apply_transformation(
        self,
        transformation_id: str,
        dataframe: Any,  # Spark DataFrame or Pandas DataFrame
        track_execution: bool = True
    ) -> Any:
        """
        Apply a cataloged transformation to a dataframe

        Args:
            transformation_id: ID of transformation to apply
            dataframe: DataFrame to transform
            track_execution: Whether to track execution metrics
        """
        transformation = self.transformations.get(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation {transformation_id} not found")

        start_time = datetime.utcnow()
        success = False

        try:
            # Execute transformation based on language
            if transformation['language'] == 'python':
                # Execute Python code
                result_df = self._execute_python_transformation(dataframe, transformation)
            elif transformation['language'] == 'sql':
                # Execute SQL transformation
                result_df = self._execute_sql_transformation(dataframe, transformation)
            else:
                raise ValueError(f"Unsupported language: {transformation['language']}")

            success = True
            return result_df

        finally:
            if track_execution:
                # Update execution metrics
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                transformation['usage_count'] += 1
                if success:
                    transformation['success_count'] += 1
                else:
                    transformation['failure_count'] += 1

                # Update average execution time
                prev_avg = transformation['avg_execution_time_ms']
                usage_count = transformation['usage_count']
                transformation['avg_execution_time_ms'] = \
                    ((prev_avg * (usage_count - 1)) + execution_time_ms) / usage_count

                self._save_transformations()

    def _execute_python_transformation(self, dataframe: Any, transformation: Dict) -> Any:
        """Execute Python transformation code"""
        code = transformation['code']

        # Create execution context
        context = {
            'df': dataframe,
            '__builtins__': __builtins__
        }

        # Execute code
        exec(code, context)

        # Return transformed dataframe
        return context.get('result_df', context.get('df'))

    def _execute_sql_transformation(self, dataframe: Any, transformation: Dict) -> Any:
        """Execute SQL transformation"""
        # This would use Spark SQL or similar
        # For now, placeholder
        raise NotImplementedError("SQL transformation not yet implemented")

    def get_transformation_stats(self) -> Dict:
        """Get statistics about transformations"""
        stats = {
            'total_transformations': len(self.transformations),
            'total_patterns': len(self.patterns),
            'by_type': {},
            'most_used': [],
            'highest_success_rate': []
        }

        # Count by type
        for trans in self.transformations.values():
            trans_type = trans['type']
            stats['by_type'][trans_type] = stats['by_type'].get(trans_type, 0) + 1

        # Most used transformations
        sorted_by_usage = sorted(
            self.transformations.values(),
            key=lambda x: x['usage_count'],
            reverse=True
        )
        stats['most_used'] = [
            {
                'id': t['transformation_id'],
                'name': t['name'],
                'usage_count': t['usage_count']
            }
            for t in sorted_by_usage[:10]
        ]

        # Highest success rate
        sorted_by_success = sorted(
            [t for t in self.transformations.values() if t['usage_count'] > 0],
            key=lambda x: x['success_count'] / (x['success_count'] + x['failure_count']),
            reverse=True
        )
        stats['highest_success_rate'] = [
            {
                'id': t['transformation_id'],
                'name': t['name'],
                'success_rate': t['success_count'] / (t['success_count'] + t['failure_count'])
            }
            for t in sorted_by_success[:10]
        ]

        return stats
