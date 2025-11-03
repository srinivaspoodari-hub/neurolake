"""
NeuroLake Prompts Module

Prompt templates for natural language to SQL, intent parsing, and more.

Example:
    from neurolake.prompts import PromptTemplate, get_prompt

    # Get a pre-built prompt
    template = get_prompt("intent_parser")

    # Render with variables
    prompt = template.render(user_query="Show me all users")
    print(prompt)
"""

from neurolake.prompts.template import PromptTemplate, PromptVersion
from neurolake.prompts.registry import get_prompt, list_prompts, register_prompt

__all__ = [
    "PromptTemplate",
    "PromptVersion",
    "get_prompt",
    "list_prompts",
    "register_prompt",
]
