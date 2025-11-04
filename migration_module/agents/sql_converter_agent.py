"""
SQL-to-SQL Converter Agent
100% Logic Preservation with AI-driven conversion
"""

import json
from typing import Dict, List, Optional
import anthropic
from ..config import AI_CONFIG


class SQLConverterAgent:
    """
    AI Agent for converting SQL between dialects with 100% logic preservation
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.ai_config = AI_CONFIG['code_generator']

    def convert(self,
                original_sql: str,
                source_dialect: str,
                target_dialect: str,
                extracted_logic: Dict,
                optimization_level: str = 'balanced') -> Dict:
        """
        Convert SQL from one dialect to another with 100% logic preservation

        Args:
            original_sql: Original SQL code
            source_dialect: Source SQL dialect (oracle, mssql, postgresql, etc.)
            target_dialect: Target SQL dialect
            extracted_logic: Extracted business logic
            optimization_level: 'preserve' | 'balanced' | 'aggressive'

        Returns:
            Dictionary with converted SQL and validation info
        """

        result = {
            'source_dialect': source_dialect,
            'target_dialect': target_dialect,
            'converted_sql': None,
            'validation': {},
            'warnings': [],
            'optimization_applied': [],
            'compatibility_notes': []
        }

        # Multi-step conversion process
        steps = [
            self._analyze_conversion_requirements,
            self._generate_converted_sql,
            self._validate_logic_preservation,
            self._optimize_converted_sql,
            self._generate_test_cases
        ]

        context = {
            'original_sql': original_sql,
            'source_dialect': source_dialect,
            'target_dialect': target_dialect,
            'extracted_logic': extracted_logic,
            'optimization_level': optimization_level
        }

        for step in steps:
            step_result = step(context)
            context.update(step_result)
            result.update(step_result)

        return result

    def _analyze_conversion_requirements(self, context: Dict) -> Dict:
        """Step 1: Analyze what needs to be converted"""

        prompt = f"""Analyze the conversion requirements for this SQL code.

**Source Dialect**: {context['source_dialect']}
**Target Dialect**: {context['target_dialect']}

**Original SQL**:
```sql
{context['original_sql']}
```

**Extracted Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:3000]}
```

Identify:
1. Dialect-specific features that need conversion
2. Functions that need to be replaced
3. Syntax differences
4. Data type mappings
5. Potential compatibility issues
6. Features not available in target dialect
7. Required workarounds

Return as JSON with structure:
{{
  "conversion_requirements": [...],
  "function_mappings": {{}},
  "syntax_changes": [...],
  "compatibility_issues": [...],
  "workarounds_needed": [...]
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
                return json.loads(json_match.group())
            else:
                return {'analysis': response_text}

        except Exception as e:
            return {'analysis_error': str(e)}

    def _generate_converted_sql(self, context: Dict) -> Dict:
        """Step 2: Generate converted SQL"""

        prompt = f"""Convert this SQL code from {context['source_dialect']} to {context['target_dialect']}.

**CRITICAL REQUIREMENTS**:
1. Preserve 100% of business logic - NOTHING can be lost or changed
2. Maintain exact same output/behavior
3. Keep all edge cases and error handling
4. Preserve performance characteristics where possible
5. Add comments explaining any non-obvious conversions

**Original SQL**:
```sql
{context['original_sql']}
```

**Business Logic to Preserve**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:3000]}
```

**Conversion Analysis**:
```json
{json.dumps(context.get('conversion_requirements', {}), indent=2)[:2000]}
```

Generate the converted {context['target_dialect']} SQL code.

Include:
1. The complete converted SQL
2. Inline comments explaining conversions
3. Any helper functions needed
4. Setup/configuration statements if required

