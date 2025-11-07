"""
NeuroLake Smart Ingestion
Intelligent data ingestion with auto-detection and routing
"""

import pandas as pd
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib

from ..neurobrain.orchestrator import NeuroOrchestrator
from ..neurobrain.schema_detector import DetectedSchema
from ..neurobrain.quality_assessor import QualityAssessment
from ..nuic.catalog_engine import NUICEngine, LineageType


@dataclass
class IngestionConfig:
    """Configuration for ingestion"""
    target_use_case: str = "analytics"  # "analytics", "ml", "reporting", "archive"
    auto_execute_transformations: bool = True
    enable_cataloging: bool = True
    enable_lineage: bool = True
    enable_quality_checks: bool = True
    quality_threshold: float = 0.5  # Minimum quality score to accept
    max_file_size_mb: int = 1000
    enable_pii_detection: bool = True
    enable_auto_partitioning: bool = True
    partition_column: Optional[str] = None
    storage_location: str = "C:/NeuroLake/buckets/raw-data"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Result of ingestion operation"""
    success: bool
    ingestion_id: str
    file_path: Optional[str]
    dataset_name: str
    detected_schema: DetectedSchema
    quality_assessment: QualityAssessment
    routing_path: str
    rows_ingested: int
    rows_rejected: int
    transformations_applied: int
    catalog_entry_created: bool
    lineage_tracked: bool
    ingestion_time_seconds: float
    storage_location: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SmartIngestor:
    """Smart data ingestion with AI-powered analysis"""

    def __init__(self,
                 orchestrator: Optional[NeuroOrchestrator] = None,
                 config: Optional[IngestionConfig] = None,
                 nuic_engine: Optional[NUICEngine] = None):
        """
        Initialize Smart Ingestor

        Args:
            orchestrator: NEUROBRAIN orchestrator
            config: Ingestion configuration
            nuic_engine: NUIC catalog engine (creates one if not provided)
        """
        self.orchestrator = orchestrator or NeuroOrchestrator()
        self.config = config or IngestionConfig()
        self.nuic = nuic_engine or NUICEngine()

        # Statistics
        self.total_ingestions = 0
        self.successful_ingestions = 0
        self.total_rows_ingested = 0
        self.total_rows_rejected = 0

    def ingest(self,
               source: Union[str, pd.DataFrame],
               dataset_name: Optional[str] = None,
               config_override: Optional[Dict] = None) -> IngestionResult:
        """
        Ingest data with automatic detection and intelligent processing

        Args:
            source: File path or DataFrame
            dataset_name: Name for the dataset (optional)
            config_override: Override config parameters (optional)

        Returns:
            IngestionResult with complete outcome
        """
        start_time = datetime.now()

        # Apply config overrides
        config = self._apply_config_overrides(config_override)

        print(f"\n{'='*80}")
        print(f"🚀 NEUROLAKE SMART INGESTION")
        print(f"{'='*80}\n")

        # Generate ingestion ID
        ingestion_id = self._generate_ingestion_id()

        # Determine source type and load data
        if isinstance(source, str):
            file_path = source
            dataset_name = dataset_name or Path(file_path).stem

            # Validate file
            validation_result = self._validate_file(file_path, config)
            if not validation_result['valid']:
                return self._create_failed_result(
                    ingestion_id,
                    dataset_name,
                    validation_result['errors']
                )

            print(f"📄 Source: {file_path}")
        else:
            file_path = None
            dataset_name = dataset_name or f"dataframe_{ingestion_id}"
            print(f"📊 Source: In-memory DataFrame")

        print(f"🏷️  Dataset: {dataset_name}")
        print(f"🎯 Target Use Case: {config.target_use_case}")

        # Step 1: NEUROBRAIN Analysis
        print(f"\n{'─'*80}")
        print("STEP 1: NEUROBRAIN ANALYSIS")
        print(f"{'─'*80}")

        decision = self.orchestrator.analyze_and_plan(
            file_path=file_path if isinstance(source, str) else None,
            df=source if isinstance(source, pd.DataFrame) else None,
            target_use_case=config.target_use_case,
            auto_execute=False
        )

        # Print decision summary
        self.orchestrator.print_decision_summary(decision)

        # Check if ingestion should proceed
        if not decision.should_ingest:
            return self._create_rejected_result(
                ingestion_id,
                dataset_name,
                decision
            )

        # Check quality threshold
        if decision.quality_assessment.overall_score < config.quality_threshold:
            warning = f"Quality score {decision.quality_assessment.overall_score:.2%} below threshold {config.quality_threshold:.2%}"
            print(f"\n⚠️  {warning}")

            if not config.auto_execute_transformations:
                return self._create_rejected_result(
                    ingestion_id,
                    dataset_name,
                    decision,
                    [warning]
                )

        # Step 2: Execute Transformations
        print(f"\n{'─'*80}")
        print("STEP 2: TRANSFORMATION EXECUTION")
        print(f"{'─'*80}")

        # Load full dataset if needed
        if file_path:
            df = pd.read_csv(file_path)  # Load full dataset
        else:
            df = source

        processing_result = None
        if config.auto_execute_transformations:
            processing_result = self.orchestrator.execute_plan(df, decision)

            if processing_result.success:
                df = processing_result.processed_df
            else:
                return self._create_failed_result(
                    ingestion_id,
                    dataset_name,
                    processing_result.errors
                )

        # Step 3: Store Data
        print(f"\n{'─'*80}")
        print("STEP 3: DATA STORAGE")
        print(f"{'─'*80}")

        storage_location = self._store_data(
            df,
            dataset_name,
            decision.routing_path,
            config
        )

        print(f"✓ Data stored: {storage_location}")

        # Step 4: Catalog Registration
        catalog_created = False
        if config.enable_cataloging:
            print(f"\n{'─'*80}")
            print("STEP 4: CATALOG REGISTRATION")
            print(f"{'─'*80}")

            catalog_created = self._register_in_catalog(
                ingestion_id,
                dataset_name,
                decision,
                storage_location,
                df
            )

            if catalog_created:
                print("✓ Catalog entry created")

        # Step 5: Lineage Tracking
        lineage_tracked = False
        if config.enable_lineage:
            print(f"\n{'─'*80}")
            print("STEP 5: LINEAGE TRACKING")
            print(f"{'─'*80}")

            lineage_tracked = self._track_lineage(
                ingestion_id,
                dataset_name,
                file_path,
                decision,
                processing_result
            )

            if lineage_tracked:
                print("✓ Lineage tracked")

        # Calculate statistics
        rows_ingested = len(df)
        rows_rejected = 0
        transformations_applied = processing_result.transformations_applied if processing_result else 0

        ingestion_time = (datetime.now() - start_time).total_seconds()

        # Update statistics
        self.total_ingestions += 1
        self.successful_ingestions += 1
        self.total_rows_ingested += rows_ingested

        # Create result
        result = IngestionResult(
            success=True,
            ingestion_id=ingestion_id,
            file_path=file_path,
            dataset_name=dataset_name,
            detected_schema=decision.detected_schema,
            quality_assessment=decision.quality_assessment,
            routing_path=decision.routing_path,
            rows_ingested=rows_ingested,
            rows_rejected=rows_rejected,
            transformations_applied=transformations_applied,
            catalog_entry_created=catalog_created,
            lineage_tracked=lineage_tracked,
            ingestion_time_seconds=ingestion_time,
            storage_location=storage_location,
            warnings=decision.warnings
        )

        # Print final summary
        self._print_ingestion_summary(result)

        return result

    def _validate_file(self, file_path: str, config: IngestionConfig) -> Dict:
        """Validate file before ingestion"""
        errors = []

        # Check if file exists
        if not os.path.exists(file_path):
            errors.append(f"File not found: {file_path}")
            return {'valid': False, 'errors': errors}

        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > config.max_file_size_mb:
            errors.append(f"File size {file_size_mb:.1f}MB exceeds limit {config.max_file_size_mb}MB")

        # Check file extension
        valid_extensions = ['.csv', '.json', '.parquet', '.xlsx', '.xls']
        if not any(file_path.endswith(ext) for ext in valid_extensions):
            errors.append(f"Unsupported file type. Supported: {', '.join(valid_extensions)}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'file_size_mb': file_size_mb
        }

    def _store_data(self,
                    df: pd.DataFrame,
                    dataset_name: str,
                    routing_path: str,
                    config: IngestionConfig) -> str:
        """Store data based on routing path"""
        # Create storage directory structure
        base_path = Path(config.storage_location)

        # Route to appropriate zone
        if routing_path == "express":
            zone_path = base_path / "express"
        elif routing_path == "standard":
            zone_path = base_path / "standard"
        elif routing_path == "quality":
            zone_path = base_path / "quality"
        elif routing_path == "enrichment":
            zone_path = base_path / "enrichment"
        else:
            zone_path = base_path / "default"

        zone_path.mkdir(parents=True, exist_ok=True)

        # Auto-partition if enabled
        if config.enable_auto_partitioning and config.partition_column:
            # Save partitioned
            for partition_value in df[config.partition_column].unique():
                partition_df = df[df[config.partition_column] == partition_value]
                partition_path = zone_path / f"{config.partition_column}={partition_value}"
                partition_path.mkdir(exist_ok=True)

                file_path = partition_path / f"{dataset_name}.parquet"
                partition_df.to_parquet(file_path, index=False)

            return str(zone_path / f"{dataset_name}_partitioned")
        else:
            # Save as single file
            file_path = zone_path / f"{dataset_name}.parquet"
            df.to_parquet(file_path, index=False)
            return str(file_path)

    def _register_in_catalog(self,
                            ingestion_id: str,
                            dataset_name: str,
                            decision,
                            storage_location: str,
                            df: pd.DataFrame) -> bool:
        """Register dataset in NUIC catalog with full database backend"""
        try:
            # Prepare schema columns for NUIC
            schema_columns = [
                {
                    'name': col.name,
                    'type': col.data_type.value,
                    'nullable': col.nullable,
                    'pii': col.pii_type.value,
                    'metadata': {
                        'confidence': col.confidence,
                        'sample_values': col.sample_values[:5] if hasattr(col, 'sample_values') else []
                    }
                }
                for col in decision.detected_schema.columns
            ]

            # Generate tags
            tags = self._generate_auto_tags(decision)

            # Register in NUIC database
            success = self.nuic.register_dataset(
                dataset_id=ingestion_id,
                dataset_name=dataset_name,
                schema_columns=schema_columns,
                quality_score=decision.quality_assessment.overall_score,
                row_count=len(df),
                size_bytes=decision.detected_schema.estimated_size_bytes,
                storage_location=storage_location,
                routing_path=decision.routing_path,
                tags=tags,
                metadata={
                    'source_format': decision.detected_schema.format,
                    'encoding': decision.detected_schema.encoding,
                    'delimiter': decision.detected_schema.delimiter,
                    'use_case': decision.target_use_case
                },
                user="neurolake_ingestion"
            )

            # Record initial quality metrics
            if success:
                dimension_scores = {
                    'completeness': decision.quality_assessment.dimension_scores.get('completeness', 0),
                    'accuracy': decision.quality_assessment.dimension_scores.get('accuracy', 0),
                    'consistency': decision.quality_assessment.dimension_scores.get('consistency', 0),
                    'timeliness': decision.quality_assessment.dimension_scores.get('timeliness', 0),
                    'uniqueness': decision.quality_assessment.dimension_scores.get('uniqueness', 0),
                    'validity': decision.quality_assessment.dimension_scores.get('validity', 0)
                }

                self.nuic.record_quality_metric(
                    dataset_id=ingestion_id,
                    overall_score=decision.quality_assessment.overall_score,
                    dimension_scores=dimension_scores,
                    issues_found=len(decision.quality_assessment.issues),
                    metadata={
                        'issues': [
                            {
                                'dimension': issue.dimension.value,
                                'severity': issue.severity.value,
                                'description': issue.description
                            }
                            for issue in decision.quality_assessment.issues[:10]  # Limit to 10 issues
                        ]
                    }
                )

            return success

        except Exception as e:
            print(f"⚠️  Catalog registration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _track_lineage(self,
                      ingestion_id: str,
                      dataset_name: str,
                      source_file: Optional[str],
                      decision,
                      processing_result) -> bool:
        """Track data lineage with graph-based system"""
        try:
            # For raw ingestion from file, we don't have a source dataset yet
            # This creates the initial lineage entry for the dataset

            # If we have transformation results, track those
            if processing_result and processing_result.transformations_applied:
                # Build transformation code summary
                transformation_code = "\n".join([
                    f"# {t.transformation_type.value}: {t.description}"
                    for t in decision.transformation_plan.suggestions[:10]
                ])

                # Track column-level lineage for transformations
                column_mappings = []
                for transform in decision.transformation_plan.suggestions:
                    if transform.column:
                        # For now, column maps to itself after transformation
                        # In future, track actual column derivations
                        column_mappings.append((
                            transform.column,  # source column
                            transform.column,  # target column (same for in-place transforms)
                            transform.transformation_type.value  # transformation applied
                        ))

                # Note: For initial ingestion, we would need a "raw source" dataset ID
                # For now, we'll create a pseudo-source ID based on file path
                if source_file:
                    source_id = f"raw_file_{hashlib.md5(source_file.encode()).hexdigest()[:16]}"
                else:
                    source_id = f"raw_dataframe_{ingestion_id}_source"

                # Track lineage edge from source to ingested dataset
                success = self.nuic.track_lineage(
                    source_dataset_id=source_id,
                    target_dataset_id=ingestion_id,
                    lineage_type=LineageType.TRANSFORMED_TO,
                    transformation_code=transformation_code,
                    column_mappings=column_mappings[:50],  # Limit to 50 columns
                    metadata={
                        'source_file': source_file or "in_memory_dataframe",
                        'transformations_applied': processing_result.transformations_applied,
                        'quality_improvement': processing_result.quality_improvement,
                        'execution_time': processing_result.execution_time,
                        'use_case': decision.target_use_case
                    }
                )

                return success
            else:
                # No transformations, still successful lineage tracking
                return True

        except Exception as e:
            print(f"⚠️  Lineage tracking failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_auto_tags(self, decision) -> List[str]:
        """Generate automatic tags based on analysis"""
        tags = []

        # Quality tags
        if decision.quality_assessment.overall_score >= 0.9:
            tags.append("high_quality")
        elif decision.quality_assessment.overall_score < 0.6:
            tags.append("low_quality")

        # PII tags
        pii_columns = [col for col in decision.detected_schema.columns if col.pii_type.value != "none"]
        if pii_columns:
            tags.append("contains_pii")

        # Size tags
        if decision.detected_schema.row_count > 1000000:
            tags.append("large_dataset")

        # Routing tags
        tags.append(f"path_{decision.routing_path}")

        return tags

    def _generate_ingestion_id(self) -> str:
        """Generate unique ingestion ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_hash = hashlib.md5(f"{timestamp}_{self.total_ingestions}".encode()).hexdigest()[:8]
        return f"ing_{timestamp}_{random_hash}"

    def _apply_config_overrides(self, overrides: Optional[Dict]) -> IngestionConfig:
        """Apply configuration overrides"""
        if not overrides:
            return self.config

        config_dict = {
            'target_use_case': overrides.get('target_use_case', self.config.target_use_case),
            'auto_execute_transformations': overrides.get('auto_execute', self.config.auto_execute_transformations),
            'enable_cataloging': overrides.get('catalog', self.config.enable_cataloging),
            'enable_lineage': overrides.get('lineage', self.config.enable_lineage),
            'quality_threshold': overrides.get('quality_threshold', self.config.quality_threshold),
            'storage_location': overrides.get('storage', self.config.storage_location)
        }

        return IngestionConfig(**config_dict)

    def _create_failed_result(self,
                             ingestion_id: str,
                             dataset_name: str,
                             errors: List[str]) -> IngestionResult:
        """Create failed result"""
        return IngestionResult(
            success=False,
            ingestion_id=ingestion_id,
            file_path=None,
            dataset_name=dataset_name,
            detected_schema=None,
            quality_assessment=None,
            routing_path="rejected",
            rows_ingested=0,
            rows_rejected=0,
            transformations_applied=0,
            catalog_entry_created=False,
            lineage_tracked=False,
            ingestion_time_seconds=0,
            storage_location="",
            errors=errors
        )

    def _create_rejected_result(self,
                               ingestion_id: str,
                               dataset_name: str,
                               decision,
                               additional_warnings: Optional[List[str]] = None) -> IngestionResult:
        """Create rejected result"""
        warnings = decision.warnings.copy()
        if additional_warnings:
            warnings.extend(additional_warnings)

        return IngestionResult(
            success=False,
            ingestion_id=ingestion_id,
            file_path=None,
            dataset_name=dataset_name,
            detected_schema=decision.detected_schema,
            quality_assessment=decision.quality_assessment,
            routing_path="rejected",
            rows_ingested=0,
            rows_rejected=decision.detected_schema.row_count,
            transformations_applied=0,
            catalog_entry_created=False,
            lineage_tracked=False,
            ingestion_time_seconds=0,
            storage_location="",
            warnings=warnings
        )

    def _print_ingestion_summary(self, result: IngestionResult):
        """Print ingestion summary"""
        print(f"\n{'='*80}")
        print(f"✅ INGESTION COMPLETE")
        print(f"{'='*80}\n")

        print(f"📊 SUMMARY:")
        print(f"  Ingestion ID: {result.ingestion_id}")
        print(f"  Dataset: {result.dataset_name}")
        print(f"  Rows Ingested: {result.rows_ingested:,}")
        print(f"  Quality Score: {result.quality_assessment.overall_score:.2%}")
        print(f"  Routing Path: {result.routing_path}")
        print(f"  Transformations: {result.transformations_applied}")
        print(f"  Execution Time: {result.ingestion_time_seconds:.1f}s")
        print(f"  Storage: {result.storage_location}")
        print(f"  Cataloged: {'Yes' if result.catalog_entry_created else 'No'}")
        print(f"  Lineage Tracked: {'Yes' if result.lineage_tracked else 'No'}")

        print(f"\n{'='*80}\n")

    def get_statistics(self) -> Dict:
        """Get ingestion statistics"""
        success_rate = (
            self.successful_ingestions / self.total_ingestions
            if self.total_ingestions > 0 else 0
        )

        return {
            'total_ingestions': self.total_ingestions,
            'successful_ingestions': self.successful_ingestions,
            'success_rate': round(success_rate, 2),
            'total_rows_ingested': self.total_rows_ingested,
            'total_rows_rejected': self.total_rows_rejected
        }