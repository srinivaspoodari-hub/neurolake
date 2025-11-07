"""
NeuroLake Transformation Suggester
AI-powered transformation suggestion and learning engine
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class TransformationType(Enum):
    """Types of transformations"""
    DEDUPLICATE = "deduplicate"
    FILL_NULLS = "fill_nulls"
    DROP_NULLS = "drop_nulls"
    REMOVE_OUTLIERS = "remove_outliers"
    CAP_OUTLIERS = "cap_outliers"
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    TYPE_CONVERSION = "type_conversion"
    STRING_CLEAN = "string_clean"
    DATE_PARSE = "date_parse"
    DERIVE_COLUMN = "derive_column"
    AGGREGATE = "aggregate"
    JOIN = "join"
    FILTER = "filter"
    SORT = "sort"
    PIVOT = "pivot"
    MELT = "melt"
    RENAME = "rename"
    DROP_COLUMN = "drop_column"
    CUSTOM = "custom"


@dataclass
class TransformationSuggestion:
    """A suggested transformation"""
    transformation_type: TransformationType
    description: str
    column: Optional[str]
    parameters: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    estimated_impact: str  # "low", "medium", "high"
    reason: str
    code_snippet: str
    priority: int = 5  # 1-10, higher is more important
    learned_from: Optional[str] = None  # Pattern ID if learned
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationPlan:
    """Complete transformation plan"""
    suggestions: List[TransformationSuggestion]
    estimated_time_seconds: float
    estimated_cost_dollars: float
    processing_path: str  # "express", "standard", "quality", "enrichment"
    total_steps: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class TransformationSuggester:
    """AI-powered transformation suggestion engine"""

    def __init__(self, pattern_learner=None):
        """
        Initialize transformation suggester

        Args:
            pattern_learner: Optional PatternLearner for learning from executions
        """
        self.pattern_learner = pattern_learner
        self.learned_patterns = []

    def suggest_transformations(self,
                                df: pd.DataFrame,
                                quality_assessment: Optional[Dict] = None,
                                schema: Optional[Dict] = None,
                                target_use_case: str = "analytics") -> TransformationPlan:
        """
        Suggest transformations for a DataFrame

        Args:
            df: pandas DataFrame
            quality_assessment: Quality assessment results
            schema: Detected schema
            target_use_case: "analytics", "ml", "reporting", "archive"

        Returns:
            TransformationPlan with suggestions
        """
        suggestions = []

        # Suggest based on quality issues
        if quality_assessment:
            quality_suggestions = self._suggest_from_quality(df, quality_assessment)
            suggestions.extend(quality_suggestions)

        # Suggest based on schema
        if schema:
            schema_suggestions = self._suggest_from_schema(df, schema)
            suggestions.extend(schema_suggestions)

        # Suggest based on data patterns
        pattern_suggestions = self._suggest_from_patterns(df)
        suggestions.extend(pattern_suggestions)

        # Suggest based on target use case
        use_case_suggestions = self._suggest_from_use_case(df, target_use_case)
        suggestions.extend(use_case_suggestions)

        # Check learned patterns
        if self.pattern_learner:
            learned_suggestions = self._suggest_from_learned_patterns(df)
            suggestions.extend(learned_suggestions)

        # Remove duplicates and prioritize
        suggestions = self._deduplicate_and_prioritize(suggestions)

        # Determine processing path
        processing_path = self._determine_processing_path(quality_assessment)

        # Estimate time and cost
        estimated_time = self._estimate_time(suggestions, len(df))
        estimated_cost = self._estimate_cost(suggestions, len(df))

        return TransformationPlan(
            suggestions=suggestions,
            estimated_time_seconds=estimated_time,
            estimated_cost_dollars=estimated_cost,
            processing_path=processing_path,
            total_steps=len(suggestions),
            confidence=self._calculate_plan_confidence(suggestions)
        )

    def _suggest_from_quality(self, df: pd.DataFrame,
                              quality_assessment: Dict) -> List[TransformationSuggestion]:
        """Suggest transformations based on quality issues"""
        suggestions = []

        issues = quality_assessment.get('issues', [])

        for issue in issues:
            dimension = issue.get('dimension')
            severity = issue.get('severity')
            column = issue.get('column')
            description = issue.get('description')

            # Handle completeness issues
            if dimension == 'completeness':
                null_pct = issue.get('affected_percentage', 0)

                if null_pct < 5:
                    # Low percentage - drop rows
                    suggestions.append(TransformationSuggestion(
                        transformation_type=TransformationType.DROP_NULLS,
                        description=f"Drop rows with nulls in '{column}'",
                        column=column,
                        parameters={'column': column},
                        confidence=0.9,
                        estimated_impact="low",
                        reason=f"Only {null_pct:.1f}% nulls - safe to drop",
                        code_snippet=f"df = df.dropna(subset=['{column}'])",
                        priority=8
                    ))
                else:
                    # High percentage - fill nulls
                    fill_strategy = self._suggest_fill_strategy(df, column)
                    suggestions.append(TransformationSuggestion(
                        transformation_type=TransformationType.FILL_NULLS,
                        description=f"Fill nulls in '{column}' with {fill_strategy}",
                        column=column,
                        parameters={'column': column, 'strategy': fill_strategy},
                        confidence=0.85,
                        estimated_impact="medium",
                        reason=f"{null_pct:.1f}% nulls - filling recommended",
                        code_snippet=self._generate_fill_code(column, fill_strategy),
                        priority=9
                    ))

            # Handle uniqueness issues (duplicates)
            elif dimension == 'uniqueness':
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DEDUPLICATE,
                    description="Remove duplicate rows",
                    column=None,
                    parameters={'subset': None, 'keep': 'first'},
                    confidence=0.95,
                    estimated_impact="medium",
                    reason="Duplicates detected",
                    code_snippet="df = df.drop_duplicates()",
                    priority=10
                ))

            # Handle accuracy issues (outliers)
            elif dimension == 'accuracy' and 'outlier' in description.lower():
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.CAP_OUTLIERS,
                    description=f"Cap outliers in '{column}'",
                    column=column,
                    parameters={'column': column, 'method': 'iqr'},
                    confidence=0.8,
                    estimated_impact="medium",
                    reason="Outliers detected",
                    code_snippet=self._generate_cap_outliers_code(column),
                    priority=7
                ))

            # Handle consistency issues
            elif dimension == 'consistency':
                if 'casing' in description.lower():
                    suggestions.append(TransformationSuggestion(
                        transformation_type=TransformationType.STRING_CLEAN,
                        description=f"Standardize casing in '{column}'",
                        column=column,
                        parameters={'column': column, 'operation': 'lower'},
                        confidence=0.9,
                        estimated_impact="low",
                        reason="Inconsistent casing detected",
                        code_snippet=f"df['{column}'] = df['{column}'].str.lower()",
                        priority=6
                    ))
                elif 'whitespace' in description.lower():
                    suggestions.append(TransformationSuggestion(
                        transformation_type=TransformationType.STRING_CLEAN,
                        description=f"Strip whitespace from '{column}'",
                        column=column,
                        parameters={'column': column, 'operation': 'strip'},
                        confidence=0.95,
                        estimated_impact="low",
                        reason="Whitespace detected",
                        code_snippet=f"df['{column}'] = df['{column}'].str.strip()",
                        priority=8
                    ))

        return suggestions

    def _suggest_from_schema(self, df: pd.DataFrame, schema: Dict) -> List[TransformationSuggestion]:
        """Suggest transformations based on detected schema"""
        suggestions = []

        columns = schema.get('columns', [])

        for col_info in columns:
            col_name = col_info.get('name')
            data_type = col_info.get('data_type')
            pii_type = col_info.get('pii_type')

            # Suggest type conversions
            if data_type == 'string':
                # Check if it's actually numeric
                try:
                    df[col_name].astype(float)
                    suggestions.append(TransformationSuggestion(
                        transformation_type=TransformationType.TYPE_CONVERSION,
                        description=f"Convert '{col_name}' to numeric",
                        column=col_name,
                        parameters={'column': col_name, 'target_type': 'float'},
                        confidence=0.85,
                        estimated_impact="low",
                        reason="String column contains numeric values",
                        code_snippet=f"df['{col_name}'] = pd.to_numeric(df['{col_name}'])",
                        priority=7
                    ))
                except (ValueError, TypeError):
                    pass

            # Suggest PII masking
            if pii_type and pii_type != 'none':
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.CUSTOM,
                    description=f"Mask PII in '{col_name}' ({pii_type})",
                    column=col_name,
                    parameters={'column': col_name, 'pii_type': pii_type},
                    confidence=0.9,
                    estimated_impact="high",
                    reason=f"PII detected: {pii_type}",
                    code_snippet=f"# Mask PII: df['{col_name}'] = mask_pii(df['{col_name}'], '{pii_type}')",
                    priority=9
                ))

        return suggestions

    def _suggest_from_patterns(self, df: pd.DataFrame) -> List[TransformationSuggestion]:
        """Suggest transformations based on data patterns"""
        suggestions = []

        # Check for columns that might need to be derived
        # Example: If we have first_name and last_name, suggest deriving full_name
        if 'first_name' in df.columns and 'last_name' in df.columns and 'full_name' not in df.columns:
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.DERIVE_COLUMN,
                description="Derive 'full_name' from 'first_name' and 'last_name'",
                column='full_name',
                parameters={'columns': ['first_name', 'last_name'], 'operation': 'concat'},
                confidence=0.95,
                estimated_impact="low",
                reason="Related name columns detected",
                code_snippet="df['full_name'] = df['first_name'] + ' ' + df['last_name']",
                priority=6
            ))

        # Check for revenue/quantity columns - suggest deriving total
        if 'quantity' in df.columns and 'price' in df.columns and 'total' not in df.columns:
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.DERIVE_COLUMN,
                description="Derive 'total' from 'quantity' * 'price'",
                column='total',
                parameters={'columns': ['quantity', 'price'], 'operation': 'multiply'},
                confidence=0.9,
                estimated_impact="medium",
                reason="Quantity and price columns detected",
                code_snippet="df['total'] = df['quantity'] * df['price']",
                priority=7
            ))

        # Check for date columns - suggest extracting components
        date_cols = df.select_dtypes(include=['datetime64']).columns
        for col in date_cols:
            if f"{col}_year" not in df.columns:
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.DERIVE_COLUMN,
                    description=f"Extract date components from '{col}'",
                    column=col,
                    parameters={'column': col, 'components': ['year', 'month', 'day']},
                    confidence=0.85,
                    estimated_impact="low",
                    reason="Date column detected - components useful for analysis",
                    code_snippet=f"df['{col}_year'] = df['{col}'].dt.year\ndf['{col}_month'] = df['{col}'].dt.month",
                    priority=5
                ))

        return suggestions

    def _suggest_from_use_case(self, df: pd.DataFrame, target_use_case: str) -> List[TransformationSuggestion]:
        """Suggest transformations based on target use case"""
        suggestions = []

        if target_use_case == "ml":
            # ML use case - suggest normalization/standardization
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols[:3]:  # Top 3 numeric columns
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.STANDARDIZE,
                    description=f"Standardize '{col}' for ML (z-score)",
                    column=col,
                    parameters={'column': col, 'method': 'standard'},
                    confidence=0.8,
                    estimated_impact="medium",
                    reason="ML use case - standardization improves model performance",
                    code_snippet=f"df['{col}'] = (df['{col}'] - df['{col}'].mean()) / df['{col}'].std()",
                    priority=6
                ))

        elif target_use_case == "analytics":
            # Analytics - suggest aggregations
            if 'date' in df.columns or any('date' in col.lower() for col in df.columns):
                suggestions.append(TransformationSuggestion(
                    transformation_type=TransformationType.AGGREGATE,
                    description="Consider aggregating by date for time-series analysis",
                    column=None,
                    parameters={'group_by': 'date', 'agg_functions': ['sum', 'mean', 'count']},
                    confidence=0.7,
                    estimated_impact="medium",
                    reason="Analytics use case with date column",
                    code_snippet="# df_agg = df.groupBy('date').agg(F.sum('amount'), F.count('*'))",
                    priority=4
                ))

        elif target_use_case == "reporting":
            # Reporting - suggest sorting and formatting
            suggestions.append(TransformationSuggestion(
                transformation_type=TransformationType.SORT,
                description="Sort data for reporting",
                column=None,
                parameters={'columns': df.columns[0], 'ascending': True},
                confidence=0.75,
                estimated_impact="low",
                reason="Reporting use case - sorted data improves readability",
                code_snippet=f"df = df.sort_values('{df.columns[0]}')",
                priority=3
            ))

        return suggestions

    def _suggest_from_learned_patterns(self, df: pd.DataFrame) -> List[TransformationSuggestion]:
        """Suggest transformations based on learned patterns"""
        suggestions = []

        # This would query the PatternLearner for similar past transformations
        # For now, return empty list (will be populated when pattern learner is integrated)

        return suggestions

    def _suggest_fill_strategy(self, df: pd.DataFrame, column: str) -> str:
        """Suggest best strategy for filling nulls"""
        if pd.api.types.is_numeric_dtype(df[column]):
            # Check if data is normally distributed
            non_null = df[column].dropna()
            if len(non_null) > 0:
                skew = non_null.skew()
                if abs(skew) < 0.5:
                    return "mean"
                else:
                    return "median"
        elif pd.api.types.is_bool_dtype(df[column]):
            return "mode"
        else:
            return "mode"

    def _generate_fill_code(self, column: str, strategy: str) -> str:
        """Generate code for filling nulls"""
        if strategy == "mean":
            return f"df['{column}'] = df['{column}'].fillna(df['{column}'].mean())"
        elif strategy == "median":
            return f"df['{column}'] = df['{column}'].fillna(df['{column}'].median())"
        elif strategy == "mode":
            return f"df['{column}'] = df['{column}'].fillna(df['{column}'].mode()[0])"
        else:
            return f"df['{column}'] = df['{column}'].fillna('{strategy}')"

    def _generate_cap_outliers_code(self, column: str) -> str:
        """Generate code for capping outliers"""
        return f"""
