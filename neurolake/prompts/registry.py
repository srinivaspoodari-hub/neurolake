"""
Prompt Registry

Central registry for all prompt templates.
"""

from typing import Dict, List
from neurolake.prompts.template import PromptTemplate
from neurolake.prompts import library


# Global registry
_PROMPT_REGISTRY: Dict[str, PromptTemplate] = {}


def _initialize_registry():
    """Initialize registry with built-in prompts."""
    if _PROMPT_REGISTRY:
        return  # Already initialized

    # Register all built-in prompts
    register_prompt(library.create_intent_parser_prompt())
    register_prompt(library.create_sql_generation_prompt())
    register_prompt(library.create_optimization_prompt())
    register_prompt(library.create_error_diagnosis_prompt())
    register_prompt(library.create_summarization_prompt())
    register_prompt(library.create_schema_explainer_prompt())


def register_prompt(template: PromptTemplate):
    """
    Register a prompt template.

    Args:
        template: Prompt template to register
    """
    _PROMPT_REGISTRY[template.name] = template


def get_prompt(name: str) -> PromptTemplate:
    """
    Get a prompt template by name.

    Args:
        name: Template name

    Returns:
        PromptTemplate

    Raises:
        KeyError: If template not found
    """
    _initialize_registry()

    if name not in _PROMPT_REGISTRY:
        raise KeyError(
            f"Prompt '{name}' not found. "
            f"Available prompts: {list(_PROMPT_REGISTRY.keys())}"
        )

    return _PROMPT_REGISTRY[name]


def list_prompts() -> List[str]:
    """
    List all registered prompts.

    Returns:
        List of prompt names
    """
    _initialize_registry()
    return list(_PROMPT_REGISTRY.keys())


def clear_registry():
    """Clear the prompt registry (mainly for testing)."""
    _PROMPT_REGISTRY.clear()


__all__ = ["register_prompt", "get_prompt", "list_prompts", "clear_registry"]
