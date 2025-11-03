"""
Test Parameterized Queries, Pagination, Row Limits, Templates, and Prepared Statements
"""

import pytest
import pandas as pd
from neurolake.engine import NeuroLakeEngine, SQLValidationError


def test_parameterized_query_basic():
    """Test basic parameterized query with named parameters."""
    engine = NeuroLakeEngine()

    # Test with integer parameter
    sql = "SELECT :user_id as id, 'test' as name"
    params = {"user_id": 123}
    result = engine.execute_sql(sql, params=params)

    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["id"] == 123
    print("[PASS] Integer parameter works")


def test_parameterized_query_string():
    """Test parameterized query with string escaping."""
    engine = NeuroLakeEngine()

    # Test with string parameter (SQL injection protection)
    sql = "SELECT :name as name, :age as age"
    params = {"name": "John's Test", "age": 25}
    result = engine.execute_sql(sql, params=params)

    assert result.iloc[0]["name"] == "John's Test"
    assert result.iloc[0]["age"] == 25
    print("[PASS] String parameter with escaping works")


def test_parameterized_query_multiple():
    """Test query with multiple parameters."""
    engine = NeuroLakeEngine()

    sql = """
    SELECT
        :user_id as id,
        :username as username,
        :age as age,
        :active as active
    """
    params = {
        "user_id": 456,
        "username": "alice",
        "age": 30,
        "active": True
    }
    result = engine.execute_sql(sql, params=params)

    assert result.iloc[0]["id"] == 456
    assert result.iloc[0]["username"] == "alice"
    assert result.iloc[0]["age"] == 30
    print("[PASS] Multiple parameters work")


def test_parameterized_query_null():
    """Test parameterized query with NULL values."""
    engine = NeuroLakeEngine()

    sql = "SELECT :value as value"
    params = {"value": None}
    result = engine.execute_sql(sql, params=params)

    assert pd.isna(result.iloc[0]["value"])
    print("[PASS] NULL parameter works")


def test_parameterized_query_list():
    """Test parameterized query with list/IN clause."""
    engine = NeuroLakeEngine()

    # Create test data
    engine.execute_sql("""
        CREATE TABLE temp_users AS
        SELECT 1 as id, 'Alice' as name
        UNION ALL SELECT 2, 'Bob'
        UNION ALL SELECT 3, 'Charlie'
    """)

    # Query with list parameter
    sql = "SELECT * FROM temp_users WHERE id IN :user_ids"
    params = {"user_ids": [1, 2]}
    result = engine.execute_sql(sql, params=params)

    assert len(result) == 2
    print("[PASS] List parameter works")


def test_parameterized_query_missing_param():
    """Test error when required parameter is missing."""
    engine = NeuroLakeEngine()

    sql = "SELECT :user_id as id, :name as name"
    params = {"user_id": 123}  # Missing 'name' parameter

    with pytest.raises(SQLValidationError, match="Missing required parameters"):
        engine.execute_sql(sql, params=params)

    print("[PASS] Missing parameter detection works")


def test_parameterized_query_no_params():
    """Test that queries work without parameters."""
    engine = NeuroLakeEngine()

    sql = "SELECT 1 as id, 'test' as name"
    result = engine.execute_sql(sql)

    assert result.iloc[0]["id"] == 1
    print("[PASS] Query without parameters works")


def test_row_limit_default():
    """Test default row limit (10K)."""
    engine = NeuroLakeEngine()

    # Create test data with more than 10K rows would be slow, so test the SQL modification
    sql = "SELECT * FROM users"
    modified_sql = engine._apply_pagination(sql, limit=10000, offset=None, page=None, page_size=None)

    assert "LIMIT 10000" in modified_sql
    print("[PASS] Default row limit works")


def test_row_limit_custom():
    """Test custom row limit."""
    engine = NeuroLakeEngine()

    # Create small test dataset
    engine.execute_sql("""
        CREATE TABLE test_limit AS
        SELECT 1 as id UNION ALL
        SELECT 2 UNION ALL
        SELECT 3 UNION ALL
        SELECT 4 UNION ALL
        SELECT 5
    """)

    result = engine.execute_sql("SELECT * FROM test_limit", limit=3)
    assert len(result) == 3
    print("[PASS] Custom row limit works")

    return engine  # Return engine for reuse in other tests


def test_row_limit_unlimited(engine):
    """Test unlimited rows (limit=None)."""
    result = engine.execute_sql("SELECT * FROM test_limit", limit=None)
    assert len(result) == 5
    print("[PASS] Unlimited rows work")


def test_pagination_by_offset(engine):
    """Test pagination with offset."""
    # Get second page (offset 2, limit 2)
    result = engine.execute_sql("SELECT * FROM test_limit ORDER BY id", limit=2, offset=2)

    assert len(result) == 2
    assert result.iloc[0]["id"] == 3
    assert result.iloc[1]["id"] == 4
    print("[PASS] Pagination with offset works")


def test_pagination_by_page(engine):
    """Test pagination with page/page_size."""
    # Get page 2, with 2 rows per page
    result = engine.execute_sql("SELECT * FROM test_limit ORDER BY id", page=2, page_size=2)

    assert len(result) == 2
    assert result.iloc[0]["id"] == 3
    assert result.iloc[1]["id"] == 4
    print("[PASS] Pagination with page/page_size works")


def test_pagination_page_1(engine):
    """Test first page."""
    result = engine.execute_sql("SELECT * FROM test_limit ORDER BY id", page=1, page_size=2)

    assert len(result) == 2
    assert result.iloc[0]["id"] == 1
    assert result.iloc[1]["id"] == 2
    print("[PASS] First page works")


def test_pagination_last_page(engine):
    """Test last page (partial results)."""
    result = engine.execute_sql("SELECT * FROM test_limit ORDER BY id", page=3, page_size=2)

    assert len(result) == 1
    assert result.iloc[0]["id"] == 5
    print("[PASS] Last page with partial results works")


def run_manual_tests():
    """Run all tests manually."""
    print("=== Parameterized Query Tests ===\n")

    test_parameterized_query_basic()
    test_parameterized_query_string()
    test_parameterized_query_multiple()
    test_parameterized_query_null()
    test_parameterized_query_list()
    test_parameterized_query_missing_param()
    test_parameterized_query_no_params()

    print("\n=== Pagination and Row Limit Tests ===\n")

    test_row_limit_default()

    # Create shared engine and test table for pagination tests
    engine = test_row_limit_custom()
    test_row_limit_unlimited(engine)
    test_pagination_by_offset(engine)
    test_pagination_by_page(engine)
    test_pagination_page_1(engine)
    test_pagination_last_page(engine)

    print("\n[SUCCESS] All tests passed!")


if __name__ == "__main__":
    run_manual_tests()
