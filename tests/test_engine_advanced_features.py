"""
Test Templates, Prepared Statements, EXPLAIN, and Advanced Query Types
"""

import pytest
import pandas as pd
from neurolake.engine import (
    NeuroLakeEngine,
    QueryTemplate,
    PreparedStatement,
    TemplateRegistry,
    get_template_registry,
    QueryPlanVisualizer,
)


# ===== Template Tests =====

def test_query_template_basic():
    """Test basic query template."""
    template = QueryTemplate(
        name="get_user",
        sql="SELECT * FROM users WHERE id = :user_id",
        description="Get user by ID"
    )

    assert template.name == "get_user"
    assert "user_id" in template.required_params
    print("[PASS] Query template creation works")


def test_query_template_render():
    """Test template rendering."""
    template = QueryTemplate(
        name="filter_users",
        sql="SELECT * FROM users WHERE age > :min_age AND city = :city"
    )

    rendered = template.render(min_age=18, city="NYC")
    assert ":min_age" in rendered  # Placeholders remain (will be substituted by engine)
    assert ":city" in rendered
    print("[PASS] Template rendering works")


def test_query_template_defaults():
    """Test template with default parameters."""
    template = QueryTemplate(
        name="search_users",
        sql="SELECT * FROM users WHERE active = :active",
        default_params={"active": True}
    )

    # Should validate even without providing 'active'
    assert template.validate_params()
    print("[PASS] Template default parameters work")


def test_query_template_missing_param():
    """Test error on missing required parameter."""
    template = QueryTemplate(
        name="get_orders",
        sql="SELECT * FROM orders WHERE user_id = :user_id AND status = :status"
    )

    with pytest.raises(ValueError, match="missing required parameters"):
        template.render(user_id=123)  # Missing 'status'

    print("[PASS] Missing parameter detection works")


def test_template_registry():
    """Test template registry."""
    registry = TemplateRegistry()

    template = QueryTemplate(
        name="test_template",
        sql="SELECT :value as value"
    )

    registry.register(template)
    retrieved = registry.get("test_template")

    assert retrieved is not None
    assert retrieved.name == "test_template"
    print("[PASS] Template registry works")


def test_template_registry_create():
    """Test create and register in one step."""
    registry = TemplateRegistry()

    template = registry.create_and_register(
        name="quick_template",
        sql="SELECT * FROM users WHERE id = :id",
        description="Quick template"
    )

    assert template.name == "quick_template"
    assert registry.get("quick_template") is not None
    print("[PASS] Registry create_and_register works")


# ===== Prepared Statement Tests =====

def test_prepared_statement_basic():
    """Test basic prepared statement."""
    stmt = PreparedStatement(
        sql="SELECT :id as id, :name as name",
        name="test_stmt"
    )

    assert stmt.name == "test_stmt"
    assert "id" in stmt.required_params
    assert "name" in stmt.required_params
    print("[PASS] Prepared statement creation works")


def test_prepared_statement_execute():
    """Test prepared statement execution."""
    engine = NeuroLakeEngine()

    stmt = PreparedStatement(
        sql="SELECT :value as value",
        name="select_value"
    )

    result = stmt.execute(engine, value=42)
    assert result.iloc[0]["value"] == 42
    assert stmt.execution_count == 1
    print("[PASS] Prepared statement execution works")


def test_prepared_statement_reuse():
    """Test prepared statement reuse."""
    engine = NeuroLakeEngine()

    stmt = PreparedStatement(
        sql="SELECT :x as x, :y as y",
        name="select_xy"
    )

    result1 = stmt.execute(engine, x=1, y=2)
    result2 = stmt.execute(engine, x=3, y=4)

    assert result1.iloc[0]["x"] == 1
    assert result2.iloc[0]["x"] == 3
    assert stmt.execution_count == 2
    print("[PASS] Prepared statement reuse works")


def test_prepared_statement_stats():
    """Test prepared statement statistics."""
    engine = NeuroLakeEngine()

    stmt = PreparedStatement(
        sql="SELECT :n as n",
        name="select_n",
        description="Select number"
    )

    stmt.execute(engine, n=100)
    stats = stmt.get_stats()

    assert stats["execution_count"] == 1
    assert stats["name"] == "select_n"
    assert "last_execution" in stats
    print("[PASS] Prepared statement stats work")


