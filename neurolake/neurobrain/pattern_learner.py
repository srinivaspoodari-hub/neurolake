"""
NeuroLake Pattern Learner
Learns patterns from transformations and improves over time
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import hashlib
import json


@dataclass
class TransformationPattern:
    """A learned transformation pattern"""
    pattern_id: str
    pattern_type: str  # "quality_fix", "derived_column", "aggregation", etc.
    source_columns: List[str]
    target_columns: List[str]
    transformation_code: str
    success_count: int = 0
    failure_count: int = 0
    total_executions: int = 0
    avg_improvement: float = 0.0  # Quality improvement
    confidence: float = 0.0
    learned_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    use_cases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    """Record of a transformation execution"""
    execution_id: str
    pattern_id: Optional[str]
    transformation_type: str
    columns: List[str]
    row_count_before: int
    row_count_after: int
    quality_score_before: float
    quality_score_after: float
    execution_time_seconds: float
    success: bool
    executed_at: datetime = field(default_factory=datetime.now)
    user: Optional[str] = None
    dataset_signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternLearner:
    """Learns patterns from transformation executions"""

    def __init__(self, storage_backend=None):
        """
        Initialize pattern learner

        Args:
            storage_backend: Optional storage backend for persistence
        """
        self.patterns: Dict[str, TransformationPattern] = {}
        self.executions: List[ExecutionRecord] = []
        self.dataset_patterns: Dict[str, List[str]] = defaultdict(list)  # dataset_sig -> pattern_ids
        self.storage_backend = storage_backend

        # Statistics
        self.total_patterns_learned = 0
        self.total_executions = 0
        self.successful_executions = 0

    def record_execution(self,
                        transformation_type: str,
                        columns: List[str],
                        df_before: pd.DataFrame,
                        df_after: pd.DataFrame,
                        quality_score_before: float,
                        quality_score_after: float,
                        execution_time: float,
                        success: bool,
                        transformation_code: str,
                        user: Optional[str] = None,
                        pattern_id: Optional[str] = None) -> ExecutionRecord:
        """
        Record a transformation execution

        Args:
            transformation_type: Type of transformation
            columns: Columns involved
            df_before: DataFrame before transformation
            df_after: DataFrame after transformation
            quality_score_before: Quality score before
            quality_score_after: Quality score after
            execution_time: Execution time in seconds
            success: Whether transformation succeeded
            transformation_code: Code that was executed
            user: User who executed (optional)
            pattern_id: If this used an existing pattern

        Returns:
            ExecutionRecord
        """
        # Generate execution ID
        execution_id = self._generate_execution_id()

        # Generate dataset signature
        dataset_sig = self._generate_dataset_signature(df_before)

        # Create execution record
        record = ExecutionRecord(
            execution_id=execution_id,
            pattern_id=pattern_id,
            transformation_type=transformation_type,
            columns=columns,
            row_count_before=len(df_before),
            row_count_after=len(df_after),
            quality_score_before=quality_score_before,
            quality_score_after=quality_score_after,
            execution_time_seconds=execution_time,
            success=success,
            user=user,
            dataset_signature=dataset_sig
        )

        self.executions.append(record)
        self.total_executions += 1

        if success:
            self.successful_executions += 1

        # If this was a successful execution, consider learning the pattern
        if success and quality_score_after > quality_score_before:
            self._learn_from_execution(
                record,
                transformation_code,
                columns,
                transformation_type,
                dataset_sig
            )

        # Update existing pattern if applicable
        if pattern_id and pattern_id in self.patterns:
            self._update_pattern(pattern_id, record)

        return record

    def _learn_from_execution(self,
                             record: ExecutionRecord,
                             transformation_code: str,
                             columns: List[str],
                             transformation_type: str,
                             dataset_sig: str):
        """Learn a new pattern from successful execution"""
        # Generate pattern ID
        pattern_id = self._generate_pattern_id(columns, transformation_type)

        # Check if pattern already exists
        if pattern_id in self.patterns:
            # Update existing pattern
            pattern = self.patterns[pattern_id]
            pattern.success_count += 1
            pattern.total_executions += 1
            pattern.last_used = datetime.now()

            # Update average improvement
            improvement = record.quality_score_after - record.quality_score_before
            pattern.avg_improvement = (
                (pattern.avg_improvement * (pattern.total_executions - 1) + improvement) /
                pattern.total_executions
            )

            # Update confidence
            pattern.confidence = self._calculate_confidence(pattern)
        else:
            # Create new pattern
            improvement = record.quality_score_after - record.quality_score_before

            pattern = TransformationPattern(
                pattern_id=pattern_id,
                pattern_type=transformation_type,
                source_columns=columns,
                target_columns=columns,  # May be different in some cases
                transformation_code=transformation_code,
                success_count=1,
                total_executions=1,
                avg_improvement=improvement,
                confidence=0.5  # Initial confidence
            )

            self.patterns[pattern_id] = pattern
            self.total_patterns_learned += 1

        # Associate pattern with dataset signature
        if pattern_id not in self.dataset_patterns[dataset_sig]:
            self.dataset_patterns[dataset_sig].append(pattern_id)

    def _update_pattern(self, pattern_id: str, record: ExecutionRecord):
        """Update existing pattern with new execution"""
        pattern = self.patterns[pattern_id]

        if record.success:
            pattern.success_count += 1
            improvement = record.quality_score_after - record.quality_score_before
            pattern.avg_improvement = (
                (pattern.avg_improvement * pattern.total_executions + improvement) /
                (pattern.total_executions + 1)
            )
        else:
            pattern.failure_count += 1

        pattern.total_executions += 1
        pattern.last_used = datetime.now()
        pattern.confidence = self._calculate_confidence(pattern)

    def get_recommended_patterns(self,
                                df: pd.DataFrame,
                                transformation_type: Optional[str] = None,
                                top_n: int = 5) -> List[TransformationPattern]:
        """
        Get recommended patterns for a dataset

        Args:
            df: DataFrame to get recommendations for
            transformation_type: Filter by transformation type (optional)
            top_n: Number of top patterns to return

        Returns:
            List of recommended patterns
        """
        dataset_sig = self._generate_dataset_signature(df)

        # Get patterns that have worked for similar datasets
        candidate_patterns = []

        # First, try patterns that worked for this exact dataset signature
        if dataset_sig in self.dataset_patterns:
            for pattern_id in self.dataset_patterns[dataset_sig]:
                if pattern_id in self.patterns:
                    candidate_patterns.append(self.patterns[pattern_id])

        # Add all other successful patterns
        for pattern in self.patterns.values():
            if pattern not in candidate_patterns:
                # Filter by transformation type if specified
                if transformation_type and pattern.pattern_type != transformation_type:
                    continue

                # Only recommend patterns with decent confidence
                if pattern.confidence >= 0.6:
                    candidate_patterns.append(pattern)

        # Score and rank patterns
        scored_patterns = [
            (pattern, self._score_pattern_relevance(pattern, df))
            for pattern in candidate_patterns
        ]

        # Sort by relevance score
        scored_patterns.sort(key=lambda x: x[1], reverse=True)

        # Return top N patterns
        return [pattern for pattern, score in scored_patterns[:top_n]]

    def _score_pattern_relevance(self, pattern: TransformationPattern, df: pd.DataFrame) -> float:
        """Score how relevant a pattern is to a dataset"""
        score = 0.0

        # Base score from pattern confidence
        score += pattern.confidence * 0.4

        # Score from average improvement
        score += min(pattern.avg_improvement, 1.0) * 0.3

        # Score from success rate
        success_rate = pattern.success_count / pattern.total_executions if pattern.total_executions > 0 else 0
        score += success_rate * 0.2

        # Score from recency
        days_since_use = (datetime.now() - pattern.last_used).days
        recency_score = max(0, 1.0 - (days_since_use / 365))  # Decay over a year
        score += recency_score * 0.1

        # Check if columns exist in dataset
        columns_match = all(col in df.columns for col in pattern.source_columns)
        if not columns_match:
            score *= 0.5  # Penalize if columns don't match

        return score

    def _calculate_confidence(self, pattern: TransformationPattern) -> float:
        """Calculate confidence score for a pattern"""
        if pattern.total_executions == 0:
            return 0.0

        # Base confidence from success rate
        success_rate = pattern.success_count / pattern.total_executions
        confidence = success_rate * 0.5

        # Boost from number of executions (more executions = more confidence)
        execution_boost = min(pattern.total_executions / 100.0, 0.3)  # Cap at 0.3
        confidence += execution_boost

        # Boost from average improvement
        improvement_boost = min(pattern.avg_improvement, 0.2)
        confidence += improvement_boost

        return round(min(confidence, 1.0), 2)

    def _generate_pattern_id(self, columns: List[str], transformation_type: str) -> str:
        """Generate unique pattern ID"""
        # Sort columns for consistency
        sorted_cols = sorted(columns)
        signature = f"{transformation_type}:{'_'.join(sorted_cols)}"
        return hashlib.md5(signature.encode()).hexdigest()[:12]

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{timestamp}_{self.total_executions}".encode()).hexdigest()[:12]

    def _generate_dataset_signature(self, df: pd.DataFrame) -> str:
        """Generate signature for dataset (based on columns and types)"""
        # Create signature from column names and types
        col_types = [(col, str(df[col].dtype)) for col in sorted(df.columns)]
        signature = json.dumps(col_types, sort_keys=True)
        return hashlib.md5(signature.encode()).hexdigest()[:12]

    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        success_rate = (
            self.successful_executions / self.total_executions
            if self.total_executions > 0 else 0
        )

        # Find most successful pattern
        most_successful = None
        if self.patterns:
            most_successful = max(
                self.patterns.values(),
                key=lambda p: p.success_count
            )

        # Average pattern confidence
        avg_confidence = (
            sum(p.confidence for p in self.patterns.values()) / len(self.patterns)
            if self.patterns else 0
        )

        return {
            'total_patterns_learned': self.total_patterns_learned,
            'active_patterns': len(self.patterns),
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'success_rate': round(success_rate, 2),
            'average_pattern_confidence': round(avg_confidence, 2),
            'most_successful_pattern': {
                'pattern_id': most_successful.pattern_id,
                'pattern_type': most_successful.pattern_type,
                'success_count': most_successful.success_count,
                'confidence': most_successful.confidence
            } if most_successful else None
        }

    def get_pattern_history(self, pattern_id: str) -> Optional[Dict]:
        """Get history of a specific pattern"""
        if pattern_id not in self.patterns:
            return None

        pattern = self.patterns[pattern_id]

        # Get all executions that used this pattern
        pattern_executions = [
            {
                'execution_id': exec.execution_id,
                'success': exec.success,
                'quality_improvement': exec.quality_score_after - exec.quality_score_before,
                'execution_time': exec.execution_time_seconds,
                'executed_at': exec.executed_at.isoformat()
            }
            for exec in self.executions
            if exec.pattern_id == pattern_id
        ]

        return {
            'pattern': {
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'source_columns': pattern.source_columns,
                'success_count': pattern.success_count,
                'failure_count': pattern.failure_count,
                'total_executions': pattern.total_executions,
                'avg_improvement': pattern.avg_improvement,
                'confidence': pattern.confidence,
                'learned_at': pattern.learned_at.isoformat(),
                'last_used': pattern.last_used.isoformat()
            },
            'executions': pattern_executions
        }

    def export_patterns(self) -> List[Dict]:
        """Export all patterns"""
        return [
            {
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'source_columns': pattern.source_columns,
                'target_columns': pattern.target_columns,
                'transformation_code': pattern.transformation_code,
                'success_count': pattern.success_count,
                'failure_count': pattern.failure_count,
                'total_executions': pattern.total_executions,
                'avg_improvement': pattern.avg_improvement,
                'confidence': pattern.confidence,
                'learned_at': pattern.learned_at.isoformat(),
                'last_used': pattern.last_used.isoformat()
            }
            for pattern in self.patterns.values()
        ]

    def import_patterns(self, patterns_data: List[Dict]):
        """Import patterns from external source"""
        for data in patterns_data:
            pattern = TransformationPattern(
                pattern_id=data['pattern_id'],
                pattern_type=data['pattern_type'],
                source_columns=data['source_columns'],
                target_columns=data['target_columns'],
                transformation_code=data['transformation_code'],
                success_count=data.get('success_count', 0),
                failure_count=data.get('failure_count', 0),
                total_executions=data.get('total_executions', 0),
                avg_improvement=data.get('avg_improvement', 0.0),
                confidence=data.get('confidence', 0.0),
                learned_at=datetime.fromisoformat(data['learned_at']),
                last_used=datetime.fromisoformat(data['last_used'])
            )
            self.patterns[pattern.pattern_id] = pattern
            self.total_patterns_learned += 1

    def clear_patterns(self, older_than_days: Optional[int] = None):
        """
        Clear patterns

        Args:
            older_than_days: Only clear patterns older than N days (optional)
        """
        if older_than_days:
            cutoff_date = datetime.now() - pd.Timedelta(days=older_than_days)
            patterns_to_remove = [
                pid for pid, pattern in self.patterns.items()
                if pattern.last_used < cutoff_date
            ]
            for pid in patterns_to_remove:
                del self.patterns[pid]
        else:
            self.patterns.clear()
            self.dataset_patterns.clear()
