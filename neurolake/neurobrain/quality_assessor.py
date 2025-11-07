"""
NeuroLake Quality Assessor
Automatic data quality assessment and scoring
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class QualityDimension(Enum):
    """Data quality dimensions"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


class QualitySeverity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """Individual quality issue"""
    dimension: QualityDimension
    severity: QualitySeverity
    column: Optional[str]
    description: str
    affected_rows: int
    affected_percentage: float
    suggestion: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Quality score for a dimension"""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    issues: List[QualityIssue] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Complete quality assessment"""
    overall_score: float  # 0.0 to 1.0
    dimension_scores: Dict[QualityDimension, QualityScore]
    issues: List[QualityIssue]
    row_count: int
    column_count: int
    assessed_at: datetime = field(default_factory=datetime.now)
    suggestions: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class QualityAssessor:
    """Automatic data quality assessment engine"""

    # Default dimension weights
    DEFAULT_WEIGHTS = {
        QualityDimension.COMPLETENESS: 0.25,
        QualityDimension.ACCURACY: 0.20,
        QualityDimension.CONSISTENCY: 0.20,
        QualityDimension.TIMELINESS: 0.10,
        QualityDimension.UNIQUENESS: 0.15,
        QualityDimension.VALIDITY: 0.10
    }

    def __init__(self, weights: Optional[Dict[QualityDimension, float]] = None):
        """
        Initialize quality assessor

        Args:
            weights: Custom weights for quality dimensions
        """
        self.weights = weights or self.DEFAULT_WEIGHTS

    def assess_dataframe(self, df: pd.DataFrame,
                        schema: Optional[Dict] = None,
                        expected_values: Optional[Dict[str, List]] = None) -> QualityAssessment:
        """
        Assess data quality of a DataFrame

        Args:
            df: pandas DataFrame to assess
            schema: Expected schema for validation
            expected_values: Expected values for specific columns

        Returns:
            QualityAssessment with scores and issues
        """
        dimension_scores = {}
        all_issues = []

        # Assess completeness
        completeness_score, completeness_issues = self._assess_completeness(df)
        dimension_scores[QualityDimension.COMPLETENESS] = QualityScore(
            dimension=QualityDimension.COMPLETENESS,
            score=completeness_score,
            weight=self.weights[QualityDimension.COMPLETENESS],
            issues=completeness_issues
        )
        all_issues.extend(completeness_issues)

        # Assess accuracy
        accuracy_score, accuracy_issues = self._assess_accuracy(df, expected_values)
        dimension_scores[QualityDimension.ACCURACY] = QualityScore(
            dimension=QualityDimension.ACCURACY,
            score=accuracy_score,
            weight=self.weights[QualityDimension.ACCURACY],
            issues=accuracy_issues
        )
        all_issues.extend(accuracy_issues)

        # Assess consistency
        consistency_score, consistency_issues = self._assess_consistency(df)
        dimension_scores[QualityDimension.CONSISTENCY] = QualityScore(
            dimension=QualityDimension.CONSISTENCY,
            score=consistency_score,
            weight=self.weights[QualityDimension.CONSISTENCY],
            issues=consistency_issues
        )
        all_issues.extend(consistency_issues)

        # Assess timeliness
        timeliness_score, timeliness_issues = self._assess_timeliness(df)
        dimension_scores[QualityDimension.TIMELINESS] = QualityScore(
            dimension=QualityDimension.TIMELINESS,
            score=timeliness_score,
            weight=self.weights[QualityDimension.TIMELINESS],
            issues=timeliness_issues
        )
        all_issues.extend(timeliness_issues)

        # Assess uniqueness
        uniqueness_score, uniqueness_issues = self._assess_uniqueness(df)
        dimension_scores[QualityDimension.UNIQUENESS] = QualityScore(
            dimension=QualityDimension.UNIQUENESS,
            score=uniqueness_score,
            weight=self.weights[QualityDimension.UNIQUENESS],
            issues=uniqueness_issues
        )
        all_issues.extend(uniqueness_issues)

        # Assess validity
        validity_score, validity_issues = self._assess_validity(df, schema)
        dimension_scores[QualityDimension.VALIDITY] = QualityScore(
            dimension=QualityDimension.VALIDITY,
            score=validity_score,
            weight=self.weights[QualityDimension.VALIDITY],
            issues=validity_issues
        )
        all_issues.extend(validity_issues)

        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)

        # Generate suggestions and recommended actions
        suggestions = self._generate_suggestions(all_issues)
        recommended_actions = self._generate_recommended_actions(all_issues, overall_score)

        return QualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            row_count=len(df),
            column_count=len(df.columns),
            suggestions=suggestions,
            recommended_actions=recommended_actions
        )

    def _assess_completeness(self, df: pd.DataFrame) -> tuple[float, List[QualityIssue]]:
        """Assess data completeness (no missing values)"""
        issues = []
        total_cells = df.size
        null_cells = df.isnull().sum().sum()

        # Check each column
        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                null_pct = (null_count / len(df)) * 100

                severity = QualitySeverity.LOW
                if null_pct > 50:
                    severity = QualitySeverity.CRITICAL
                elif null_pct > 20:
                    severity = QualitySeverity.HIGH
                elif null_pct > 10:
                    severity = QualitySeverity.MEDIUM

                issues.append(QualityIssue(
                    dimension=QualityDimension.COMPLETENESS,
                    severity=severity,
                    column=col,
                    description=f"Column '{col}' has {null_count} null values ({null_pct:.1f}%)",
                    affected_rows=int(null_count),
                    affected_percentage=null_pct,
                    suggestion=f"Fill nulls in '{col}' with mean/median/mode or drop rows"
                ))

        # Calculate score
        completeness_score = 1.0 - (null_cells / total_cells) if total_cells > 0 else 1.0
        return round(completeness_score, 4), issues

    def _assess_accuracy(self, df: pd.DataFrame,
                        expected_values: Optional[Dict[str, List]] = None) -> tuple[float, List[QualityIssue]]:
        """Assess data accuracy"""
        issues = []

        # Check for outliers in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            outliers = self._detect_outliers(df[col])
            if outliers > 0:
                outlier_pct = (outliers / len(df)) * 100

                severity = QualitySeverity.LOW
                if outlier_pct > 10:
                    severity = QualitySeverity.MEDIUM
                if outlier_pct > 20:
                    severity = QualitySeverity.HIGH

                issues.append(QualityIssue(
                    dimension=QualityDimension.ACCURACY,
                    severity=severity,
                    column=col,
                    description=f"Column '{col}' has {outliers} outliers ({outlier_pct:.1f}%)",
                    affected_rows=outliers,
                    affected_percentage=outlier_pct,
                    suggestion=f"Review and handle outliers in '{col}' (cap, remove, or keep)"
                ))

        # Check expected values if provided
        if expected_values:
            for col, expected in expected_values.items():
                if col in df.columns:
                    invalid = df[~df[col].isin(expected)].shape[0]
                    if invalid > 0:
                        invalid_pct = (invalid / len(df)) * 100
                        issues.append(QualityIssue(
                            dimension=QualityDimension.ACCURACY,
                            severity=QualitySeverity.HIGH,
                            column=col,
                            description=f"Column '{col}' has {invalid} values not in expected set",
                            affected_rows=invalid,
                            affected_percentage=invalid_pct,
                            suggestion=f"Validate and correct values in '{col}'"
                        ))

        # Calculate score based on issues
        accuracy_score = 1.0 - (len(issues) * 0.1)
        return max(0.0, min(1.0, accuracy_score)), issues

    def _assess_consistency(self, df: pd.DataFrame) -> tuple[float, List[QualityIssue]]:
        """Assess data consistency"""
        issues = []

        # Check for inconsistent formats in string columns
        string_cols = df.select_dtypes(include=['object']).columns
        for col in string_cols:
            # Check for mixed case inconsistency
            if df[col].dtype == 'object':
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    # Check case consistency
                    upper_count = non_null.str.isupper().sum()
                    lower_count = non_null.str.islower().sum()
                    mixed_count = len(non_null) - upper_count - lower_count

                    if mixed_count > len(non_null) * 0.1:  # More than 10% mixed
                        issues.append(QualityIssue(
                            dimension=QualityDimension.CONSISTENCY,
                            severity=QualitySeverity.LOW,
                            column=col,
                            description=f"Column '{col}' has inconsistent casing",
                            affected_rows=int(mixed_count),
                            affected_percentage=(mixed_count / len(non_null)) * 100,
                            suggestion=f"Standardize casing in '{col}' (e.g., .str.lower())"
                        ))

                    # Check for leading/trailing whitespace
                    whitespace_count = (non_null != non_null.str.strip()).sum()
                    if whitespace_count > 0:
                        issues.append(QualityIssue(
                            dimension=QualityDimension.CONSISTENCY,
                            severity=QualitySeverity.LOW,
                            column=col,
                            description=f"Column '{col}' has {whitespace_count} values with whitespace",
                            affected_rows=int(whitespace_count),
                            affected_percentage=(whitespace_count / len(non_null)) * 100,
                            suggestion=f"Strip whitespace from '{col}'"
                        ))

        consistency_score = 1.0 - (len(issues) * 0.05)
        return max(0.0, min(1.0, consistency_score)), issues

    def _assess_timeliness(self, df: pd.DataFrame) -> tuple[float, List[QualityIssue]]:
        """Assess data timeliness"""
        issues = []

        # Check for date columns
        date_cols = df.select_dtypes(include=['datetime64']).columns
        for col in date_cols:
            non_null = df[col].dropna()
            if len(non_null) > 0:
                max_date = non_null.max()
                now = pd.Timestamp.now()

                # Check if data is stale (older than 30 days)
                if (now - max_date).days > 30:
                    issues.append(QualityIssue(
                        dimension=QualityDimension.TIMELINESS,
                        severity=QualitySeverity.MEDIUM,
                        column=col,
                        description=f"Column '{col}' has stale data (latest: {max_date.date()})",
                        affected_rows=len(df),
                        affected_percentage=100.0,
                        suggestion=f"Update data in '{col}' - latest record is {(now - max_date).days} days old"
                    ))

                # Check for future dates
                future_count = (non_null > now).sum()
                if future_count > 0:
                    issues.append(QualityIssue(
                        dimension=QualityDimension.TIMELINESS,
                        severity=QualitySeverity.HIGH,
                        column=col,
                        description=f"Column '{col}' has {future_count} future dates",
                        affected_rows=int(future_count),
                        affected_percentage=(future_count / len(non_null)) * 100,
                        suggestion=f"Validate and correct future dates in '{col}'"
                    ))

        timeliness_score = 1.0 - (len(issues) * 0.15)
        return max(0.0, min(1.0, timeliness_score)), issues

    def _assess_uniqueness(self, df: pd.DataFrame) -> tuple[float, List[QualityIssue]]:
        """Assess data uniqueness (no duplicates)"""
        issues = []

        # Check for duplicate rows
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            dup_pct = (duplicate_rows / len(df)) * 100

            severity = QualitySeverity.LOW
            if dup_pct > 10:
                severity = QualitySeverity.MEDIUM
            if dup_pct > 20:
                severity = QualitySeverity.HIGH

            issues.append(QualityIssue(
                dimension=QualityDimension.UNIQUENESS,
                severity=severity,
                column=None,
                description=f"Dataset has {duplicate_rows} duplicate rows ({dup_pct:.1f}%)",
                affected_rows=int(duplicate_rows),
                affected_percentage=dup_pct,
                suggestion="Remove duplicate rows using .drop_duplicates()"
            ))

        # Check for duplicate values in columns that should be unique
        for col in df.columns:
            # Heuristic: columns with 'id' in name should be unique
            if 'id' in col.lower():
                duplicate_values = df[col].duplicated().sum()
                if duplicate_values > 0:
                    dup_pct = (duplicate_values / len(df)) * 100
                    issues.append(QualityIssue(
                        dimension=QualityDimension.UNIQUENESS,
                        severity=QualitySeverity.HIGH,
                        column=col,
                        description=f"Column '{col}' (likely ID) has {duplicate_values} duplicates",
                        affected_rows=int(duplicate_values),
                        affected_percentage=dup_pct,
                        suggestion=f"Ensure '{col}' has unique values or review data source"
                    ))

        uniqueness_score = 1.0 - (duplicate_rows / len(df)) if len(df) > 0 else 1.0
        return round(uniqueness_score, 4), issues

    def _assess_validity(self, df: pd.DataFrame,
                        schema: Optional[Dict] = None) -> tuple[float, List[QualityIssue]]:
        """Assess data validity against schema/rules"""
        issues = []

        # Check for invalid email formats
        for col in df.columns:
            if 'email' in col.lower():
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                non_null = df[col].dropna().astype(str)
                if len(non_null) > 0:
                    invalid = ~non_null.str.match(email_pattern)
                    invalid_count = invalid.sum()
                    if invalid_count > 0:
                        invalid_pct = (invalid_count / len(non_null)) * 100
                        issues.append(QualityIssue(
                            dimension=QualityDimension.VALIDITY,
                            severity=QualitySeverity.MEDIUM,
                            column=col,
                            description=f"Column '{col}' has {invalid_count} invalid email formats",
                            affected_rows=int(invalid_count),
                            affected_percentage=invalid_pct,
                            suggestion=f"Validate and correct email formats in '{col}'"
                        ))

        # Check for negative values in columns that should be positive
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['amount', 'price', 'quantity', 'count', 'age']):
                if pd.api.types.is_numeric_dtype(df[col]):
                    negative_count = (df[col] < 0).sum()
                    if negative_count > 0:
                        neg_pct = (negative_count / len(df)) * 100
                        issues.append(QualityIssue(
                            dimension=QualityDimension.VALIDITY,
                            severity=QualitySeverity.MEDIUM,
                            column=col,
                            description=f"Column '{col}' has {negative_count} negative values",
                            affected_rows=int(negative_count),
                            affected_percentage=neg_pct,
                            suggestion=f"Review negative values in '{col}' - may be invalid"
                        ))

        validity_score = 1.0 - (len(issues) * 0.1)
        return max(0.0, min(1.0, validity_score)), issues

    def _detect_outliers(self, series: pd.Series) -> int:
        """Detect outliers using IQR method"""
        if len(series) < 4:
            return 0

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        outliers = ((series < lower_bound) | (series > upper_bound)).sum()
        return int(outliers)

    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, QualityScore]) -> float:
        """Calculate weighted overall quality score"""
        total_score = 0.0
        total_weight = 0.0

        for dimension, score_obj in dimension_scores.items():
            total_score += score_obj.score * score_obj.weight
            total_weight += score_obj.weight

        overall = total_score / total_weight if total_weight > 0 else 0.0
        return round(overall, 4)

    def _generate_suggestions(self, issues: List[QualityIssue]) -> List[str]:
        """Generate actionable suggestions"""
        suggestions = []

        # Group by severity
        critical = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
        high = [i for i in issues if i.severity == QualitySeverity.HIGH]

        if critical:
            suggestions.append(f"CRITICAL: Address {len(critical)} critical issues immediately")
        if high:
            suggestions.append(f"HIGH: Review and fix {len(high)} high-priority issues")

        # Add specific suggestions from issues
        for issue in issues[:5]:  # Top 5 issues
            suggestions.append(issue.suggestion)

        return suggestions

    def _generate_recommended_actions(self, issues: List[QualityIssue],
                                     overall_score: float) -> List[str]:
        """Generate recommended actions based on quality"""
        actions = []

        if overall_score >= 0.95:
            actions.append("Quality is excellent - proceed to production")
        elif overall_score >= 0.85:
            actions.append("Quality is good - minor cleanup recommended")
            actions.append("Review and address low-priority issues")
        elif overall_score >= 0.70:
            actions.append("Quality is fair - significant cleanup needed")
            actions.append("Address all high-priority issues before production")
        else:
            actions.append("Quality is poor - extensive data cleaning required")
            actions.append("DO NOT proceed to production without cleanup")
            actions.append("Consider data source quality issues")

        return actions

    def export_to_dict(self, assessment: QualityAssessment) -> Dict:
        """Export assessment to dictionary"""
        return {
            'overall_score': assessment.overall_score,
            'dimension_scores': {
                dim.value: {
                    'score': score.score,
                    'weight': score.weight,
                    'issues_count': len(score.issues)
                }
                for dim, score in assessment.dimension_scores.items()
            },
            'issues': [
                {
                    'dimension': issue.dimension.value,
                    'severity': issue.severity.value,
                    'column': issue.column,
                    'description': issue.description,
                    'affected_rows': issue.affected_rows,
                    'affected_percentage': issue.affected_percentage,
                    'suggestion': issue.suggestion
                }
                for issue in assessment.issues
            ],
            'row_count': assessment.row_count,
            'column_count': assessment.column_count,
            'assessed_at': assessment.assessed_at.isoformat(),
            'suggestions': assessment.suggestions,
            'recommended_actions': assessment.recommended_actions
        }