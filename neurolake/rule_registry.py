"""
NeuroLake Rule Registry Service
Version control, audit, and reuse business rules and transformation logic
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json


class RuleType(Enum):
    """Types of transformation rules"""
    FILTER = "filter"
    MAP = "map"
    AGGREGATE = "aggregate"
    JOIN = "join"
    VALIDATION = "validation"
    ENRICHMENT = "enrichment"
    CLEANSING = "cleansing"
    BUSINESS_LOGIC = "business_logic"


class RuleStatus(Enum):
    """Rule lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class TransformationRule:
    """Represents a transformation rule"""
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    logic: str  # SQL, Python, or transformation expression
    version: int = 1
    status: RuleStatus = RuleStatus.DRAFT
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other rule IDs
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleAuditLog:
    """Audit log for rule changes"""
    timestamp: datetime
    rule_id: str
    action: str  # created, updated, activated, deprecated
    user: str
    changes: Dict[str, Any]
    version: int


class RuleRegistry:
    """Central registry for managing transformation rules"""

    def __init__(self):
        self.rules: Dict[str, Dict[int, TransformationRule]] = {}  # rule_id -> {version -> rule}
        self.audit_log: List[RuleAuditLog] = []
        self.rule_index: Dict[str, List[str]] = {}  # tag -> [rule_ids]

    def register_rule(self, rule: TransformationRule) -> str:
        """Register a new transformation rule"""
        # Generate rule ID if not provided
        if not rule.rule_id:
            rule.rule_id = self._generate_rule_id(rule.name)

        # Check for conflicts
        if rule.rule_id in self.rules:
            # Create new version
            existing_versions = self.rules[rule.rule_id]
            max_version = max(existing_versions.keys())
            rule.version = max_version + 1
        else:
            self.rules[rule.rule_id] = {}

        # Store rule
        self.rules[rule.rule_id][rule.version] = rule

        # Index by tags
        for tag in rule.tags:
            if tag not in self.rule_index:
                self.rule_index[tag] = []
            if rule.rule_id not in self.rule_index[tag]:
                self.rule_index[tag].append(rule.rule_id)

        # Audit log
        self._log_action(rule.rule_id, "created", rule.created_by, {"rule": rule.__dict__}, rule.version)

        return rule.rule_id

    def get_rule(self, rule_id: str, version: Optional[int] = None) -> Optional[TransformationRule]:
        """Get a rule by ID and version (latest if version not specified)"""
        if rule_id not in self.rules:
            return None

        versions = self.rules[rule_id]
        if version is not None:
            return versions.get(version)

        # Return latest version
        latest_version = max(versions.keys())
        return versions[latest_version]

    def update_rule(self, rule_id: str, updates: Dict[str, Any], user: str) -> Optional[TransformationRule]:
        """Update an existing rule (creates new version)"""
        current_rule = self.get_rule(rule_id)
        if not current_rule:
            return None

        # Create new version
        new_version = current_rule.version + 1
        new_rule = TransformationRule(
            rule_id=rule_id,
            name=updates.get('name', current_rule.name),
            description=updates.get('description', current_rule.description),
            rule_type=updates.get('rule_type', current_rule.rule_type),
            logic=updates.get('logic', current_rule.logic),
            version=new_version,
            status=updates.get('status', current_rule.status),
            created_by=user,
            created_at=current_rule.created_at,
            updated_at=datetime.now(),
            tags=updates.get('tags', current_rule.tags),
            dependencies=updates.get('dependencies', current_rule.dependencies),
            parameters=updates.get('parameters', current_rule.parameters),
            metadata=updates.get('metadata', current_rule.metadata)
        )

        self.rules[rule_id][new_version] = new_rule
        self._log_action(rule_id, "updated", user, updates, new_version)

        return new_rule

    def activate_rule(self, rule_id: str, version: int, user: str) -> bool:
        """Activate a specific rule version"""
        rule = self.get_rule(rule_id, version)
        if not rule:
            return False

        rule.status = RuleStatus.ACTIVE
        rule.updated_at = datetime.now()
        self._log_action(rule_id, "activated", user, {"version": version}, version)
        return True

    def deprecate_rule(self, rule_id: str, user: str) -> bool:
        """Deprecate all versions of a rule"""
        if rule_id not in self.rules:
            return False

        for version, rule in self.rules[rule_id].items():
            rule.status = RuleStatus.DEPRECATED
            rule.updated_at = datetime.now()

        self._log_action(rule_id, "deprecated", user, {"all_versions": True}, max(self.rules[rule_id].keys()))
        return True

    def find_rules_by_tag(self, tag: str) -> List[TransformationRule]:
        """Find all active rules with a specific tag"""
        rule_ids = self.rule_index.get(tag, [])
        rules = []
        for rule_id in rule_ids:
            rule = self.get_rule(rule_id)
            if rule and rule.status == RuleStatus.ACTIVE:
                rules.append(rule)
        return rules

    def find_rules_by_type(self, rule_type: RuleType) -> List[TransformationRule]:
        """Find all active rules of a specific type"""
        rules = []
        for rule_id, versions in self.rules.items():
            latest_rule = self.get_rule(rule_id)
            if latest_rule and latest_rule.rule_type == rule_type and latest_rule.status == RuleStatus.ACTIVE:
                rules.append(latest_rule)
        return rules

    def detect_rule_conflicts(self, rule: TransformationRule) -> List[str]:
        """Detect potential conflicts with existing rules"""
        conflicts = []

        # Check for duplicate logic
        rule_hash = self._hash_logic(rule.logic)
        for rule_id, versions in self.rules.items():
            for version, existing_rule in versions.items():
                if existing_rule.status == RuleStatus.ACTIVE:
                    existing_hash = self._hash_logic(existing_rule.logic)
                    if rule_hash == existing_hash and rule.rule_id != rule_id:
                        conflicts.append(f"Duplicate logic found in rule {rule_id} v{version}")

        # Check for circular dependencies
        if self._has_circular_dependency(rule):
            conflicts.append(f"Circular dependency detected for rule {rule.rule_id}")

        return conflicts

    def get_rule_dependencies(self, rule_id: str) -> List[TransformationRule]:
        """Get all dependency rules for a given rule"""
        rule = self.get_rule(rule_id)
        if not rule:
            return []

        dependencies = []
        for dep_id in rule.dependencies:
            dep_rule = self.get_rule(dep_id)
            if dep_rule:
                dependencies.append(dep_rule)

        return dependencies

    def get_rule_history(self, rule_id: str) -> List[TransformationRule]:
        """Get version history for a rule"""
        if rule_id not in self.rules:
            return []

        versions = self.rules[rule_id]
        return [versions[v] for v in sorted(versions.keys())]

    def get_audit_log(self, rule_id: Optional[str] = None, user: Optional[str] = None) -> List[RuleAuditLog]:
        """Get audit log filtered by rule_id and/or user"""
        logs = self.audit_log

        if rule_id:
            logs = [log for log in logs if log.rule_id == rule_id]

        if user:
            logs = [log for log in logs if log.user == user]

        return logs

    def export_rules(self, format: str = "json") -> str:
        """Export all active rules"""
        active_rules = []
        for rule_id, versions in self.rules.items():
            latest_rule = self.get_rule(rule_id)
            if latest_rule and latest_rule.status == RuleStatus.ACTIVE:
                active_rules.append({
                    'rule_id': latest_rule.rule_id,
                    'name': latest_rule.name,
                    'description': latest_rule.description,
                    'type': latest_rule.rule_type.value,
                    'logic': latest_rule.logic,
                    'version': latest_rule.version,
                    'tags': latest_rule.tags,
                    'created_at': latest_rule.created_at.isoformat()
                })

        if format == "json":
            return json.dumps(active_rules, indent=2)
        else:
            return str(active_rules)

    def get_registry_stats(self) -> Dict:
        """Get registry statistics"""
        total_rules = len(self.rules)
        active_rules = sum(1 for rid in self.rules if self.get_rule(rid).status == RuleStatus.ACTIVE)

        type_counts = {}
        for rule_id in self.rules:
            rule = self.get_rule(rule_id)
            if rule:
                rule_type = rule.rule_type.value
                type_counts[rule_type] = type_counts.get(rule_type, 0) + 1

        return {
            'total_rules': total_rules,
            'active_rules': active_rules,
            'deprecated_rules': sum(1 for rid in self.rules if self.get_rule(rid).status == RuleStatus.DEPRECATED),
            'rules_by_type': type_counts,
            'total_versions': sum(len(versions) for versions in self.rules.values()),
            'audit_log_entries': len(self.audit_log)
        }

    def _generate_rule_id(self, name: str) -> str:
        """Generate unique rule ID from name"""
        base_id = name.lower().replace(' ', '_').replace('-', '_')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{base_id}_{timestamp}"

    def _hash_logic(self, logic: str) -> str:
        """Generate hash of rule logic for duplicate detection"""
        return hashlib.md5(logic.encode()).hexdigest()

    def _has_circular_dependency(self, rule: TransformationRule, visited: Optional[set] = None) -> bool:
        """Check for circular dependencies"""
        if visited is None:
            visited = set()

        if rule.rule_id in visited:
            return True

        visited.add(rule.rule_id)

        for dep_id in rule.dependencies:
            dep_rule = self.get_rule(dep_id)
            if dep_rule and self._has_circular_dependency(dep_rule, visited.copy()):
                return True

        return False

    def _log_action(self, rule_id: str, action: str, user: str, changes: Dict, version: int):
        """Log audit action"""
        log_entry = RuleAuditLog(
            timestamp=datetime.now(),
            rule_id=rule_id,
            action=action,
            user=user,
            changes=changes,
            version=version
        )
        self.audit_log.append(log_entry)
