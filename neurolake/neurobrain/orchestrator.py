"""
NeuroLake NEUROBRAIN Orchestrator
Main AI orchestration engine that coordinates all intelligence
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time

from .schema_detector import SchemaDetector, DetectedSchema
from .quality_assessor import QualityAssessor, QualityAssessment
from .transformation_suggester import TransformationSuggester, TransformationPlan, TransformationSuggestion
from .pattern_learner import PatternLearner


@dataclass
class IngestionDecision:
    """Decision made by NEUROBRAIN for data ingestion"""
    should_ingest: bool
    routing_path: str  # "express", "standard", "quality", "enrichment", "reject"
    detected_schema: DetectedSchema
    quality_assessment: QualityAssessment
    transformation_plan: TransformationPlan
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    estimated_total_time: float = 0.0
    estimated_total_cost: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of processing data through NEUROBRAIN"""
    success: bool
    processed_df: Optional[pd.DataFrame]
    original_row_count: int
    final_row_count: int
    quality_improvement: float
    transformations_applied: int
    execution_time: float
    execution_cost: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NeuroOrchestrator:
    """
    Main NEUROBRAIN orchestration engine

    This is the central AI that:
    - Analyzes incoming data
    - Makes intelligent routing decisions
    - Suggests and applies transformations
    - Learns from every execution
    - Improves over time
    """

    def __init__(self,
                 schema_detector: Optional[SchemaDetector] = None,
                 quality_assessor: Optional[QualityAssessor] = None,
                 transformation_suggester: Optional[TransformationSuggester] = None,
                 pattern_learner: Optional[PatternLearner] = None):
        """
        Initialize NEUROBRAIN orchestrator

        Args:
            schema_detector: Schema detection engine
            quality_assessor: Quality assessment engine
            transformation_suggester: Transformation suggestion engine
            pattern_learner: Pattern learning engine
        """
        self.schema_detector = schema_detector or SchemaDetector()
        self.quality_assessor = quality_assessor or QualityAssessor()
        self.pattern_learner = pattern_learner or PatternLearner()
        self.transformation_suggester = transformation_suggester or TransformationSuggester(
            pattern_learner=self.pattern_learner
        )

        # Statistics
        self.total_ingestions = 0
        self.successful_ingestions = 0
        self.total_transformations_suggested = 0
        self.total_transformations_applied = 0
        self.total_quality_improvement = 0.0

    def analyze_and_plan(self,
                        file_path: Optional[str] = None,
                        df: Optional[pd.DataFrame] = None,
                        target_use_case: str = "analytics",
                        auto_execute: bool = False) -> IngestionDecision:
        """
        Analyze data and create intelligent ingestion plan

        This is the main entry point for NEUROBRAIN intelligence

        Args:
            file_path: Path to file (if analyzing file)
            df: DataFrame (if analyzing DataFrame directly)
            target_use_case: "analytics", "ml", "reporting", "archive"
            auto_execute: Whether to automatically execute the plan

        Returns:
            IngestionDecision with complete analysis and plan
        """
        start_time = time.time()

        # Input validation
        if file_path is None and df is None:
            raise ValueError("Either file_path or df must be provided")

        # Step 1: Schema Detection
        print("🧠 NEUROBRAIN: Detecting schema...")
        if file_path:
            schema = self.schema_detector.detect_from_file(file_path)
            df = pd.read_csv(file_path, nrows=10000)  # Load sample for analysis
        else:
            schema = self.schema_detector.detect_from_dataframe(df)

        print(f"✓ Schema detected: {len(schema.columns)} columns, {schema.row_count} rows")
        print(f"  Confidence: {schema.confidence:.2%}")

        # Step 2: Quality Assessment
        print("\n🧠 NEUROBRAIN: Assessing data quality...")
        quality_assessment = self.quality_assessor.assess_dataframe(
            df,
            schema=self.schema_detector.export_schema_to_dict(schema)
        )

        print(f"✓ Quality Score: {quality_assessment.overall_score:.2%}")
        print(f"  Issues found: {len(quality_assessment.issues)}")

        # Step 3: Transformation Suggestions
        print("\n🧠 NEUROBRAIN: Suggesting transformations...")
        transformation_plan = self.transformation_suggester.suggest_transformations(
            df,
            quality_assessment=self.quality_assessor.export_to_dict(quality_assessment),
            schema=self.schema_detector.export_schema_to_dict(schema),
            target_use_case=target_use_case
        )

        print(f"✓ Suggested {len(transformation_plan.suggestions)} transformations")
        print(f"  Processing path: {transformation_plan.processing_path}")
        print(f"  Estimated time: {transformation_plan.estimated_time_seconds:.1f}s")
        print(f"  Estimated cost: ${transformation_plan.estimated_cost_dollars:.4f}")

        # Step 4: Make routing decision
        routing_path, should_ingest, warnings = self._make_routing_decision(
            schema,
            quality_assessment,
            transformation_plan
        )

        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(
            schema,
            quality_assessment,
            transformation_plan
        )

        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            schema,
            quality_assessment,
            transformation_plan
        )

        # Estimate totals
        estimated_time = (time.time() - start_time) + transformation_plan.estimated_time_seconds
        estimated_cost = transformation_plan.estimated_cost_dollars

        self.total_ingestions += 1
        self.total_transformations_suggested += len(transformation_plan.suggestions)

        decision = IngestionDecision(
            should_ingest=should_ingest,
            routing_path=routing_path,
            detected_schema=schema,
            quality_assessment=quality_assessment,
            transformation_plan=transformation_plan,
            warnings=warnings,
            recommendations=recommendations,
            estimated_total_time=estimated_time,
            estimated_total_cost=estimated_cost,
            confidence=confidence
        )

        # Auto-execute if requested
        if auto_execute and should_ingest:
            print("\n🧠 NEUROBRAIN: Auto-executing transformation plan...")
            result = self.execute_plan(df, decision)
            decision.metadata['execution_result'] = result

        return decision

    def execute_plan(self,
                    df: pd.DataFrame,
                    decision: IngestionDecision,
                    user: Optional[str] = None) -> ProcessingResult:
        """
        Execute transformation plan on data

        Args:
            df: Input DataFrame
            decision: IngestionDecision with plan
            user: User executing the plan (optional)

        Returns:
            ProcessingResult with outcome
        """
        start_time = time.time()
        original_row_count = len(df)
        errors = []
        warnings = []
        transformations_applied = 0

        # Get initial quality score
        quality_before = decision.quality_assessment.overall_score

        # Apply each transformation
        current_df = df.copy()

        print(f"\n🧠 NEUROBRAIN: Executing {len(decision.transformation_plan.suggestions)} transformations...")

        for i, suggestion in enumerate(decision.transformation_plan.suggestions):
            try:
                print(f"  [{i+1}/{len(decision.transformation_plan.suggestions)}] {suggestion.description}")

                # Execute transformation
                current_df = self.transformation_suggester.execute_transformation(
                    current_df,
                    suggestion
                )

                transformations_applied += 1

                # Record execution for learning
                self._record_transformation_execution(
                    df,
                    current_df,
                    suggestion,
                    quality_before,
                    True,
                    user
                )

            except Exception as e:
                error_msg = f"Failed to apply {suggestion.transformation_type.value}: {str(e)}"
                errors.append(error_msg)
                warnings.append(f"Skipping transformation: {suggestion.description}")
                print(f"  ⚠️  {error_msg}")

                # Record failed execution
                self._record_transformation_execution(
                    df,
                    current_df,
                    suggestion,
                    quality_before,
                    False,
                    user
                )

        # Assess quality after transformations
        quality_after_assessment = self.quality_assessor.assess_dataframe(current_df)
        quality_after = quality_after_assessment.overall_score

        quality_improvement = quality_after - quality_before

        execution_time = time.time() - start_time
        execution_cost = decision.estimated_total_cost

        self.total_transformations_applied += transformations_applied
        self.total_quality_improvement += quality_improvement

        success = len(errors) == 0 or transformations_applied > 0

        if success:
            self.successful_ingestions += 1
            print(f"\n✓ Processing complete!")
            print(f"  Quality improvement: {quality_improvement:+.2%}")
            print(f"  Transformations applied: {transformations_applied}/{len(decision.transformation_plan.suggestions)}")
        else:
            print(f"\n✗ Processing failed with {len(errors)} errors")

        return ProcessingResult(
            success=success,
            processed_df=current_df if success else None,
            original_row_count=original_row_count,
            final_row_count=len(current_df),
            quality_improvement=quality_improvement,
            transformations_applied=transformations_applied,
            execution_time=execution_time,
            execution_cost=execution_cost,
            errors=errors,
            warnings=warnings
        )

    def _make_routing_decision(self,
                               schema: DetectedSchema,
                               quality: QualityAssessment,
                               plan: TransformationPlan) -> Tuple[str, bool, List[str]]:
        """Make intelligent routing decision"""
        warnings = []

        # Check if data should be rejected
        if quality.overall_score < 0.3:
            warnings.append("Quality score too low - data may be corrupt")
            return "reject", False, warnings

        # Check for critical issues
        critical_issues = [i for i in quality.issues if i.severity.value == "critical"]
        if len(critical_issues) > 3:
            warnings.append(f"{len(critical_issues)} critical quality issues found")
            return "quality", True, warnings

        # Route based on quality and plan
        routing_path = plan.processing_path

        # Add warnings for specific paths
        if routing_path == "enrichment":
            warnings.append("Significant data quality issues require enrichment")
        elif routing_path == "quality":
            warnings.append("Data quality cleanup needed")

        return routing_path, True, warnings

    def _generate_recommendations(self,
                                 schema: DetectedSchema,
                                 quality: QualityAssessment,
                                 plan: TransformationPlan) -> List[str]:
        """Generate recommendations for the user"""
        recommendations = []

        # Schema recommendations
        if schema.confidence < 0.8:
            recommendations.append("Schema detection confidence is low - manual review recommended")

        if len(schema.primary_key_candidates) == 0:
            recommendations.append("No primary key detected - consider adding a unique identifier")

        # Quality recommendations
        if quality.overall_score < 0.7:
            recommendations.append("Quality score is below 70% - extensive cleanup recommended")

        # PII recommendations
        pii_columns = [col for col in schema.columns if col.pii_type.value != "none"]
        if pii_columns:
            recommendations.append(f"PII detected in {len(pii_columns)} columns - ensure compliance with data privacy regulations")

        # Transformation recommendations
        high_priority = [s for s in plan.suggestions if s.priority >= 8]
        if high_priority:
            recommendations.append(f"Apply {len(high_priority)} high-priority transformations immediately")

        return recommendations

    def _calculate_overall_confidence(self,
                                     schema: DetectedSchema,
                                     quality: QualityAssessment,
                                     plan: TransformationPlan) -> float:
        """Calculate overall confidence in the analysis"""
        # Weighted average of confidences
        schema_weight = 0.3
        quality_weight = 0.3
        plan_weight = 0.4

        overall = (
            schema.confidence * schema_weight +
            quality.overall_score * quality_weight +
            plan.confidence * plan_weight
        )

        return round(overall, 2)

    def _record_transformation_execution(self,
                                        df_before: pd.DataFrame,
                                        df_after: pd.DataFrame,
                                        suggestion: TransformationSuggestion,
                                        quality_before: float,
                                        success: bool,
                                        user: Optional[str]):
        """Record transformation execution for learning"""
        # Calculate quality after
        try:
            quality_after_assessment = self.quality_assessor.assess_dataframe(df_after)
            quality_after = quality_after_assessment.overall_score
        except Exception:
            quality_after = quality_before

        # Record in pattern learner
        columns = [suggestion.column] if suggestion.column else []

        self.pattern_learner.record_execution(
            transformation_type=suggestion.transformation_type.value,
            columns=columns,
            df_before=df_before,
            df_after=df_after,
            quality_score_before=quality_before,
            quality_score_after=quality_after,
            execution_time=0.1,  # Placeholder
            success=success,
            transformation_code=suggestion.code_snippet,
            user=user,
            pattern_id=suggestion.learned_from
        )

    def get_statistics(self) -> Dict:
        """Get NEUROBRAIN statistics"""
        success_rate = (
            self.successful_ingestions / self.total_ingestions
            if self.total_ingestions > 0 else 0
        )

        avg_quality_improvement = (
            self.total_quality_improvement / self.successful_ingestions
            if self.successful_ingestions > 0 else 0
        )

        pattern_stats = self.pattern_learner.get_statistics()

        return {
            'neurobrain_stats': {
                'total_ingestions': self.total_ingestions,
                'successful_ingestions': self.successful_ingestions,
                'success_rate': round(success_rate, 2),
                'total_transformations_suggested': self.total_transformations_suggested,
                'total_transformations_applied': self.total_transformations_applied,
                'avg_quality_improvement': round(avg_quality_improvement, 2)
            },
            'pattern_learning_stats': pattern_stats,
            'summary': {
                'status': 'learning' if pattern_stats['total_patterns_learned'] > 0 else 'new',
                'intelligence_level': self._calculate_intelligence_level(pattern_stats),
                'recommendations': self._get_system_recommendations(pattern_stats)
            }
        }

    def _calculate_intelligence_level(self, pattern_stats: Dict) -> str:
        """Calculate intelligence level based on learning"""
        patterns_learned = pattern_stats['total_patterns_learned']
        executions = pattern_stats['total_executions']

        if patterns_learned == 0:
            return "beginner"
        elif patterns_learned < 10:
            return "learning"
        elif patterns_learned < 50:
            return "intermediate"
        elif patterns_learned < 200:
            return "advanced"
        else:
            return "expert"

    def _get_system_recommendations(self, pattern_stats: Dict) -> List[str]:
        """Get recommendations for improving the system"""
        recommendations = []

        if pattern_stats['total_executions'] < 100:
            recommendations.append("System is still learning - more executions will improve suggestions")

        if pattern_stats['success_rate'] < 0.8:
            recommendations.append("Success rate is below 80% - review failed transformations")

        if pattern_stats['average_pattern_confidence'] < 0.7:
            recommendations.append("Pattern confidence is low - more training data needed")

        return recommendations

    def print_decision_summary(self, decision: IngestionDecision):
        """Print a formatted summary of the ingestion decision"""
        print("\n" + "="*80)
        print("🧠 NEUROBRAIN INGESTION DECISION SUMMARY")
        print("="*80)

        print(f"\n📊 DATA OVERVIEW:")
        print(f"  Rows: {decision.detected_schema.row_count:,}")
        print(f"  Columns: {len(decision.detected_schema.columns)}")
        print(f"  Size: {decision.detected_schema.estimated_size_bytes / 1024 / 1024:.2f} MB")

        print(f"\n✅ DECISION:")
        print(f"  Should Ingest: {'YES' if decision.should_ingest else 'NO'}")
        print(f"  Routing Path: {decision.routing_path.upper()}")
        print(f"  Confidence: {decision.confidence:.2%}")

        print(f"\n📈 QUALITY ASSESSMENT:")
        print(f"  Overall Score: {decision.quality_assessment.overall_score:.2%}")
        print(f"  Issues Found: {len(decision.quality_assessment.issues)}")

        print(f"\n🔧 TRANSFORMATION PLAN:")
        print(f"  Total Steps: {decision.transformation_plan.total_steps}")
        print(f"  Estimated Time: {decision.estimated_total_time:.1f}s")
        print(f"  Estimated Cost: ${decision.estimated_total_cost:.4f}")

        if decision.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in decision.warnings:
                print(f"  • {warning}")

        if decision.recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in decision.recommendations:
                print(f"  • {rec}")

        print("\n" + "="*80 + "\n")