# ===== EXPLAIN PLAN Tests =====

def test_explain_basic(engine):
    """Test basic EXPLAIN."""
    plan_df = engine.explain("SELECT * FROM explain_test")
    assert plan_df is not None
    assert len(plan_df) > 0
    print("[PASS] EXPLAIN works")


def test_explain_with_params(engine):
    """Test EXPLAIN with parameters."""
    plan_df = engine.explain(
        "SELECT * FROM explain_test WHERE id = :user_id",
        params={"user_id": 1}
    )

    assert plan_df is not None
    print("[PASS] EXPLAIN with parameters works")


def test_get_query_plan(engine):
    """Test structured query plan."""
    plan_info = engine.get_query_plan("SELECT * FROM explain_test WHERE id = 1")

    assert "sql" in plan_info
    assert "backend" in plan_info
    assert "plan_text" in plan_info
    assert "plan_lines" in plan_info
    print(f"[PASS] get_query_plan works: {plan_info['backend']}")


# ===== Plan Visualization Tests =====

def test_plan_visualizer_tree(engine):
    """Test plan visualization in tree format."""
    visualizer = QueryPlanVisualizer()

    plan_info = engine.get_query_plan("SELECT * FROM explain_test")
    formatted = visualizer.format_plan(plan_info, format="tree")

    assert "QUERY EXECUTION PLAN" in formatted
    assert "Backend:" in formatted
    print("[PASS] Plan visualizer tree format works")


def test_plan_visualizer_table(engine):
    """Test plan visualization in table format."""
    visualizer = QueryPlanVisualizer()

    plan_info = engine.get_query_plan("SELECT * FROM explain_test")
    formatted = visualizer.format_plan(plan_info, format="table")

    assert "┌" in formatted  # Table border
    assert "│" in formatted
    print("[PASS] Plan visualizer table format works")


def test_plan_visualizer_compact(engine):
    """Test plan visualization in compact format."""
    visualizer = QueryPlanVisualizer()

    plan_info = engine.get_query_plan("SELECT * FROM explain_test")
    formatted = visualizer.format_plan(plan_info, format="compact")

    assert "Plan" in formatted
    print("[PASS] Plan visualizer compact format works")


def test_plan_summary(engine):
    """Test plan summary extraction."""
    visualizer = QueryPlanVisualizer()

    plan_info = engine.get_query_plan("SELECT * FROM explain_test WHERE id = 1")
    summary = visualizer.get_plan_summary(plan_info)

    assert "backend" in summary
    assert "total_operations" in summary
    print(f"[PASS] Plan summary works: {summary['total_operations']} operations")


# ===== SQL Query Type Tests =====

def create_sql_test_engine():
    """Create engine with all test tables."""
    engine = NeuroLakeEngine()

    # Create select_test
    engine.execute_sql("""
        CREATE TABLE select_test AS
        SELECT 1 as id, 'Alice' as name, 25 as age
        UNION ALL SELECT 2, 'Bob', 30
        UNION ALL SELECT 3, 'Charlie', 35
    """)

    # Create join tables
    engine.execute_sql("""
        CREATE TABLE users_join AS
        SELECT 1 as user_id, 'Alice' as name
        UNION ALL SELECT 2, 'Bob'
        UNION ALL SELECT 3, 'Charlie'
    """)

    engine.execute_sql("""
        CREATE TABLE orders_join AS
        SELECT 1 as order_id, 1 as user_id, 100.0 as amount
        UNION ALL SELECT 2, 2, 200.0
    """)

    # Create sales table
    engine.execute_sql("""
        CREATE TABLE sales AS
        SELECT 'Electronics' as category, 100 as amount
        UNION ALL SELECT 'Electronics', 150
        UNION ALL SELECT 'Books', 50
        UNION ALL SELECT 'Books', 75
    """)

    return engine


def test_select_basic():
    """Test basic SELECT query."""
    engine = NeuroLakeEngine()

    result = engine.execute_sql("SELECT 1 as one, 2 as two, 3 as three")

    assert len(result) == 1
    assert result.iloc[0]["one"] == 1
    assert result.iloc[0]["two"] == 2
    print("[PASS] Basic SELECT works")


