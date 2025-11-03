"""
Cache Key Generator

Generates deterministic cache keys from SQL queries and parameters.
"""

import hashlib
import json
import re
from typing import Any, Dict, Optional


class CacheKeyGenerator:
    """
    Generate cache keys from SQL queries.

    Generates deterministic, collision-resistant cache keys by:
    1. Normalizing SQL (removing whitespace, case)
    2. Including query parameters
    3. Hashing with SHA-256

    Example:
        generator = CacheKeyGenerator(prefix="neurolake")

        key = generator.generate("SELECT * FROM users WHERE id = ?", [123])
        # Returns: "neurolake:cache:abc123def456..."

        key = generator.generate_simple("SELECT * FROM users")
        # Returns: "neurolake:cache:xyz789..."
    """

    def __init__(self, prefix: str = "neurolake", namespace: str = "cache"):
        """
        Initialize cache key generator.

        Args:
            prefix: Key prefix for namespacing
            namespace: Secondary namespace (e.g., "cache", "results")
        """
        self.prefix = prefix
        self.namespace = namespace

    def generate(
        self,
        sql: str,
        params: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate cache key from SQL and parameters.

        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)
            metadata: Optional metadata (e.g., user_id, tenant_id)

        Returns:
            Cache key string (e.g., "neurolake:cache:abc123...")
        """
        # Normalize SQL
        normalized_sql = self._normalize_sql(sql)

        # Build key components
        components = {
            "sql": normalized_sql,
            "params": params or [],
            "metadata": metadata or {},
        }

        # Serialize to JSON (deterministic ordering)
        serialized = json.dumps(components, sort_keys=True, separators=(",", ":"))

        # Hash with SHA-256
        hash_obj = hashlib.sha256(serialized.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        # Build full key
        return f"{self.prefix}:{self.namespace}:{hash_hex}"

    def generate_simple(self, sql: str) -> str:
        """
        Generate simple cache key from SQL only (no parameters).

        Args:
            sql: SQL query string

        Returns:
            Cache key string
        """
        return self.generate(sql, params=None, metadata=None)

    def generate_with_metadata(
        self, sql: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> str:
        """
        Generate cache key with user/tenant metadata.

        Useful for multi-tenant applications where cache should be isolated.

        Args:
            sql: SQL query string
            user_id: User ID for cache isolation
            tenant_id: Tenant ID for cache isolation

        Returns:
            Cache key string
        """
        metadata = {}
        if user_id:
            metadata["user_id"] = user_id
        if tenant_id:
            metadata["tenant_id"] = tenant_id

        return self.generate(sql, params=None, metadata=metadata)

    def _normalize_sql(self, sql: str) -> str:
        """
        Normalize SQL for consistent cache keys.

        Normalization steps:
        1. Convert to lowercase
        2. Remove extra whitespace
        3. Remove comments
        4. Trim leading/trailing whitespace

        Args:
            sql: Original SQL string

        Returns:
            Normalized SQL string
        """
        # Remove SQL comments (-- and /* */)
        sql = re.sub(r"--[^\n]*", "", sql)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

        # Convert to lowercase
        sql = sql.lower()

        # Normalize whitespace (multiple spaces/tabs/newlines -> single space)
        sql = re.sub(r"\s+", " ", sql)

        # Trim
        sql = sql.strip()

        return sql

    def extract_table_names(self, sql: str) -> list:
        """
        Extract table names from SQL for invalidation.

        Used for cache invalidation when tables are updated.

        Args:
            sql: SQL query string

        Returns:
            List of table names
        """
        normalized = self._normalize_sql(sql)

        # Extract FROM and JOIN table names
        tables = []

        # FROM clause
        from_matches = re.findall(r"\bfrom\s+([\w.]+)", normalized)
        tables.extend(from_matches)

        # JOIN clauses
        join_matches = re.findall(r"\bjoin\s+([\w.]+)", normalized)
        tables.extend(join_matches)

        # Remove duplicates and subqueries (starting with ()
        tables = [t for t in set(tables) if not t.startswith("(")]

        return tables

    def invalidation_pattern(self, table_name: str) -> str:
        """
        Generate Redis key pattern for invalidating table-related queries.

        Args:
            table_name: Table name to invalidate

        Returns:
            Redis key pattern (e.g., "neurolake:cache:*")
        """
        # For now, return wildcard pattern (all cache keys)
        # In production, you'd maintain a table->keys mapping
        return f"{self.prefix}:{self.namespace}:*"


__all__ = ["CacheKeyGenerator"]
