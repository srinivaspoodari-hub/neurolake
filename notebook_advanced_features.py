"""
NeuroLake Notebook Advanced Features
Compliance, Governance, Intelligence, and Neuro Brain Integration
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class CompliancePolicyEngine:
    """Enforce compliance policies on notebook operations"""

    def __init__(self):
        self.policies = {
            "pii_detection": True,
            "data_retention": 90,  # days
            "encryption_required": True,
            "audit_logging": True,
            "access_control": True
        }
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        }

    def detect_pii(self, data: Any) -> Dict:
        """Detect PII in data"""
        pii_found = []

        if isinstance(data, str):
            for pii_type, pattern in self.pii_patterns.items():
                if re.search(pattern, data):
                    pii_found.append(pii_type)

        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    for pii_type, pattern in self.pii_patterns.items():
                        if re.search(pattern, value):
                            pii_found.append(f"{key}:{pii_type}")

        elif isinstance(data, list):
            for item in data:
                result = self.detect_pii(item)
                pii_found.extend(result.get('pii_found', []))

        return {
            "has_pii": len(pii_found) > 0,
            "pii_found": list(set(pii_found)),
            "requires_masking": len(pii_found) > 0
        }

    def mask_pii(self, data: str, pii_type: str) -> str:
        """Mask PII data"""
        if pii_type == "email":
            return re.sub(self.pii_patterns['email'], '***@***.com', data)
        elif pii_type == "ssn":
            return re.sub(self.pii_patterns['ssn'], '***-**-****', data)
        elif pii_type == "credit_card":
            return re.sub(self.pii_patterns['credit_card'], '****-****-****-****', data)
        elif pii_type == "phone":
            return re.sub(self.pii_patterns['phone'], '***-***-****', data)
        return data

    def check_compliance(self, operation: Dict) -> Dict:
        """Check if operation complies with policies"""
        violations = []

        # Check PII handling
        if 'data' in operation:
            pii_result = self.detect_pii(operation['data'])
            if pii_result['has_pii'] and not operation.get('pii_masked', False):
                violations.append({
                    "policy": "pii_detection",
                    "severity": "high",
                    "message": f"Unmasked PII detected: {pii_result['pii_found']}"
                })

        # Check encryption
        if self.policies['encryption_required'] and not operation.get('encrypted', False):
            if 'sensitive' in str(operation).lower():
                violations.append({
                    "policy": "encryption_required",
                    "severity": "high",
                    "message": "Sensitive data must be encrypted"
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "timestamp": datetime.now().isoformat()
        }


class GovernanceEngine:
    """Data governance and access control"""

    def __init__(self):
        self.access_policies = {}
        self.audit_log = []

    def check_access(self, user: str, resource: str, operation: str) -> bool:
        """Check if user has access to perform operation"""
        # Default: allow all for demo
        self.log_access(user, resource, operation, "allowed")
        return True

    def log_access(self, user: str, resource: str, operation: str, result: str):
        """Log access attempt"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "resource": resource,
            "operation": operation,
            "result": result
        })

    def get_audit_log(self, filters: Dict = None) -> List[Dict]:
        """Get filtered audit log"""
        if not filters:
            return self.audit_log

        # Apply filters
        filtered = self.audit_log
        if 'user' in filters:
            filtered = [log for log in filtered if log['user'] == filters['user']]
        if 'resource' in filters:
            filtered = [log for log in filtered if log['resource'] == filters['resource']]

        return filtered


