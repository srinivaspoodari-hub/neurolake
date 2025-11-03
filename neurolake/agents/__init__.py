"""
NeuroLake Agents Module

AI agents for autonomous data analysis and query execution.

Example:
    from neurolake.agents import Agent, Tool, AgentMemory, DataEngineerAgent

    # Create an agent
    agent = Agent(
        name="data_analyst",
        description="Analyzes data and answers questions"
    )

    # Create specialized agent
    engineer = DataEngineerAgent(
        name="data_engineer",
        llm_provider=llm
    )

    # Execute a task
    result = agent.execute("Find trends in sales data")

    # Build a pipeline
    pipeline = engineer.build_pipeline(
        source="raw_data",
        destination="clean_data",
        transformations=["clean", "deduplicate"]
    )
"""

from neurolake.agents.base import Agent, AgentState
from neurolake.agents.tools import Tool, ToolRegistry
from neurolake.agents.memory import AgentMemory, MemoryType
from neurolake.agents.coordinator import AgentCoordinator, TaskQueue
from neurolake.agents.data_engineer import (
    DataEngineerAgent,
    Pipeline,
    Transformation,
    PipelineStage,
    TransformationType
)

__all__ = [
    "Agent",
    "AgentState",
    "Tool",
    "ToolRegistry",
    "AgentMemory",
    "MemoryType",
    "AgentCoordinator",
    "TaskQueue",
    "DataEngineerAgent",
    "Pipeline",
    "Transformation",
    "PipelineStage",
    "TransformationType",
]
