"""
AI-Powered SQL Parser
Parses SQL stored procedures, functions, and scripts from all major databases
"""

import re
import sqlparse
from typing import Dict, List, Optional, Tuple
import anthropic
from ..config import AI_CONFIG


class SQLParser:
    """Parse SQL code using AI and traditional parsing"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.ai_config = AI_CONFIG['code_parser']

    def parse(self, sql_code: str, dialect: str = 'generic') -> Dict:
        """
        Parse SQL code and extract structure
        """
        # Traditional parsing
        parsed_traditional = self._traditional_parse(sql_code, dialect)

        # AI-enhanced parsing
        if self.client:
            parsed_ai = self._ai_parse(sql_code, dialect)
            # Merge results
            return self._merge_parse_results(parsed_traditional, parsed_ai)

        return parsed_traditional

    def _traditional_parse(self, sql_code: str, dialect: str) -> Dict:
        """Traditional SQL parsing using sqlparse"""
        parsed_statements = sqlparse.parse(sql_code)

        result = {
            'type': 'sql',
            'dialect': dialect,
            'statements': [],
            'procedures': [],
            'functions': [],
            'tables': set(),
            'columns': set(),
            'variables': set(),
            'parameters': [],
            'cursors': [],
            'temp_tables': set(),
            'cte_tables': set(),
            'joins': [],
            'where_clauses': [],
            'transformations': [],
            'aggregations': []
        }

        for statement in parsed_statements:
            stmt_type = statement.get_type()
            stmt_str = str(statement)

            # Detect statement type
            if stmt_type == 'CREATE':
                if 'PROCEDURE' in stmt_str.upper():
                    result['procedures'].append(self._parse_procedure(stmt_str))
                elif 'FUNCTION' in stmt_str.upper():
                    result['functions'].append(self._parse_function(stmt_str))

            # Extract tables
            result['tables'].update(self._extract_tables(stmt_str))

            # Extract columns
            result['columns'].update(self._extract_columns(stmt_str))

            # Extract variables
            result['variables'].update(self._extract_variables(stmt_str))

            # Extract joins
            result['joins'].extend(self._extract_joins(stmt_str))

            # Extract WHERE clauses
            where_clause = self._extract_where_clause(stmt_str)
            if where_clause:
                result['where_clauses'].append(where_clause)

            # Extract CTEs
            result['cte_tables'].update(self._extract_ctes(stmt_str))

            # Extract aggregations
            result['aggregations'].extend(self._extract_aggregations(stmt_str))

            result['statements'].append({
                'type': stmt_type,
                'sql': stmt_str.strip()
            })

        # Convert sets to lists for JSON serialization
        result['tables'] = list(result['tables'])
        result['columns'] = list(result['columns'])
        result['variables'] = list(result['variables'])
        result['temp_tables'] = list(result['temp_tables'])
        result['cte_tables'] = list(result['cte_tables'])

        return result

    def _ai_parse(self, sql_code: str, dialect: str) -> Dict:
        """AI-enhanced parsing using Claude"""
        prompt = f"""Analyze this {dialect} SQL code and extract:

1. Business logic and transformations
2. Data flow and dependencies
3. Complex logic patterns (CASE statements, window functions, etc.)
4. Error handling patterns
5. Performance-critical sections
6. Data quality checks
7. Variables and parameters with their purposes
8. Table relationships and join logic
9. Aggregation and grouping logic
10. Any implicit business rules

SQL Code:
```sql
{sql_code}
```

