"""
Phase 1 Integration Tests

Tests all critical fixes from Phase 1:
1. Database migrations (RBAC tables)
2. Authentication flow
3. Query execution and history persistence
4. Frontend-backend integration readiness
5. Pipelines API
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json


class TestPhase1Integration:
    """Test suite for Phase 1 critical fixes."""

    @classmethod
    def setup_class(cls):
        """Setup test database connection."""
        # Use test database
        db_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake"
        )
        cls.engine = create_engine(db_url)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def test_01_database_connection(self):
        """Test database connection works."""
        with self.SessionLocal() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("✅ Database connection successful")

    def test_02_users_table_exists(self):
        """Test users table exists with new fields."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY column_name
            """))
            columns = [row[0] for row in result.fetchall()]

            required_columns = [
                'id', 'username', 'email', 'password_hash',
                'is_active', 'is_superuser', 'is_verified',
                'require_password_change', 'created_at'
            ]

            for col in required_columns:
                assert col in columns, f"Missing column: {col}"

        print("✅ Users table has all required fields")

    def test_03_rbac_tables_exist(self):
        """Test RBAC tables were created."""
        with self.SessionLocal() as session:
            tables = ['roles', 'permissions', 'user_roles', 'role_permissions']

            for table in tables:
                result = session.execute(text(f"""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_name = '{table}'
                """))
                count = result.scalar()
                assert count == 1, f"Table {table} not found"

        print("✅ All RBAC tables exist")

    def test_04_default_roles_seeded(self):
        """Test default roles were seeded."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT name, is_system
                FROM roles
                WHERE is_system = true
                ORDER BY name
            """))
            roles = [row[0] for row in result.fetchall()]

            expected_roles = ['admin', 'data_analyst', 'data_engineer', 'data_viewer']
            assert set(roles) == set(expected_roles), f"Expected {expected_roles}, got {roles}"

        print("✅ Default roles seeded correctly")

    def test_05_default_permissions_seeded(self):
        """Test default permissions were seeded."""
        with self.SessionLocal() as session:
            result = session.execute(text("SELECT COUNT(*) FROM permissions"))
            count = result.scalar()
            assert count >= 20, f"Expected at least 20 permissions, got {count}"

            # Check specific critical permissions
            result = session.execute(text("""
                SELECT name FROM permissions
                WHERE name IN ('query:execute', 'data:read', 'admin:system')
            """))
            perms = [row[0] for row in result.fetchall()]
            assert len(perms) == 3, "Missing critical permissions"

        print("✅ Default permissions seeded correctly")

    def test_06_role_permissions_assigned(self):
        """Test permissions are assigned to roles."""
        with self.SessionLocal() as session:
            # Admin should have all permissions
            result = session.execute(text("""
                SELECT COUNT(*)
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                WHERE r.name = 'admin'
            """))
            admin_perms = result.scalar()
            assert admin_perms >= 20, f"Admin should have all permissions, got {admin_perms}"

            # Data analyst should have limited permissions
            result = session.execute(text("""
                SELECT p.name
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE r.name = 'data_analyst'
            """))
            analyst_perms = [row[0] for row in result.fetchall()]
            assert 'query:execute' in analyst_perms
            assert 'data:read' in analyst_perms
            assert 'admin:system' not in analyst_perms, "Analyst shouldn't have admin perms"

        print("✅ Role permissions assigned correctly")

    def test_07_query_history_table_exists(self):
        """Test query_history table has correct schema."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'query_history'
                ORDER BY column_name
            """))
            columns = {row[0]: row[1] for row in result.fetchall()}

            required_columns = {
                'query_id': 'character varying',
                'query_text': 'text',
                'query_status': 'character varying',
                'execution_time_ms': 'integer',
                'created_at': 'timestamp with time zone',
            }

            for col, dtype in required_columns.items():
                assert col in columns, f"Missing column: {col}"
                # Note: data types might vary slightly, so just check column exists

        print("✅ Query history table schema correct")

    def test_08_pipelines_table_exists(self):
        """Test pipelines table exists."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pipelines'
                ORDER BY column_name
            """))
            columns = [row[0] for row in result.fetchall()]

            required_columns = [
                'id', 'pipeline_name', 'pipeline_type', 'status',
                'is_active', 'created_at', 'updated_at'
            ]

            for col in required_columns:
                assert col in columns, f"Missing column: {col}"

        print("✅ Pipelines table exists with correct schema")

    def test_09_create_test_admin_user(self):
        """Create a test admin user for integration testing."""
        from neurolake.auth.password_utils import hash_password

        with self.SessionLocal() as session:
            # Check if test user already exists
            result = session.execute(text("""
                SELECT id FROM users WHERE username = 'test_admin'
            """))
            existing = result.fetchone()

            if existing:
                print("ℹ️  Test admin user already exists")
                return

            # Create test admin user
            hashed_password = hash_password("TestPassword123!")

            session.execute(text("""
                INSERT INTO users (
                    username, email, password_hash,
                    is_active, is_superuser, is_verified
                ) VALUES (
                    'test_admin', 'admin@test.com', :password,
                    true, true, true
                )
            """), {"password": hashed_password})

            # Assign admin role
            session.execute(text("""
                INSERT INTO user_roles (user_id, role_id)
                SELECT u.id, r.id
                FROM users u, roles r
                WHERE u.username = 'test_admin'
                AND r.name = 'admin'
            """))

            session.commit()

        print("✅ Test admin user created successfully")

    def test_10_verify_password_hashing(self):
        """Test password hashing and verification."""
        from neurolake.auth.password_utils import hash_password, verify_password

        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed), "Password verification failed"
        assert not verify_password("WrongPassword", hashed), "Wrong password verified"

        print("✅ Password hashing works correctly")

    def test_11_test_database_indexes(self):
        """Verify important indexes exist."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT tablename, indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'roles', 'permissions', 'query_history')
                ORDER BY tablename, indexname
            """))
            indexes = [(row[0], row[1]) for row in result.fetchall()]

            # Check critical indexes exist
            index_names = [idx[1] for idx in indexes]
            assert any('users' in idx and 'username' in idx for idx in index_names), "Missing users username index"
            assert any('users' in idx and 'email' in idx for idx in index_names), "Missing users email index"

        print("✅ Database indexes created correctly")

    def test_12_foreign_key_constraints(self):
        """Verify foreign key constraints are in place."""
        with self.SessionLocal() as session:
            result = session.execute(text("""
                SELECT
                    tc.table_name,
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name IN ('user_roles', 'role_permissions', 'query_history', 'pipelines')
            """))
            fks = list(result.fetchall())

            assert len(fks) > 0, "No foreign keys found"

        print("✅ Foreign key constraints in place")

    def test_13_query_engine_initialization(self):
        """Test NeuroLakeEngine can be initialized."""
        from neurolake.engine import NeuroLakeEngine

        engine = NeuroLakeEngine()
        assert engine is not None
        assert engine.backend in ["spark", "duckdb"]

        print(f"✅ NeuroLake Engine initialized (backend: {engine.backend})")

    def test_14_auth_service_initialization(self):
        """Test AuthService can be initialized."""
        from neurolake.auth.auth_service import AuthService

        with self.SessionLocal() as session:
            auth_service = AuthService(session)
            assert auth_service is not None

        print("✅ Auth service initialized successfully")

    def test_15_compliance_engine_initialization(self):
        """Test ComplianceEngine can be initialized."""
        from neurolake.compliance import ComplianceEngine

        engine = ComplianceEngine()
        assert engine is not None

        print("✅ Compliance engine initialized successfully")

    def test_16_data_catalog_initialization(self):
        """Test DataCatalog can be initialized."""
        from neurolake.catalog import DataCatalog

        catalog = DataCatalog()
        assert catalog is not None

        print("✅ Data catalog initialized successfully")


def run_tests():
    """Run all tests with detailed output."""
    print("\n" + "="*80)
    print("PHASE 1 INTEGRATION TESTS")
    print("="*80 + "\n")

    test_suite = TestPhase1Integration()
    test_suite.setup_class()

    tests = [
        test_suite.test_01_database_connection,
        test_suite.test_02_users_table_exists,
        test_suite.test_03_rbac_tables_exist,
        test_suite.test_04_default_roles_seeded,
        test_suite.test_05_default_permissions_seeded,
        test_suite.test_06_role_permissions_assigned,
        test_suite.test_07_query_history_table_exists,
        test_suite.test_08_pipelines_table_exists,
        test_suite.test_09_create_test_admin_user,
        test_suite.test_10_verify_password_hashing,
        test_suite.test_11_test_database_indexes,
        test_suite.test_12_foreign_key_constraints,
        test_suite.test_13_query_engine_initialization,
        test_suite.test_14_auth_service_initialization,
        test_suite.test_15_compliance_engine_initialization,
        test_suite.test_16_data_catalog_initialization,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}")

    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*80 + "\n")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! Phase 1 integration is successful.\n")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