q1 = df['{column}'].quantile(0.25)
q3 = df['{column}'].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
df['{column}'] = df['{column}'].clip(lower, upper)
""".strip()

    def _deduplicate_and_prioritize(self, suggestions: List[TransformationSuggestion]) -> List[TransformationSuggestion]:
        """Remove duplicate suggestions and prioritize"""
        # Remove duplicates based on transformation_type + column
        seen = set()
        unique_suggestions = []

        for suggestion in suggestions:
            key = (suggestion.transformation_type, suggestion.column)
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)

        # Sort by priority (descending)
        unique_suggestions.sort(key=lambda x: x.priority, reverse=True)

        return unique_suggestions

    def _determine_processing_path(self, quality_assessment: Optional[Dict]) -> str:
        """Determine optimal processing path based on quality"""
        if not quality_assessment:
            return "standard"

        overall_score = quality_assessment.get('overall_score', 0.8)

        if overall_score >= 0.95:
            return "express"  # High quality - minimal processing
        elif overall_score >= 0.80:
            return "standard"  # Good quality - standard processing
        elif overall_score >= 0.60:
            return "quality"  # Fair quality - extensive cleaning
        else:
            return "enrichment"  # Poor quality - enrichment needed

    def _estimate_time(self, suggestions: List[TransformationSuggestion], row_count: int) -> float:
        """Estimate processing time in seconds"""
        # Simple heuristic: 0.1 seconds per suggestion per 1000 rows
        base_time = len(suggestions) * 0.1 * (row_count / 1000)
        return round(max(1.0, base_time), 2)

    def _estimate_cost(self, suggestions: List[TransformationSuggestion], row_count: int) -> float:
        """Estimate processing cost in dollars"""
        # Simple heuristic: $0.001 per 1000 rows per transformation
        base_cost = len(suggestions) * 0.001 * (row_count / 1000)
        return round(max(0.001, base_cost), 4)

    def _calculate_plan_confidence(self, suggestions: List[TransformationSuggestion]) -> float:
        """Calculate overall plan confidence"""
        if not suggestions:
            return 0.0

        avg_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
        return round(avg_confidence, 2)

    def execute_transformation(self, df: pd.DataFrame,
                              suggestion: TransformationSuggestion) -> pd.DataFrame:
        """Execute a transformation suggestion"""
        trans_type = suggestion.transformation_type
        column = suggestion.column
        params = suggestion.parameters

        if trans_type == TransformationType.DEDUPLICATE:
            return df.drop_duplicates()

        elif trans_type == TransformationType.DROP_NULLS:
            return df.dropna(subset=[column]) if column else df.dropna()

        elif trans_type == TransformationType.FILL_NULLS:
            strategy = params.get('strategy', 'mean')
            if strategy == 'mean':
                df[column] = df[column].fillna(df[column].mean())
            elif strategy == 'median':
                df[column] = df[column].fillna(df[column].median())
            elif strategy == 'mode':
                df[column] = df[column].fillna(df[column].mode()[0])
            return df

        elif trans_type == TransformationType.STRING_CLEAN:
            operation = params.get('operation', 'strip')
            if operation == 'lower':
                df[column] = df[column].str.lower()
            elif operation == 'upper':
                df[column] = df[column].str.upper()
            elif operation == 'strip':
                df[column] = df[column].str.strip()
            return df

        elif trans_type == TransformationType.CAP_OUTLIERS:
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            df[column] = df[column].clip(lower, upper)
            return df

        elif trans_type == TransformationType.TYPE_CONVERSION:
            target_type = params.get('target_type')
            if target_type == 'float':
                df[column] = pd.to_numeric(df[column], errors='coerce')
            elif target_type == 'int':
                df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
            elif target_type == 'datetime':
                df[column] = pd.to_datetime(df[column], errors='coerce')
            return df

        else:
            # For other types, return original (can be extended)
            return df

    def export_plan_to_dict(self, plan: TransformationPlan) -> Dict:
        """Export plan to dictionary"""
        return {
            'suggestions': [
                {
                    'transformation_type': s.transformation_type.value,
                    'description': s.description,
                    'column': s.column,
                    'parameters': s.parameters,
                    'confidence': s.confidence,
                    'estimated_impact': s.estimated_impact,
                    'reason': s.reason,
                    'code_snippet': s.code_snippet,
                    'priority': s.priority
                }
                for s in plan.suggestions
            ],
            'estimated_time_seconds': plan.estimated_time_seconds,
            'estimated_cost_dollars': plan.estimated_cost_dollars,
            'processing_path': plan.processing_path,
            'total_steps': plan.total_steps,
            'confidence': plan.confidence
        }
