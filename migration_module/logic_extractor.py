"""
Logic Extraction Engine
Extracts business logic, transformations, and dependencies using AI
"""

import json
from typing import Dict, List, Optional
import anthropic
from .config import AI_CONFIG
from .parsers import SQLParser, ETLParser, MainframeParser


class LogicExtractor:
    """Extract and document business logic from code"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.ai_config = AI_CONFIG['logic_extractor']
        self.sql_parser = SQLParser(api_key)
        self.etl_parser = ETLParser(api_key)
        self.mainframe_parser = MainframeParser(api_key)

    def extract_logic(self, code: str, platform: str, parsed_data: Dict) -> Dict:
        """
        Extract comprehensive business logic from code
        """
        result = {
            'platform': platform,
            'business_rules': [],
            'transformations': [],
            'data_lineage': {},
            'dependencies': [],
            'validation_rules': [],
            'calculations': [],
            'aggregations': [],
            'joins': [],
            'filters': [],
            'error_handling': [],
            'performance_considerations': []
        }

        # Use AI to extract detailed logic
        if self.client:
            ai_logic = self._ai_extract_logic(code, platform, parsed_data)
            result.update(ai_logic)

        # Add parser-specific extractions
        result['parsed_metadata'] = parsed_data

        # Extract data lineage
        result['data_lineage'] = self._build_data_lineage(parsed_data)

        # Extract dependencies
        result['dependencies'] = self._extract_dependencies(parsed_data)

        return result

    def _ai_extract_logic(self, code: str, platform: str, parsed_data: Dict) -> Dict:
        """Use AI to extract business logic comprehensively"""

        prompt = f"""You are a senior data engineer analyzing {platform} code for migration.

**Task**: Extract ALL business logic in extreme detail so it can be recreated 100% accurately.

**Parsed Metadata**:
```json
{json.dumps(parsed_data, indent=2, default=str)[:3000]}
```

**Source Code**:
```
{code[:10000]}
```

**Extract the following in JSON format**:

1. **business_rules**: Array of business rules with:
   - rule_id: Unique identifier
   - description: Clear description
   - logic: Exact logic/formula
   - conditions: All conditions
   - examples: Sample inputs/outputs

2. **transformations**: Array of data transformations:
   - transformation_id: Unique ID
   - type: (filter, map, aggregate, join, pivot, etc.)
   - source_columns: Input columns
   - target_columns: Output columns
   - logic: Transformation logic/formula
   - sql_equivalent: SQL pseudocode
   - spark_equivalent: Spark pseudocode

3. **data_lineage**: Object mapping each output column to:
   - source_tables: Origin tables
   - source_columns: Origin columns
   - transformation_steps: Step-by-step lineage
   - business_meaning: What this represents

4. **validation_rules**: Array of validation checks:
   - rule_type: (not_null, unique, range, format, etc.)
   - columns: Affected columns
   - logic: Validation logic
   - error_action: What happens on failure

5. **calculations**: All calculations/formulas:
   - calc_id: Unique ID
   - name: Calculation name
   - formula: Exact formula
   - inputs: Input fields
   - output: Output field
   - data_type: Result data type

6. **aggregations**: All group-by/aggregations:
   - group_by_columns: Grouping columns
   - aggregate_functions: Functions (sum, count, avg, etc.)
   - filters: Pre/post aggregation filters
   - having_clause: Post-aggregation filters

7. **joins**: All join operations:
   - left_table: Left side
   - right_table: Right side
   - join_type: (inner, left, right, full, cross)
   - join_conditions: Join conditions
   - selected_columns: Columns selected after join

8. **filters**: All filter conditions:
   - filter_id: Unique ID
   - condition: Filter condition
   - applies_to: Tables/views affected
   - selectivity: Estimated % of rows kept

9. **error_handling**: Error handling patterns:
   - error_type: Type of error handled
   - handling_logic: How it's handled
   - fallback: Default/fallback behavior

10. **performance_considerations**:
    - indexes_used: Indexes referenced
    - partitioning: Partitioning strategy
    - caching: What should be cached
    - optimization_hints: Query hints or optimizations

**CRITICAL**: Be extremely detailed. This extraction must allow 100% accurate recreation of logic.

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            response_text = response.content[0].text

            # Try to find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Return structured response if JSON parsing fails
                return {
                    'ai_analysis': response_text,
                    'raw_extraction': True
                }

        except Exception as e:
            return {
                'extraction_error': str(e),
                'platform': platform
            }

    def _build_data_lineage(self, parsed_data: Dict) -> Dict:
        """Build data lineage from parsed data"""
        lineage = {
            'sources': [],
            'targets': [],
            'flow': []
        }

        # Extract from different platforms
        if 'tables' in parsed_data:
            lineage['sources'].extend(parsed_data['tables'])

        if 'sources' in parsed_data:
            lineage['sources'].extend([s.get('name', 'unknown') for s in parsed_data['sources']])

        if 'targets' in parsed_data:
            lineage['targets'].extend([t.get('name', 'unknown') for t in parsed_data['targets']])

        return lineage

    def _extract_dependencies(self, parsed_data: Dict) -> List[Dict]:
        """Extract code dependencies"""
        dependencies = []

        # Tables
        if 'tables' in parsed_data:
            for table in parsed_data['tables']:
                dependencies.append({
                    'type': 'table',
                    'name': table,
                    'required': True
                })

        # Procedures/Functions
        if 'procedures' in parsed_data:
            for proc in parsed_data['procedures']:
                dependencies.append({
                    'type': 'procedure',
                    'name': proc.get('name', 'unknown'),
                    'required': True
                })

        if 'functions' in parsed_data:
            for func in parsed_data['functions']:
                dependencies.append({
                    'type': 'function',
                    'name': func.get('name', 'unknown'),
                    'required': True
                })

        return dependencies

    def generate_documentation(self, logic_data: Dict) -> str:
        """Generate comprehensive documentation from extracted logic"""

        if not self.client:
            return self._generate_simple_doc(logic_data)

        prompt = f"""Generate comprehensive technical documentation for this code migration.

**Extracted Logic**:
```json
{json.dumps(logic_data, indent=2, default=str)[:8000]}
```

**Generate documentation with these sections**:

1. **Executive Summary**: High-level overview
2. **Business Logic**: Detailed business rules and logic
3. **Data Flow**: Complete data flow diagrams (in Mermaid)
4. **Transformations**: All data transformations
5. **Technical Specifications**: Technical details
6. **Dependencies**: All dependencies
7. **Migration Notes**: Special considerations for migration
8. **Test Scenarios**: Suggested test cases

Use Markdown format with Mermaid diagrams where appropriate."""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            return f"# Documentation Generation Error\n\n{str(e)}\n\n{self._generate_simple_doc(logic_data)}"

    def _generate_simple_doc(self, logic_data: Dict) -> str:
        """Generate simple documentation without AI"""
        doc = f"""# Migration Documentation

## Platform
{logic_data.get('platform', 'Unknown')}

## Business Rules
{json.dumps(logic_data.get('business_rules', []), indent=2)}

## Transformations
{json.dumps(logic_data.get('transformations', []), indent=2)}

## Data Lineage
{json.dumps(logic_data.get('data_lineage', {}), indent=2)}

## Dependencies
{json.dumps(logic_data.get('dependencies', []), indent=2)}
"""
        return doc
