"""
Tests for Prompts Module
"""

import pytest
from pathlib import Path
import tempfile

from neurolake.prompts import (
    PromptTemplate,
    PromptVersion,
    get_prompt,
    list_prompts,
    register_prompt
)
from neurolake.prompts.registry import clear_registry


# ===== PromptVersion Tests =====

def test_prompt_version_creation():
    """Test creating a prompt version."""
    version = PromptVersion(
        version="v1.0",
        template="Hello $name!",
        variables=["name"],
        description="Simple greeting"
    )

    assert version.version == "v1.0"
    assert version.template == "Hello $name!"
    assert "name" in version.variables


def test_prompt_version_render():
    """Test rendering a prompt version."""
    version = PromptVersion(
        version="v1.0",
        template="Query: $query\nTable: $table",
        variables=["query", "table"]
    )

    result = version.render(query="SELECT *", table="users")

    assert "Query: SELECT *" in result
    assert "Table: users" in result


def test_prompt_version_missing_variable():
    """Test rendering with missing variable."""
    version = PromptVersion(
        version="v1.0",
        template="Hello $name!",
        variables=["name"]
    )

    with pytest.raises(ValueError, match="Missing required variables"):
        version.render()  # Missing 'name'


# ===== PromptTemplate Tests =====

def test_prompt_template_creation():
    """Test creating a prompt template."""
    template = PromptTemplate(
        name="test_prompt",
        description="Test prompt"
    )

    assert template.name == "test_prompt"
    assert template.description == "Test prompt"
    assert len(template.versions) == 0


def test_prompt_template_add_version():
    """Test adding versions to a template."""
    template = PromptTemplate(name="test")

    template.add_version(
        version="v1.0",
        template="Test: $value",
        variables=["value"]
    )

    template.add_version(
        version="v2.0",
        template="Enhanced Test: $value with $extra",
        variables=["value", "extra"]
    )

    assert len(template.versions) == 2
    assert "v1.0" in template.versions
    assert "v2.0" in template.versions


def test_prompt_template_render():
    """Test rendering a template."""
    template = PromptTemplate(name="test")

    template.add_version(
        version="v1.0",
        template="User: $user\nQuery: $query",
        variables=["user", "query"]
    )

    result = template.render(user="Alice", query="SELECT *")

    assert "User: Alice" in result
    assert "Query: SELECT *" in result


def test_prompt_template_render_specific_version():
    """Test rendering a specific version."""
    template = PromptTemplate(name="test")

    template.add_version(
        version="v1.0",
        template="V1: $value",
        variables=["value"]
    )

    template.add_version(
        version="v2.0",
        template="V2: $value",
        variables=["value"]
    )

    result = template.render(version="v1.0", value="test")
    assert "V1: test" in result

    result = template.render(version="v2.0", value="test")
    assert "V2: test" in result


def test_prompt_template_performance_tracking():
    """Test performance tracking."""
    template = PromptTemplate(name="test")

    template.add_version(
        version="v1.0",
        template="Test",
        variables=[]
    )

    template.add_version(
        version="v2.0",
        template="Test",
        variables=[]
    )

    # Record performance
    template.record_performance("v1.0", 0.8, {"accuracy": 0.85})
    template.record_performance("v2.0", 0.95, {"accuracy": 0.92})

    assert len(template.performance_history) == 2
    assert template.get_best_version() == "v2.0"


def test_prompt_template_save_load():
    """Test saving and loading templates."""
    template = PromptTemplate(name="test", description="Test template")

    template.add_version(
        version="v1.0",
        template="Test: $value",
        variables=["value"]
    )

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        template.save(temp_path)

        # Load back
        loaded = PromptTemplate.load(temp_path)

        assert loaded.name == template.name
        assert loaded.description == template.description
        assert "v1.0" in loaded.versions

        # Test rendering works
        result = loaded.render(value="test")
        assert "Test: test" in result

    finally:
        Path(temp_path).unlink()


# ===== Registry Tests =====

def test_list_builtin_prompts():
    """Test listing built-in prompts."""
    prompts = list_prompts()

    assert "intent_parser" in prompts
    assert "sql_generator" in prompts
    assert "query_optimizer" in prompts
    assert "error_diagnostician" in prompts
    assert "data_summarizer" in prompts


def test_get_prompt():
    """Test getting a prompt by name."""
    template = get_prompt("intent_parser")

    assert template.name == "intent_parser"
    assert len(template.versions) > 0


def test_get_prompt_not_found():
    """Test getting a non-existent prompt."""
    with pytest.raises(KeyError, match="not found"):
        get_prompt("nonexistent_prompt")


def test_register_custom_prompt():
    """Test registering a custom prompt."""
    clear_registry()  # Start fresh

    custom = PromptTemplate(name="custom_prompt")
    custom.add_version(
        version="v1.0",
        template="Custom: $value",
        variables=["value"]
    )

    register_prompt(custom)

    # Should be able to retrieve it
    retrieved = get_prompt("custom_prompt")
    assert retrieved.name == "custom_prompt"

    clear_registry()  # Cleanup


# ===== Integration Tests =====

def test_intent_parser_prompt_rendering():
    """Test rendering the intent parser prompt."""
    template = get_prompt("intent_parser")

    result = template.render(user_query="Show me all users")

    assert "Show me all users" in result
    assert "intent" in result.lower()
    assert "json" in result.lower()


def test_sql_generator_prompt_rendering():
    """Test rendering the SQL generator prompt."""
    template = get_prompt("sql_generator")

    result = template.render(
        schema="users(id, name, age)",
        user_query="Get all users",
        intent='{"intent": "select"}'
    )

    assert "users(id, name, age)" in result
    assert "Get all users" in result


def test_all_prompts_have_versions():
    """Test that all built-in prompts have at least one version."""
    for prompt_name in list_prompts():
        template = get_prompt(prompt_name)
        assert len(template.versions) > 0, f"{prompt_name} has no versions"


def test_all_prompts_can_render():
    """Test that all built-in prompts can render with required variables."""
    # Intent parser
    template = get_prompt("intent_parser")
    result = template.render(user_query="test query")
    assert result

    # SQL generator
    template = get_prompt("sql_generator")
    result = template.render(
        schema="test",
        user_query="test",
        intent="test",
        query_history="none"
    )
    assert result

    # Optimizer
    template = get_prompt("query_optimizer")
    result = template.render(
        query="SELECT *",
        execution_plan="plan",
        execution_time=100,
        rows_scanned=1000,
        rows_returned=100,
        memory_used=10
    )
    assert result

    # Error diagnostician
    template = get_prompt("error_diagnostician")
    result = template.render(
        query="SELECT *",
        error_message="syntax error",
        schema="test"
    )
    assert result

    # Data summarizer
    template = get_prompt("data_summarizer")
    result = template.render(
        user_query="test",
        sql_query="SELECT *",
        results="data",
        context="none"
    )
    assert result

    # Schema explainer
    template = get_prompt("schema_explainer")
    result = template.render(schema="test schema")
    assert result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