Return format:
```sql
-- Converted from {context['source_dialect']} to {context['target_dialect']}
-- Conversion date: [date]

[CONVERTED SQL HERE]
```
"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract SQL code from response
            import re
            sql_match = re.search(r'```sql\n(.*?)\n```', response_text, re.DOTALL)

            if sql_match:
                converted_sql = sql_match.group(1)
            else:
                # Try without code fence
                converted_sql = response_text

            return {
                'converted_sql': converted_sql,
                'conversion_notes': response_text
            }

        except Exception as e:
            return {'conversion_error': str(e)}

    def _validate_logic_preservation(self, context: Dict) -> Dict:
        """Step 3: Validate that logic is 100% preserved"""

        if not context.get('converted_sql'):
            return {'validation': {'passed': False, 'error': 'No converted SQL available'}}

        prompt = f"""Validate that this SQL conversion preserves 100% of the original logic.

**Original SQL** ({context['source_dialect']}):
```sql
{context['original_sql'][:5000]}
```

**Converted SQL** ({context['target_dialect']}):
```sql
{context['converted_sql'][:5000]}
```

**Original Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:2000]}
```

Perform comprehensive validation:

1. **Logic Preservation** (100 points): Does converted code implement exact same logic?
2. **Edge Cases** (100 points): Are all edge cases handled?
3. **Data Types** (100 points): Are data types correctly mapped?
4. **Functions** (100 points): Are all functions correctly converted?
5. **Performance** (100 points): Similar performance characteristics?
6. **Error Handling** (100 points): Error handling preserved?
7. **Completeness** (100 points): Nothing missing?

Return JSON:
{{
  "overall_score": <0-700>,
  "passed": <true/false (pass = score >= 690)>,
  "validation_details": {{
    "logic_preservation": {{"score": <0-100>, "issues": [...]}},
    "edge_cases": {{"score": <0-100>, "issues": [...]}},
    "data_types": {{"score": <0-100>, "issues": [...]}},
    "functions": {{"score": <0-100>, "issues": [...]}},
    "performance": {{"score": <0-100>, "issues": [...]}},
    "error_handling": {{"score": <0-100>, "issues": [...]}},
    "completeness": {{"score": <0-100>, "issues": [...]}}
  }},
  "critical_issues": [...],
  "warnings": [...],
  "recommendations": [...]
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=0.0,  # Zero temperature for validation
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                validation_result = json.loads(json_match.group())
                return {'validation': validation_result}
            else:
                return {'validation': {'passed': False, 'error': 'Could not parse validation'}}

        except Exception as e:
            return {'validation': {'passed': False, 'error': str(e)}}

    def _optimize_converted_sql(self, context: Dict) -> Dict:
        """Step 4: Optimize the converted SQL"""

        if context['optimization_level'] == 'preserve':
            return {'optimization_applied': ['None - preservation mode']}

        if not context.get('converted_sql'):
            return {'optimization_applied': []}

        prompt = f"""Optimize this {context['target_dialect']} SQL while preserving exact logic.

**Optimization Level**: {context['optimization_level']}

**Current SQL**:
```sql
{context['converted_sql'][:5000]}
```

**Optimization Guidelines**:
- balanced: Moderate optimizations (add indexes hints, rewrite inefficient patterns)
- aggressive: Maximum optimization (restructure queries, advanced techniques)

**CRITICAL**: Do NOT change logic or results in any way.

Apply optimizations such as:
1. Index hints where beneficial
2. Query restructuring for better performance
3. CTE optimization
4. Join order optimization
5. Predicate pushdown
6. Partition pruning hints

Return JSON:
{{
  "optimized_sql": "<optimized SQL>",
  "optimizations_applied": ["list of optimizations"],
  "expected_improvement": "<performance expectation>"
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                optimization_result = json.loads(json_match.group())

                # Replace converted_sql with optimized version if available
                if optimization_result.get('optimized_sql'):
                    return {
                        'converted_sql': optimization_result['optimized_sql'],
                        'optimization_applied': optimization_result.get('optimizations_applied', []),
                        'expected_improvement': optimization_result.get('expected_improvement', 'Unknown')
                    }

            return {'optimization_applied': ['Optimization attempted but no changes made']}

        except Exception as e:
            return {'optimization_error': str(e), 'optimization_applied': []}

    def _generate_test_cases(self, context: Dict) -> Dict:
        """Step 5: Generate test cases to verify conversion"""

        prompt = f"""Generate comprehensive test cases for this SQL conversion.

**Original Business Logic**:
```json
{json.dumps(context['extracted_logic'], indent=2, default=str)[:2000]}
```

**Converted SQL**:
```sql
{context.get('converted_sql', '')[:3000]}
```

Generate test cases covering:
1. Normal/happy path scenarios
2. Edge cases
3. Null handling
4. Data type boundaries
5. Complex business logic verification
6. Performance benchmarks

Return JSON:
{{
  "test_cases": [
    {{
      "id": "test_001",
      "description": "...",
      "test_type": "functional|edge_case|performance",
      "setup_data": "SQL to create test data",
      "execute": "SQL to execute",
      "expected_result": "Expected output description",
      "validation_query": "SQL to validate results"
    }}
  ],
  "performance_tests": [...],
  "regression_tests": [...]
}}"""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=8000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                return {'test_cases': json.loads(json_match.group())}
            else:
                return {'test_cases': {'raw': response_text}}

        except Exception as e:
            return {'test_cases': {'error': str(e)}}

    def iterative_refinement(self, conversion_result: Dict, feedback: str) -> Dict:
        """Refine conversion based on feedback"""

        prompt = f"""Refine this SQL conversion based on feedback.

**Current Conversion**:
```sql
{conversion_result.get('converted_sql', '')}
```

**Feedback**:
{feedback}

**Validation Results**:
```json
{json.dumps(conversion_result.get('validation', {}), indent=2)}
```

Provide improved version addressing all feedback."""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            import re
            sql_match = re.search(r'```sql\n(.*?)\n```', response_text, re.DOTALL)

            if sql_match:
                return {'refined_sql': sql_match.group(1), 'refinement_notes': response_text}
            else:
                return {'refined_sql': response_text}

        except Exception as e:
            return {'refinement_error': str(e)}
