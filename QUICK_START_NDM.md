# NeuroLake NDM - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

```bash
pip install pandas numpy scikit-learn chardet openpyxl
```

### 2. Basic Usage - One Line!

```python
from neurolake.ingestion import SmartIngestor

# Ingest any CSV/JSON/Parquet file
ingestor = SmartIngestor()
result = ingestor.ingest("your_data.csv", "my_dataset")

# Done! Data is now:
# ✅ Schema detected
# ✅ Quality assessed
# ✅ Cleaned & transformed
# ✅ Cataloged
# ✅ Lineage tracked
# ✅ Ready for analytics
```

### 3. Check Results

```python
if result.success:
    print(f"✅ Ingested {result.rows_ingested:,} rows")
    print(f"📊 Quality Score: {result.quality_assessment.overall_score:.2%}")
    print(f"🛣️  Path: {result.routing_path}")
    print(f"🔧 Transformations: {result.transformations_applied}")
else:
    print(f"❌ Errors: {result.errors}")
```

## 📖 Common Use Cases

### Analytics Pipeline

```python
from neurolake.ingestion import SmartIngestor, IngestionConfig

# Configure for analytics
config = IngestionConfig(target_use_case="analytics")
ingestor = SmartIngestor()

# Ingest
result = ingestor.ingest(
    source="sales_data.csv",
    dataset_name="sales",
    config_override={'target_use_case': 'analytics'}
)

# Data is now optimized for analytics!
```

### Machine Learning

```python
# Configure for ML
config = IngestionConfig(
    target_use_case="ml",
    auto_execute_transformations=True
)

ingestor = SmartIngestor()
result = ingestor.ingest(source="training_data.csv", dataset_name="ml_dataset")

# Data is now:
# - Standardized/normalized
# - Missing values handled
# - Outliers capped
# - Ready for ML training
```

### Data Quality Check

```python
from neurolake.neurobrain import NeuroOrchestrator

# Just analyze, don't ingest
orchestrator = NeuroOrchestrator()
decision = orchestrator.analyze_and_plan(file_path="data.csv")

# Print quality report
orchestrator.print_decision_summary(decision)

# Access quality metrics
print(f"Quality Score: {decision.quality_assessment.overall_score:.2%}")
print(f"Issues Found: {len(decision.quality_assessment.issues)}")

# Get suggestions
for suggestion in decision.transformation_plan.suggestions[:5]:
    print(f"• {suggestion.description}")
```

## 🧪 Run Tests

```bash
# Run complete E2E test
python test_ndm_complete_e2e.py

# Output:
# ✅ TEST 1: NEUROBRAIN Analysis - PASS
# ✅ TEST 2: Ingestion Zone - PASS
# ✅ TEST 3: Processing Mesh - PASS
# ✅ TEST 4: Consumption Layer - PASS
# ✅ TEST 5: Pattern Learning - PASS
# 🎉 ALL TESTS PASSED
```

## 📊 Check Statistics

```python
# Get NEUROBRAIN statistics
orchestrator = NeuroOrchestrator()
stats = orchestrator.get_statistics()

print(f"Ingestions: {stats['neurobrain_stats']['total_ingestions']}")
print(f"Success Rate: {stats['neurobrain_stats']['success_rate']:.2%}")
print(f"Patterns Learned: {stats['pattern_learning_stats']['total_patterns_learned']}")
print(f"Intelligence Level: {stats['summary']['intelligence_level']}")

# Get Ingestion statistics
ingestor = SmartIngestor()
ing_stats = ingestor.get_statistics()

print(f"Total Rows Ingested: {ing_stats['total_rows_ingested']:,}")
print(f"Success Rate: {ing_stats['success_rate']:.2%}")
```

## 🎯 Next Steps

1. **Try your own data**
   ```python
   ingestor = SmartIngestor()
   result = ingestor.ingest("YOUR_FILE.csv", "your_dataset")
   ```

2. **Explore the catalog**
   - Check `C:/NeuroLake/catalog/` for metadata
   - Check `C:/NeuroLake/catalog/lineage/` for lineage

3. **Access stored data**
   ```python
   import pandas as pd
   df = pd.read_parquet("C:/NeuroLake/buckets/raw-data/standard/your_dataset.parquet")
   ```

4. **Integrate with your pipeline**
   - Use SmartIngestor in your ETL
   - Add to Airflow/Prefect DAGs
   - Integrate with your data platform

## 💡 Tips

- **Quality Threshold**: Adjust `quality_threshold` in config (default: 0.5)
- **Auto-Execute**: Set `auto_execute_transformations=True` to apply fixes automatically
- **Target Use Case**: Choose "analytics", "ml", "reporting", or "archive"
- **Partitioning**: Enable `enable_auto_partitioning` for large datasets
- **PII Detection**: Enabled by default, detects and flags 9 PII types

## 🆘 Troubleshooting

**Issue: Import Error**
```python
# Solution: Ensure you're in the neurolake directory
import sys
sys.path.insert(0, 'C:/Users/techh/PycharmProjects/neurolake')
```

**Issue: File Not Found**
```python
# Solution: Use absolute paths
result = ingestor.ingest("C:/full/path/to/file.csv", "dataset")
```

**Issue: Quality Too Low**
```python
# Solution: Check suggestions and apply manually
decision = orchestrator.analyze_and_plan(file_path="data.csv")
for suggestion in decision.transformation_plan.suggestions:
    print(suggestion.code_snippet)
```

## 📚 Documentation

- **Full Implementation**: See `NDM_FULL_IMPLEMENTATION.md`
- **Complete Guide**: See `NDM_IMPLEMENTATION_COMPLETE.md`
- **Architecture**: See `FEATURES_GAP_ANALYSIS.md`
- **Tests**: See `test_ndm_complete_e2e.py`

---

**NeuroLake NDM v4.0 - Ready to Use! 🚀**