def test_select_with_where(engine):
    """Test SELECT with WHERE clause."""
    result = engine.execute_sql("SELECT * FROM select_test WHERE age > 25")

    assert len(result) == 2
    assert result.iloc[0]["name"] in ["Bob", "Charlie"]
    print("[PASS] SELECT with WHERE works")


def test_join_inner(engine):
    """Test INNER JOIN."""
    result = engine.execute_sql("""
        SELECT u.name, o.amount
        FROM users_join u
        INNER JOIN orders_join o ON u.user_id = o.user_id
    """)

    assert len(result) == 2
    print("[PASS] INNER JOIN works")


def test_join_left(engine):
    """Test LEFT JOIN."""
    result = engine.execute_sql("""
        SELECT u.name, o.amount
        FROM users_join u
        LEFT JOIN orders_join o ON u.user_id = o.user_id
    """)

    assert len(result) == 3  # Should include Charlie with NULL amount
    print("[PASS] LEFT JOIN works")


def test_aggregation_group_by(engine):
    """Test GROUP BY aggregation."""
    result = engine.execute_sql("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM sales
        GROUP BY category
    """)

    assert len(result) == 2
    electronics = result[result["category"] == "Electronics"].iloc[0]
    assert electronics["total"] == 250
    assert electronics["count"] == 2
    print("[PASS] GROUP BY aggregation works")


def test_aggregation_having(engine):
    """Test HAVING clause."""
    result = engine.execute_sql("""
        SELECT category, SUM(amount) as total
        FROM sales
        GROUP BY category
        HAVING SUM(amount) > 100
    """)

    # Both categories have totals > 100 (Electronics=250, Books=125)
    assert len(result) == 2
    print("[PASS] HAVING clause works")


def test_subquery(engine):
    """Test subquery."""
    result = engine.execute_sql("""
        SELECT *
        FROM sales
        WHERE amount > (SELECT AVG(amount) FROM sales)
    """)

    assert len(result) == 2  # 150 and 100 are above average
    print("[PASS] Subquery works")


def test_order_by(engine):
    """Test ORDER BY."""
    result = engine.execute_sql("""
        SELECT *
        FROM sales
        ORDER BY amount DESC
    """)

    assert result.iloc[0]["amount"] == 150  # Highest
    assert result.iloc[-1]["amount"] == 50  # Lowest
    print("[PASS] ORDER BY works")


def test_limit_offset(engine):
    """Test LIMIT and OFFSET."""
    result = engine.execute_sql("""
        SELECT *
        FROM sales
        ORDER BY amount
        LIMIT 2 OFFSET 1
    """)

    assert len(result) == 2
    assert result.iloc[0]["amount"] == 75  # Second lowest
    print("[PASS] LIMIT OFFSET works")


def run_manual_tests():
    """Run all tests manually."""
    print("=== Template Tests ===\n")
    test_query_template_basic()
    test_query_template_render()
    test_query_template_defaults()
    test_query_template_missing_param()
    test_template_registry()
    test_template_registry_create()

    print("\n=== Prepared Statement Tests ===\n")
    test_prepared_statement_basic()
    test_prepared_statement_execute()
    test_prepared_statement_reuse()
    test_prepared_statement_stats()

    print("\n=== EXPLAIN PLAN Tests ===\n")
    # Create shared engine for EXPLAIN tests
    engine = NeuroLakeEngine()
    engine.execute_sql("""
        CREATE TABLE explain_test AS
        SELECT 1 as id, 'Alice' as name
        UNION ALL SELECT 2, 'Bob'
    """)
    test_explain_basic(engine)
    test_explain_with_params(engine)
    test_get_query_plan(engine)

    print("\n=== Plan Visualization Tests ===\n")
    test_plan_visualizer_tree(engine)
    test_plan_visualizer_table(engine)
    test_plan_visualizer_compact(engine)
    test_plan_summary(engine)

    print("\n=== SQL Query Tests ===\n")
    test_select_basic()

    # Create shared engine for SQL tests
    sql_engine = create_sql_test_engine()
    test_select_with_where(sql_engine)
    test_join_inner(sql_engine)
    test_join_left(sql_engine)
    test_aggregation_group_by(sql_engine)
    test_aggregation_having(sql_engine)
    test_subquery(sql_engine)
    test_order_by(sql_engine)
    test_limit_offset(sql_engine)

    print("\n[SUCCESS] All advanced feature tests passed!")


if __name__ == "__main__":
    run_manual_tests()