class DataLineageTracker:
    """Track data lineage in notebook operations"""

    def __init__(self):
        self.lineage_graph = {
            "nodes": [],  # Tables, views, files
            "edges": []   # Transformations
        }

    def add_source(self, source_id: str, source_type: str, metadata: Dict):
        """Add data source to lineage"""
        node = {
            "id": source_id,
            "type": source_type,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        self.lineage_graph['nodes'].append(node)

    def add_transformation(self, source_id: str, target_id: str, operation: str, code: str):
        """Add transformation to lineage"""
        edge = {
            "source": source_id,
            "target": target_id,
            "operation": operation,
            "code": code,
            "timestamp": datetime.now().isoformat()
        }
        self.lineage_graph['edges'].append(edge)

    def get_lineage(self, entity_id: str) -> Dict:
        """Get complete lineage for an entity"""
        upstream = self._get_upstream(entity_id)
        downstream = self._get_downstream(entity_id)

        return {
            "entity_id": entity_id,
            "upstream": upstream,
            "downstream": downstream,
            "full_graph": self.lineage_graph
        }

    def _get_upstream(self, entity_id: str) -> List[Dict]:
        """Get upstream dependencies"""
        upstream = []
        for edge in self.lineage_graph['edges']:
            if edge['target'] == entity_id:
                upstream.append(edge)
        return upstream

    def _get_downstream(self, entity_id: str) -> List[Dict]:
        """Get downstream dependencies"""
        downstream = []
        for edge in self.lineage_graph['edges']:
            if edge['source'] == entity_id:
                downstream.append(edge)
        return downstream


class QueryOptimizer:
    """Provide query optimization suggestions"""

    def analyze_query(self, sql: str) -> Dict:
        """Analyze SQL query and provide optimization suggestions"""
        suggestions = []

        sql_upper = sql.upper()

        # Check for SELECT *
        if 'SELECT *' in sql_upper:
            suggestions.append({
                "type": "performance",
                "severity": "medium",
                "message": "Avoid SELECT * - specify only needed columns",
                "recommendation": "SELECT column1, column2 instead of SELECT *"
            })

        # Check for missing WHERE clause
        if 'WHERE' not in sql_upper and 'SELECT' in sql_upper:
            suggestions.append({
                "type": "performance",
                "severity": "high",
                "message": "Query missing WHERE clause - may scan entire table",
                "recommendation": "Add WHERE clause to filter data"
            })

        # Check for DISTINCT
        if 'DISTINCT' in sql_upper:
            suggestions.append({
                "type": "performance",
                "severity": "low",
                "message": "DISTINCT can be expensive - ensure it's necessary",
                "recommendation": "Consider if DISTINCT is truly needed"
            })

        # Check for JOIN without ON
        if 'JOIN' in sql_upper and 'ON' not in sql_upper:
            suggestions.append({
                "type": "correctness",
                "severity": "high",
                "message": "JOIN missing ON clause - will produce Cartesian product",
                "recommendation": "Add ON clause to JOIN"
            })

        return {
            "query": sql,
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
            "estimated_improvement": self._estimate_improvement(suggestions)
        }

    def _estimate_improvement(self, suggestions: List[Dict]) -> str:
        """Estimate performance improvement"""
        if len(suggestions) >= 3:
            return "high"
        elif len(suggestions) >= 1:
            return "medium"
        return "low"


class AICodeCompletion:
    """AI-powered code completion for notebook cells"""

    def __init__(self):
        self.templates = {
            "python": {
                "read_csv": "import pandas as pd\ndf = pd.read_csv('{filename}')",
                "create_table": "CREATE TABLE {table_name} (\n    id INT,\n    name STRING\n)",
                "select_query": "SELECT * FROM {table_name} WHERE {condition} LIMIT 10"
            },
            "sql": {
                "select_query": "SELECT * FROM {table_name} WHERE {condition} LIMIT 10",
                "join": "SELECT a.*, b.*\nFROM {table1} a\nJOIN {table2} b ON a.id = b.id",
                "group_by": "SELECT {column}, COUNT(*)\nFROM {table}\nGROUP BY {column}",
                "window": "SELECT {column},\n    ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {order}) as rn\nFROM {table}"
            }
        }

    def get_suggestions(self, partial_code: str, language: str) -> List[Dict]:
        """Get code completion suggestions"""
        suggestions = []

        code_lower = partial_code.lower()

        # Detect intent
        if 'select' in code_lower and language == 'sql':
            suggestions.append({
                "type": "template",
                "label": "SELECT statement",
                "code": self.templates['sql']['select_query'],
                "description": "Basic SELECT query template"
            })

        if 'join' in code_lower and language == 'sql':
            suggestions.append({
                "type": "template",
                "label": "JOIN statement",
                "code": self.templates['sql']['join'],
                "description": "JOIN query template"
            })

        if 'import' in code_lower and language == 'python':
            suggestions.append({
                "type": "import",
                "label": "import pandas",
                "code": "import pandas as pd",
                "description": "Import pandas library"
            })

        return suggestions


class NeuroBrainIntegration:
    """Integrate with Neuro Brain for intelligent insights"""

    def __init__(self):
        self.insights_cache = {}
        self.learning_patterns = []

    def analyze_data_pattern(self, data: List[Dict]) -> Dict:
        """Analyze data patterns using Neuro Brain"""
        if not data:
            return {"insights": [], "patterns": []}

        # Analyze structure
        insights = []

        # Check data distribution
        if len(data) > 0:
            first_row = data[0]
            num_columns = len(first_row.keys())
            insights.append({
                "type": "structure",
                "message": f"Dataset has {len(data)} rows and {num_columns} columns",
                "confidence": 1.0
            })

        # Detect numeric columns
        numeric_cols = []
        if data:
            for key, value in data[0].items():
                if isinstance(value, (int, float)):
                    numeric_cols.append(key)

        if numeric_cols:
            insights.append({
                "type": "recommendation",
                "message": f"Consider aggregating numeric columns: {', '.join(numeric_cols)}",
                "confidence": 0.8
            })

        # Detect potential keys
        if data and 'id' in data[0]:
            insights.append({
                "type": "schema",
                "message": "'id' column detected - likely primary key",
                "confidence": 0.9
            })

        return {
            "insights": insights,
            "patterns_detected": len(insights),
            "confidence_avg": sum(i['confidence'] for i in insights) / len(insights) if insights else 0
        }

    def suggest_transformation(self, source_data: List[Dict], target_schema: Dict) -> Dict:
        """Suggest data transformation code"""
        suggestions = []

        # Compare schemas
        if source_data:
            source_cols = set(source_data[0].keys())
            target_cols = set(target_schema.get('columns', []))

            missing_cols = target_cols - source_cols
            if missing_cols:
                suggestions.append({
                    "type": "add_columns",
                    "columns": list(missing_cols),
                    "code": f"# Add missing columns: {', '.join(missing_cols)}"
                })

            extra_cols = source_cols - target_cols
            if extra_cols:
                suggestions.append({
                    "type": "remove_columns",
                    "columns": list(extra_cols),
                    "code": f"# Remove extra columns: {', '.join(extra_cols)}"
                })

        return {
            "suggestions": suggestions,
            "estimated_complexity": "low" if len(suggestions) <= 2 else "medium"
        }


class DataQualityChecker:
    """Validate data quality in notebook operations"""

    def check_quality(self, data: List[Dict]) -> Dict:
        """Run comprehensive data quality checks"""
        if not data:
            return {
                "quality_score": 0,
                "issues": [{"type": "empty_dataset", "severity": "high"}]
            }

        issues = []

        # Check for nulls
        null_count = 0
        for row in data:
            for value in row.values():
                if value is None:
                    null_count += 1

        if null_count > 0:
            issues.append({
                "type": "null_values",
                "count": null_count,
                "severity": "medium",
                "recommendation": "Consider handling null values"
            })

        # Check for duplicates
        seen = set()
        duplicate_count = 0
        for row in data:
            row_str = str(sorted(row.items()))
            if row_str in seen:
                duplicate_count += 1
            seen.add(row_str)

        if duplicate_count > 0:
            issues.append({
                "type": "duplicates",
                "count": duplicate_count,
                "severity": "medium",
                "recommendation": "Remove duplicate rows"
            })

        # Calculate quality score
        quality_score = 100
        for issue in issues:
            if issue['severity'] == 'high':
                quality_score -= 30
            elif issue['severity'] == 'medium':
                quality_score -= 15
            elif issue['severity'] == 'low':
                quality_score -= 5

        return {
            "quality_score": max(0, quality_score),
            "total_rows": len(data),
            "issues_found": len(issues),
            "issues": issues,
            "passed": quality_score >= 70
        }


class SchemaEvolutionEngine:
    """Automatic schema evolution and migration"""

    def __init__(self):
        self.schema_versions = {}

    def detect_schema_change(self, old_schema: List[Dict], new_data: List[Dict]) -> Dict:
        """Detect schema changes in new data"""
        if not new_data:
            return {"has_changes": False}

        new_schema = self._infer_schema(new_data)
        changes = []

        old_cols = {col['name']: col for col in old_schema}
        new_cols = {col['name']: col for col in new_schema}

        # Detect new columns
        for col_name in new_cols:
            if col_name not in old_cols:
                changes.append({
                    "type": "column_added",
                    "column": col_name,
                    "data_type": new_cols[col_name]['type']
                })

        # Detect removed columns
        for col_name in old_cols:
            if col_name not in new_cols:
                changes.append({
                    "type": "column_removed",
                    "column": col_name
                })

        # Detect type changes
        for col_name in old_cols:
            if col_name in new_cols:
                if old_cols[col_name]['type'] != new_cols[col_name]['type']:
                    changes.append({
                        "type": "type_changed",
                        "column": col_name,
                        "old_type": old_cols[col_name]['type'],
                        "new_type": new_cols[col_name]['type']
                    })

        return {
            "has_changes": len(changes) > 0,
            "changes": changes,
            "new_schema": new_schema,
            "migration_required": len(changes) > 0
        }

    def _infer_schema(self, data: List[Dict]) -> List[Dict]:
        """Infer schema from data"""
        if not data:
            return []

        first_row = data[0]
        schema = []

        for key, value in first_row.items():
            col_type = type(value).__name__
            if col_type == 'int':
                col_type = 'INTEGER'
            elif col_type == 'float':
                col_type = 'DOUBLE'
            elif col_type == 'str':
                col_type = 'STRING'
            elif col_type == 'bool':
                col_type = 'BOOLEAN'

            schema.append({
                "name": key,
                "type": col_type,
                "nullable": True
            })

        return schema

    def generate_migration(self, changes: List[Dict]) -> str:
        """Generate SQL migration script"""
        sql_statements = []

        for change in changes:
            if change['type'] == 'column_added':
                sql_statements.append(
                    f"ALTER TABLE {{table_name}} ADD COLUMN {change['column']} {change['data_type']}"
                )
            elif change['type'] == 'column_removed':
                sql_statements.append(
                    f"ALTER TABLE {{table_name}} DROP COLUMN {change['column']}"
                )
            elif change['type'] == 'type_changed':
                sql_statements.append(
                    f"-- Warning: Type change from {change['old_type']} to {change['new_type']}\n"
                    f"ALTER TABLE {{table_name}} ALTER COLUMN {change['column']} TYPE {change['new_type']}"
                )

        return ";\n".join(sql_statements)


class DataEncryption:
    """Encrypt sensitive data in notebook operations"""

    def __init__(self):
        self.encryption_key = "demo_key_123"  # In production, use proper key management

    def encrypt_field(self, value: str) -> str:
        """Encrypt a single field"""
        # Simple base64 encoding for demo (use proper encryption in production)
        import base64
        return base64.b64encode(value.encode()).decode()

    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a single field"""
        import base64
        return base64.b64decode(encrypted_value.encode()).decode()

    def encrypt_dataset(self, data: List[Dict], sensitive_fields: List[str]) -> List[Dict]:
        """Encrypt sensitive fields in dataset"""
        encrypted_data = []

        for row in data:
            encrypted_row = row.copy()
            for field in sensitive_fields:
                if field in encrypted_row and encrypted_row[field] is not None:
                    encrypted_row[field] = self.encrypt_field(str(encrypted_row[field]))
            encrypted_data.append(encrypted_row)

        return encrypted_data


# Integration example
if __name__ == "__main__":
    # Demo compliance check
    compliance = CompliancePolicyEngine()

    test_data = [
        {"name": "Alice", "email": "alice@example.com", "age": 30},
        {"name": "Bob", "email": "bob@test.com", "age": 25}
    ]

    pii_result = compliance.detect_pii(test_data)
    print("PII Detection Result:")
    print(json.dumps(pii_result, indent=2))

    # Demo quality check
    quality_checker = DataQualityChecker()
    quality_result = quality_checker.check_quality(test_data)
    print("\nData Quality Check:")
    print(json.dumps(quality_result, indent=2))

    # Demo Neuro Brain
    neuro_brain = NeuroBrainIntegration()
    insights = neuro_brain.analyze_data_pattern(test_data)
    print("\nNeuro Brain Insights:")
    print(json.dumps(insights, indent=2))