Return a detailed JSON analysis including all the above aspects."""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse AI response
            ai_analysis = response.content[0].text
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', ai_analysis, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {'ai_analysis': ai_analysis}

        except Exception as e:
            return {'ai_error': str(e)}

    def _merge_parse_results(self, traditional: Dict, ai: Dict) -> Dict:
        """Merge traditional and AI parsing results"""
        merged = traditional.copy()
        merged['ai_insights'] = ai
        return merged

    def _parse_procedure(self, stmt: str) -> Dict:
        """Parse stored procedure definition"""
        # Extract procedure name
        name_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)', stmt, re.IGNORECASE)
        name = name_match.group(1) if name_match else 'unknown'

        # Extract parameters
        params_match = re.search(r'\((.*?)\)', stmt, re.DOTALL)
        params = []
        if params_match:
            params_str = params_match.group(1)
            for param in params_str.split(','):
                param = param.strip()
                if param:
                    parts = param.split()
                    if len(parts) >= 2:
                        params.append({
                            'name': parts[0],
                            'type': parts[1],
                            'mode': parts[2] if len(parts) > 2 else 'IN'
                        })

        return {
            'name': name,
            'parameters': params,
            'body': stmt
        }

    def _parse_function(self, stmt: str) -> Dict:
        """Parse function definition"""
        # Similar to procedure but with RETURN type
        name_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+)', stmt, re.IGNORECASE)
        name = name_match.group(1) if name_match else 'unknown'

        return_match = re.search(r'RETURNS?\s+(\w+)', stmt, re.IGNORECASE)
        return_type = return_match.group(1) if return_match else 'unknown'

        return {
            'name': name,
            'return_type': return_type,
            'body': stmt
        }

    def _extract_tables(self, sql: str) -> set:
        """Extract table names from SQL"""
        tables = set()
        # FROM clause
        from_matches = re.finditer(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        for match in from_matches:
            tables.add(match.group(1))

        # JOIN clause
        join_matches = re.finditer(r'JOIN\s+(\w+)', sql, re.IGNORECASE)
        for match in join_matches:
            tables.add(match.group(1))

        # INSERT/UPDATE/DELETE
        dml_matches = re.finditer(r'(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+)', sql, re.IGNORECASE)
        for match in dml_matches:
            tables.add(match.group(1))

        return tables

    def _extract_columns(self, sql: str) -> set:
        """Extract column references"""
        columns = set()
        # Simple column extraction (can be enhanced)
        select_matches = re.finditer(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        for match in select_matches:
            cols = match.group(1).split(',')
            for col in cols:
                col = col.strip()
                if col and col != '*':
                    # Remove aliases
                    col = re.sub(r'\s+AS\s+.*', '', col, flags=re.IGNORECASE)
                    columns.add(col)
        return columns

    def _extract_variables(self, sql: str) -> set:
        """Extract variable declarations"""
        variables = set()
        # DECLARE statements
        declare_matches = re.finditer(r'DECLARE\s+(@?\w+)', sql, re.IGNORECASE)
        for match in declare_matches:
            variables.add(match.group(1))
        return variables

    def _extract_joins(self, sql: str) -> List[Dict]:
        """Extract JOIN information"""
        joins = []
        join_pattern = r'(\w+\s+)?JOIN\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?\s+ON\s+(.*?)(?:WHERE|ORDER|GROUP|INNER|LEFT|RIGHT|FULL|CROSS|JOIN|$)'
        matches = re.finditer(join_pattern, sql, re.IGNORECASE | re.DOTALL)

        for match in matches:
            joins.append({
                'type': match.group(1).strip() if match.group(1) else 'INNER',
                'table': match.group(2),
                'alias': match.group(3),
                'condition': match.group(4).strip()
            })
        return joins

    def _extract_where_clause(self, sql: str) -> Optional[str]:
        """Extract WHERE clause"""
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP\s+BY|ORDER\s+BY|HAVING|$)', sql, re.IGNORECASE | re.DOTALL)
        return where_match.group(1).strip() if where_match else None

    def _extract_ctes(self, sql: str) -> set:
        """Extract CTEs (Common Table Expressions)"""
        ctes = set()
        cte_pattern = r'WITH\s+(\w+)\s+AS'
        matches = re.finditer(cte_pattern, sql, re.IGNORECASE)
        for match in matches:
            ctes.add(match.group(1))
        return ctes

    def _extract_aggregations(self, sql: str) -> List[str]:
        """Extract aggregation functions"""
        agg_functions = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'STDDEV', 'VARIANCE']
        aggregations = []

        for func in agg_functions:
            pattern = f'{func}\\s*\\((.*?)\\)'
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                aggregations.append({
                    'function': func,
                    'expression': match.group(1).strip()
                })

        return aggregations
