"""
ETL-to-Spark Converter Agent
Converts ETL jobs to PySpark with data lineage tracking
"""

import json
from typing import Dict, List, Optional
import anthropic
from ..config import AI_CONFIG


class SparkConverterAgent:
    """
    AI Agent for converting ETL jobs to PySpark
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.ai_config = AI_CONFIG['code_generator']

    def convert_to_spark(self,
                        original_code: str,
                        platform: str,
                        extracted_logic: Dict,
                        spark_version: str = '3.5',
                        use_delta: bool = True) -> Dict:
        """
        Convert ETL/SQL/Mainframe code to PySpark

        Args:
            original_code: Original code
            platform: Source platform
            extracted_logic: Extracted business logic
            spark_version: Target Spark version
            use_delta: Whether to use Delta Lake

        Returns:
            Dictionary with converted PySpark code and metadata
        """

        result = {
            'platform': platform,
            'spark_version': spark_version,
            'pyspark_code': None,
            'data_lineage': {},
            'dependencies': [],
            'configuration': {},
            'test_code': None
        }

        # Multi-step conversion
        steps = [
            self._analyze_spark_requirements,
            self._generate_pyspark_code,
            self._generate_data_lineage,
            self._generate_configuration,
            self._generate_tests,
            self._validate_conversion
        ]

        context = {
            'original_code': original_code,
            'platform': platform,
            'extracted_logic': extracted_logic,
            'spark_version': spark_version,
            'use_delta': use_delta
        }

        for step in steps:
            step_result = step(context)
            context.update(step_result)
            result.update(step_result)

        return result

    def _analyze_spark_requirements(self, context: Dict) -> Dict:
        """Analyze Spark conversion requirements"""

        prompt = f"""Analyze requirements for converting {context['platform']} to Spark {context['spark_version']}.

**Source Platform**: {context['platform']}
**Use Delta Lake**: {context['use_delta']}

**Original Code**:
```
{context['original_code'][:5000]}
```

**Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:3000]}
```

Identify:
1. Data sources and how to read them in Spark
2. Transformations and equivalent Spark operations
3. Join strategies (broadcast, sort-merge, etc.)
4. Aggregation patterns
5. Partitioning strategy
6. Caching opportunities
7. UDFs that need to be created
8. Performance optimization opportunities

Return JSON:
{{
  "data_sources": [...],
  "spark_operations": [...],
  "join_strategies": [...],
  "partitioning": {{}},
  "caching_strategy": [...],
  "udfs_needed": [...],
  "optimizations": [...]
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                return {'spark_requirements': json.loads(json_match.group())}
            else:
                return {'spark_requirements': {'analysis': response_text}}

        except Exception as e:
            return {'spark_requirements': {'error': str(e)}}

    def _generate_pyspark_code(self, context: Dict) -> Dict:
        """Generate PySpark code"""

        delta_import = "from delta import *" if context['use_delta'] else ""

        prompt = f"""Convert this {context['platform']} code to PySpark {context['spark_version']}.

**REQUIREMENTS**:
1. Use PySpark DataFrame API (prefer over RDD API)
2. Implement ALL business logic exactly as in original
3. Include comprehensive error handling
4. Add logging at key points
5. Use Delta Lake for ACID transactions (if use_delta=True)
6. Implement data quality checks
7. Make code production-ready and maintainable
8. Add type hints
9. Include docstrings

**Original Code**:
```
{context['original_code'][:8000]}
```

**Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:3000]}
```

**Spark Requirements**:
```json
{json.dumps(context.get('spark_requirements', {}), indent=2, default=str)[:2000]}
```

Generate complete PySpark application with:

1. **Imports and Setup**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window
{delta_import}
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
```

2. **Configuration Class**
3. **Main ETL Class with methods for each step**
4. **Error Handling**
5. **Data Quality Checks**
6. **Logging**
7. **Main execution**

Make it production-ready!"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract Python code
            import re
            code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)

            if code_match:
                pyspark_code = code_match.group(1)
            else:
                pyspark_code = response_text

            return {
                'pyspark_code': pyspark_code,
                'generation_notes': response_text
            }

        except Exception as e:
            return {'pyspark_error': str(e)}

    def _generate_data_lineage(self, context: Dict) -> Dict:
        """Generate data lineage documentation"""

        prompt = f"""Generate comprehensive data lineage for this Spark job.

**PySpark Code**:
```python
{context.get('pyspark_code', '')[:5000]}
```

**Original Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:2000]}
```

Create data lineage showing:
1. Source tables/files → columns
2. All transformations applied to each column
3. Target tables/files ← columns
4. Complete dependency graph

Return JSON:
{{
  "sources": [
    {{
      "name": "...",
      "type": "table|file|api",
      "location": "...",
      "schema": [...]
    }}
  ],
  "targets": [...],
  "column_lineage": {{
    "target_column": {{
      "source_columns": ["..."],
      "transformations": ["step1", "step2", ...],
      "business_rule": "..."
    }}
  }},
  "lineage_graph": {{
    "nodes": [...],
    "edges": [...]
  }}
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=8000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                return {'data_lineage': json.loads(json_match.group())}
            else:
                return {'data_lineage': {'raw': response_text}}

        except Exception as e:
            return {'data_lineage': {'error': str(e)}}

    def _generate_configuration(self, context: Dict) -> Dict:
        """Generate Spark configuration"""

        config = {
            'spark_config': {
                'spark.app.name': f'Migrated_{context["platform"]}_Job',
                'spark.sql.adaptive.enabled': 'true',
                'spark.sql.adaptive.coalescePartitions.enabled': 'true',
                'spark.sql.adaptive.skewJoin.enabled': 'true'
            },
            'resource_config': {
                'driver_memory': '4g',
                'executor_memory': '8g',
                'executor_cores': 4,
                'num_executors': 10
            }
        }

        if context.get('use_delta'):
            config['spark_config'].update({
                'spark.sql.extensions': 'io.delta.sql.DeltaSparkSessionExtension',
                'spark.sql.catalog.spark_catalog': 'org.apache.spark.sql.delta.catalog.DeltaCatalog'
            })

        return {'configuration': config}

    def _generate_tests(self, context: Dict) -> Dict:
        """Generate test code"""

        prompt = f"""Generate comprehensive pytest tests for this PySpark job.

**PySpark Code**:
```python
{context.get('pyspark_code', '')[:5000]}
```

Generate test code with:
1. Unit tests for each function
2. Integration tests for full pipeline
3. Data quality tests
4. Performance tests
5. Edge case tests

Use pytest and chispa for DataFrame testing.

Return complete test file:
```python
import pytest
from chispa.dataframe_comparer import assert_df_equality
from pyspark.sql import SparkSession
# ... rest of tests
```"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=8000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            import re
            code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)

            if code_match:
                test_code = code_match.group(1)
            else:
                test_code = response_text

            return {'test_code': test_code}

        except Exception as e:
            return {'test_code': f'# Test generation error: {str(e)}'}

    def _validate_conversion(self, context: Dict) -> Dict:
        """Validate Spark conversion"""

        prompt = f"""Validate this PySpark conversion for correctness and completeness.

**Original Platform**: {context['platform']}
**Original Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:2000]}
```

**Generated PySpark**:
```python
{context.get('pyspark_code', '')[:5000]}
```

Validate:
1. All business logic implemented
2. Data transformations correct
3. Error handling present
4. Performance optimizations applied
5. Code quality (readability, maintainability)
6. Production readiness

Return validation report JSON:
{{
  "validation_score": <0-100>,
  "passed": <true/false>,
  "logic_completeness": {{"score": ..., "issues": [...]}},
  "correctness": {{"score": ..., "issues": [...]}},
  "performance": {{"score": ..., "notes": [...]}},
  "code_quality": {{"score": ..., "notes": [...]}},
  "production_readiness": {{"score": ..., "checklist": [...]}},
  "recommendations": [...]
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=8000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                return {'spark_validation': json.loads(json_match.group())}
            else:
                return {'spark_validation': {'raw': response_text}}

        except Exception as e:
            return {'spark_validation': {'error': str(e)}}
