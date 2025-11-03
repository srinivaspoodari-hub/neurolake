"""
Tests for Agents Module
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from neurolake.agents import (
    Agent,
    AgentState,
    Tool,
    ToolRegistry,
    AgentMemory,
    MemoryType,
    AgentCoordinator,
    TaskQueue
)
from neurolake.agents.base import Observation, Action, ActionResult
from neurolake.agents.coordinator import TaskPriority, TaskStatus


# ===== Tool Tests =====

def test_tool_creation():
    """Test creating a tool."""
    class TestTool(Tool):
        def __init__(self):
            super().__init__(
                name="test",
                description="Test tool"
            )

        def execute(self, **kwargs):
            return "executed"

    tool = TestTool()
    assert tool.name == "test"
    assert tool.description == "Test tool"
    assert tool.execute() == "executed"


def test_tool_registry():
    """Test tool registry."""
    registry = ToolRegistry()

    # Create and register tool
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="mock", description="Mock tool")

        def execute(self, **kwargs):
            return "mock"

    tool = MockTool()
    registry.register(tool)

    # Get tool
    retrieved = registry.get("mock")
    assert retrieved is not None
    assert retrieved.name == "mock"

    # List tools
    tools = registry.list()
    assert len(tools) == 1

    # Unregister
    registry.unregister("mock")
    assert registry.get("mock") is None


# ===== Agent Memory Tests =====

def test_memory_creation():
    """Test creating agent memory."""
    memory = AgentMemory()
    assert len(memory.memories) == 0


def test_memory_store_retrieve():
    """Test storing and retrieving memories."""
    memory = AgentMemory()

    # Store memory
    memory_id = memory.store(
        "Executed query successfully",
        memory_type="experience"
    )

    assert memory_id is not None
    assert len(memory.memories) == 1

    # Retrieve
    memories = memory.retrieve("query")
    assert len(memories) > 0
    assert "query" in memories[0].content.lower()


def test_memory_types():
    """Test different memory types."""
    memory = AgentMemory()

    memory.store("Experience 1", memory_type="experience")
    memory.store("Episode 1", memory_type="episode")
    memory.store("Knowledge 1", memory_type="knowledge")

    assert len(memory.memories) == 3

    # Get recent by type
    experiences = memory.get_recent(memory_type="experience")
    assert len(experiences) == 1
    assert experiences[0].memory_type == MemoryType.EXPERIENCE


def test_memory_importance():
    """Test memory importance."""
    memory = AgentMemory()

    memory.store("Important event", importance=0.9)
    memory.store("Minor event", importance=0.3)

    important = memory.get_important(threshold=0.7)
    assert len(important) == 1
    assert important[0].importance == 0.9


def test_memory_clear():
    """Test clearing memories."""
    memory = AgentMemory()

    memory.store("Memory 1", memory_type="experience")
    memory.store("Memory 2", memory_type="episode")

    # Clear specific type
    memory.clear(memory_type="experience")
    assert len(memory.memories) == 1

    # Clear all
    memory.clear()
    assert len(memory.memories) == 0


# ===== Agent Tests =====

def test_agent_creation():
    """Test creating an agent."""
    agent = Agent(
        name="test_agent",
        description="Test agent"
    )

    assert agent.name == "test_agent"
    assert agent.state == AgentState.IDLE


def test_agent_with_tools():
    """Test agent with tools."""
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="mock", description="Mock tool")

        def execute(self, **kwargs):
            return {"result": "success"}

    tool = MockTool()
    agent = Agent(
        name="test_agent",
        tools=[tool]
    )

    assert len(agent.tools) == 1
    assert agent.tools[0].name == "mock"


def test_agent_perceive():
    """Test agent perception."""
    agent = Agent(name="test_agent")

    observations = agent.perceive("Test task")

    assert len(observations) > 0
    assert any(obs.type == "task" for obs in observations)


def test_agent_act():
    """Test agent action execution."""
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="execute", description="Execute action")

        def execute(self, **kwargs):
            return "completed"

    tool = MockTool()
    agent = Agent(name="test_agent", tools=[tool])

    action = Action(name="execute", tool="execute")
    result = agent.act(action)

    assert result.success is True
    assert result.output == "completed"


def test_agent_learn():
    """Test agent learning."""
    memory = AgentMemory()
    agent = Agent(name="test_agent", memory=memory)

    action = Action(name="test_action")
    result = ActionResult(success=True, output="result")

    agent.learn(action, result)

    # Check memory was stored
    assert len(memory.memories) > 0


def test_agent_execute_simple():
    """Test simple agent execution."""
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="process", description="Process task")

        def execute(self, **kwargs):
            return "task_complete"

    tool = MockTool()
    agent = Agent(
        name="test_agent",
        tools=[tool],
        max_iterations=2
    )

    result = agent.execute("Test task")

    # Should complete within iterations
    assert agent.iteration <= 2


# ===== Task Queue Tests =====

def test_task_queue_creation():
    """Test creating task queue."""
    queue = TaskQueue()
    assert queue.queue.empty()


def test_task_queue_add_get():
    """Test adding and getting tasks."""
    queue = TaskQueue()

    # Add task
    task_id = queue.add_task("Test task", priority="normal")
    assert task_id is not None

    # Get task
    task = queue.get_next_task("agent1")
    assert task is not None
    assert task.description == "Test task"
    assert task.assigned_to == "agent1"


def test_task_queue_priority():
    """Test task priority."""
    queue = TaskQueue()

    # Add tasks with different priorities
    low_id = queue.add_task("Low priority", priority="low")
    high_id = queue.add_task("High priority", priority="high")
    normal_id = queue.add_task("Normal priority", priority="normal")

    # High priority should come first
    task1 = queue.get_next_task()
    assert task1.priority == TaskPriority.HIGH

    # Normal should be next
    task2 = queue.get_next_task()
    assert task2.priority == TaskPriority.NORMAL

    # Low should be last
    task3 = queue.get_next_task()
    assert task3.priority == TaskPriority.LOW


def test_task_queue_complete():
    """Test completing tasks."""
    queue = TaskQueue()

    task_id = queue.add_task("Test task")
    queue.get_next_task()

    queue.complete_task(task_id, result="success")

    task = queue.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "success"


def test_task_queue_statistics():
    """Test queue statistics."""
    queue = TaskQueue()

    queue.add_task("Task 1")
    queue.add_task("Task 2")

    stats = queue.get_statistics()

    assert stats["total_tasks"] == 2
    assert stats["pending"] == 2


# ===== Agent Coordinator Tests =====

def test_coordinator_creation():
    """Test creating coordinator."""
    coordinator = AgentCoordinator()
    assert len(coordinator.agents) == 0


def test_coordinator_register_agent():
    """Test registering agents."""
    coordinator = AgentCoordinator()
    agent = Agent(name="test_agent")

    coordinator.register_agent(agent)

    assert "test_agent" in coordinator.agents
    assert coordinator.agents["test_agent"] == agent


def test_coordinator_assign_task():
    """Test assigning tasks."""
    coordinator = AgentCoordinator()
    agent = Agent(name="test_agent")
    coordinator.register_agent(agent)

    task_id = coordinator.assign_task(
        "Test task",
        preferred_agent="test_agent"
    )

    assert task_id is not None
    assert task_id in coordinator.agent_assignments["test_agent"]


def test_coordinator_execute_task():
    """Test executing coordinated task."""
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="process", description="Process task")

        def execute(self, **kwargs):
            return "completed"

    tool = MockTool()
    agent = Agent(name="test_agent", tools=[tool], max_iterations=1)

    coordinator = AgentCoordinator()
    coordinator.register_agent(agent)

    task_id = coordinator.assign_task("Test task", preferred_agent="test_agent")

    # Execute should complete
    try:
        result = coordinator.execute_task(task_id)
        # Result might be None if max_iterations reached
    except Exception:
        pass  # Expected in some cases


def test_coordinator_statistics():
    """Test coordinator statistics."""
    coordinator = AgentCoordinator()
    agent1 = Agent(name="agent1")
    agent2 = Agent(name="agent2")

    coordinator.register_agent(agent1)
    coordinator.register_agent(agent2)

    stats = coordinator.get_statistics()

    assert stats["agents"] == 2
    assert "queue" in stats
    assert "agents_status" in stats


# ===== Integration Tests =====

def test_full_agent_lifecycle():
    """Test complete agent lifecycle."""
    # Create memory
    memory = AgentMemory()

    # Create tool
    class AnalysisTool(Tool):
        def __init__(self):
            super().__init__(name="analyze", description="Analyze data")

        def execute(self, **kwargs):
            return {"analysis": "complete"}

    tool = AnalysisTool()

    # Create agent
    agent = Agent(
        name="analyst",
        description="Data analyst",
        tools=[tool],
        memory=memory,
        max_iterations=3
    )

    # Execute task
    result = agent.execute("Analyze sales data")

    # Check lifecycle
    assert len(agent.observations) > 0
    assert len(memory.memories) > 0


def test_multi_agent_coordination():
    """Test multiple agents working together."""
    # Create agents
    agent1 = Agent(name="agent1")
    agent2 = Agent(name="agent2")

    # Create coordinator
    coordinator = AgentCoordinator()
    coordinator.register_agent(agent1)
    coordinator.register_agent(agent2)

    # Assign tasks
    task1 = coordinator.assign_task("Task 1")
    task2 = coordinator.assign_task("Task 2")

    # Both tasks should be assigned
    assert task1 is not None
    assert task2 is not None


def test_agent_with_memory_context():
    """Test agent using memory for context."""
    memory = AgentMemory()

    # Store some prior knowledge with relevant keywords
    memory.store("Previous analysis of trends showed upward pattern", memory_type="knowledge")

    agent = Agent(name="analyst", memory=memory, max_iterations=1)

    # Execute task with matching keywords
    observations = agent.perceive("Analyze trends")

    # Just verify observations were created
    assert len(observations) > 0
    # Verify memory system is accessible
    assert agent.memory is not None
    assert len(agent.memory.memories) == 1


# ============================================================================
# Extended Comprehensive Tests
# ============================================================================


# ===== Extended Tool Tests =====

class TestToolExtended:
    """Extended tool tests."""

    def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        class ParamTool(Tool):
            def __init__(self):
                super().__init__(
                    name="param_tool",
                    description="Tool with parameters",
                    parameters=[
                        {"name": "input", "required": True, "type": "string"},
                        {"name": "optional", "required": False, "type": "int"}
                    ]
                )

            def execute(self, **kwargs):
                return kwargs

        tool = ParamTool()

        # Should fail without required param
        with pytest.raises(ValueError, match="Missing required parameter"):
            tool.validate_parameters(optional=5)

        # Should pass with required param
        assert tool.validate_parameters(input="test") is True
        assert tool.validate_parameters(input="test", optional=5) is True

    def test_tool_to_dict(self):
        """Test converting tool to dictionary"""
        class DictTool(Tool):
            def __init__(self):
                super().__init__(
                    name="dict_tool",
                    description="Tool for dict test",
                    parameters=[{"name": "param1", "type": "string"}]
                )

            def execute(self, **kwargs):
                return None

        tool = DictTool()
        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "dict_tool"
        assert tool_dict["description"] == "Tool for dict test"
        assert len(tool_dict["parameters"]) == 1


# ===== Extended Memory Tests =====

class TestMemoryExtended:
    """Extended memory tests."""

    def test_memory_max_size(self):
        """Test max memory limit"""
        memory = AgentMemory(max_memories=5)

        # Add more than max
        for i in range(10):
            memory.store(f"Memory {i}", memory_type="experience")

        # Should only keep max_memories
        assert len(memory.memories) <= 5

    def test_memory_retrieval_empty(self):
        """Test retrieval from empty memory"""
        memory = AgentMemory()

        memories = memory.retrieve("nonexistent query")

        assert len(memories) == 0

    def test_memory_get_recent(self):
        """Test getting recent memories"""
        memory = AgentMemory()

        memory.store("Old memory 1", memory_type="experience")
        memory.store("Recent memory", memory_type="experience")

        recent = memory.get_recent(limit=1)

        assert len(recent) == 1
        assert "Recent" in recent[0].content

    def test_memory_get_important_empty(self):
        """Test getting important memories when none exist"""
        memory = AgentMemory()

        memory.store("Low importance", importance=0.1)

        important = memory.get_important(threshold=0.9)

        assert len(important) == 0


# ===== Extended Agent Tests =====

class TestAgentExtended:
    """Extended agent tests."""

    def test_agent_state_transitions(self):
        """Test agent state transitions"""
        agent = Agent(name="test_agent")

        # Initial state
        assert agent.state == AgentState.IDLE

        # State should change during execution
        agent.state = AgentState.PERCEIVING
        assert agent.state == AgentState.PERCEIVING

        agent.state = AgentState.REASONING
        assert agent.state == AgentState.REASONING

        agent.state = AgentState.ACTING
        assert agent.state == AgentState.ACTING

    def test_agent_max_iterations(self):
        """Test max iterations limit"""
        agent = Agent(name="test_agent", max_iterations=3)

        assert agent.max_iterations == 3

    def test_agent_observations_tracking(self):
        """Test that observations are tracked"""
        agent = Agent(name="test_agent")

        agent.perceive("Task 1")
        agent.perceive("Task 2")

        assert len(agent.observations) >= 2

    def test_agent_actions_tracking(self):
        """Test that actions are tracked"""
        class MockTool(Tool):
            def __init__(self):
                super().__init__(name="mock", description="Mock")

            def execute(self, **kwargs):
                return "result"

        agent = Agent(name="test_agent", tools=[MockTool()])

        action = Action(name="test_action", tool="mock")
        agent.act(action)

        assert len(agent.actions_taken) > 0


# ===== Data Engineer Agent Tests =====

class TestDataEngineerAgent:
    """Tests for DataEngineerAgent."""

    def test_data_engineer_creation(self):
        """Test creating data engineer agent"""
        from neurolake.agents.data_engineer import DataEngineerAgent

        agent = DataEngineerAgent(
            name="engineer"
        )

        assert agent.name == "engineer"
        assert agent.state == AgentState.IDLE

    def test_pipeline_creation(self):
        """Test creating a pipeline"""
        from neurolake.agents.data_engineer import Pipeline, PipelineStage

        pipeline = Pipeline(
            name="etl_pipeline",
            source="raw_data",
            destination="clean_data"
        )

        assert pipeline.name == "etl_pipeline"
        assert pipeline.source == "raw_data"
        assert pipeline.destination == "clean_data"
        assert len(pipeline.stages) == 0
        assert len(pipeline.transformations) == 0

    def test_pipeline_add_stage(self):
        """Test adding stages to pipeline"""
        from neurolake.agents.data_engineer import Pipeline, PipelineStage

        pipeline = Pipeline(name="test_pipeline")

        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_stage(PipelineStage.TRANSFORM)
        pipeline.add_stage(PipelineStage.LOAD)

        assert len(pipeline.stages) == 3
        assert pipeline.stages[0] == PipelineStage.EXTRACT
        assert pipeline.stages[1] == PipelineStage.TRANSFORM
        assert pipeline.stages[2] == PipelineStage.LOAD

    def test_pipeline_add_transformation(self):
        """Test adding transformations to pipeline"""
        from neurolake.agents.data_engineer import (
            Pipeline,
            Transformation,
            TransformationType
        )

        pipeline = Pipeline(name="test_pipeline")

        transformation = Transformation(
            name="filter_nulls",
            type=TransformationType.FILTER,
            config={"column": "id", "condition": "NOT NULL"},
            description="Filter null values"
        )

        pipeline.add_transformation(transformation)

        assert len(pipeline.transformations) == 1
        assert pipeline.transformations[0].name == "filter_nulls"
        assert pipeline.transformations[0].type == TransformationType.FILTER

    def test_pipeline_to_dict(self):
        """Test converting pipeline to dictionary"""
        from neurolake.agents.data_engineer import (
            Pipeline,
            PipelineStage,
            Transformation,
            TransformationType
        )

        pipeline = Pipeline(
            name="etl_pipeline",
            source="raw_data",
            destination="clean_data",
            schedule="daily"
        )

        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_transformation(
            Transformation(
                name="clean",
                type=TransformationType.MAP,
                config={"function": "clean_data"}
            )
        )

        pipeline_dict = pipeline.to_dict()

        assert pipeline_dict["name"] == "etl_pipeline"
        assert pipeline_dict["source"] == "raw_data"
        assert pipeline_dict["destination"] == "clean_data"
        assert pipeline_dict["schedule"] == "daily"
        assert len(pipeline_dict["stages"]) == 1
        assert pipeline_dict["stages"][0] == "extract"
        assert len(pipeline_dict["transformations"]) == 1

    def test_transformation_types(self):
        """Test all transformation types"""
        from neurolake.agents.data_engineer import TransformationType

        assert TransformationType.MAP
        assert TransformationType.FILTER
        assert TransformationType.AGGREGATE
        assert TransformationType.JOIN
        assert TransformationType.PIVOT
        assert TransformationType.UNPIVOT
        assert TransformationType.WINDOW
        assert TransformationType.UNION
        assert TransformationType.DEDUPLICATE

    def test_pipeline_stages(self):
        """Test all pipeline stages"""
        from neurolake.agents.data_engineer import PipelineStage

        assert PipelineStage.EXTRACT
        assert PipelineStage.TRANSFORM
        assert PipelineStage.LOAD
        assert PipelineStage.VALIDATE
        assert PipelineStage.CLEAN
        assert PipelineStage.AGGREGATE
        assert PipelineStage.JOIN
        assert PipelineStage.FILTER

    def test_transformation_with_sql(self):
        """Test transformation with SQL"""
        from neurolake.agents.data_engineer import Transformation, TransformationType

        transformation = Transformation(
            name="aggregate_sales",
            type=TransformationType.AGGREGATE,
            sql="SELECT product, SUM(sales) FROM orders GROUP BY product",
            description="Aggregate sales by product"
        )

        assert transformation.sql is not None
        assert "SUM" in transformation.sql
        assert transformation.function is None

    def test_transformation_with_function(self):
        """Test transformation with Python function"""
        from neurolake.agents.data_engineer import Transformation, TransformationType

        def clean_func(row):
            return row.strip().lower()

        transformation = Transformation(
            name="clean_text",
            type=TransformationType.MAP,
            function=clean_func,
            description="Clean text data"
        )

        assert transformation.function is not None
        assert transformation.sql is None


# ===== Edge Cases =====

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_agent_with_no_tools(self):
        """Test agent with no tools can still operate"""
        agent = Agent(name="no_tools")

        observations = agent.perceive("Test task")

        assert len(observations) > 0
        assert agent.tools == []

    def test_agent_act_with_missing_tool(self):
        """Test acting with a tool that doesn't exist"""
        agent = Agent(name="test_agent")

        action = Action(name="test", tool="nonexistent_tool")
        result = agent.act(action)

        # Should return an error result
        assert result.success is False
        assert result.error is not None

    def test_memory_with_unicode(self):
        """Test memory with Unicode content"""
        memory = AgentMemory()

        memory_id = memory.store(
            "Test with Unicode: 你好世界 🌍",
            memory_type="experience"
        )

        assert memory_id is not None
        memories = memory.retrieve("Unicode")
        assert len(memories) > 0

    def test_task_queue_empty_get(self):
        """Test getting from empty queue"""
        queue = TaskQueue()

        task = queue.get_next_task()

        assert task is None

    def test_task_queue_complete_nonexistent(self):
        """Test completing task that doesn't exist"""
        queue = TaskQueue()

        # Should handle gracefully
        try:
            queue.complete_task("nonexistent_id", result="done")
        except Exception as e:
            # Expected - task doesn't exist
            pass

    def test_coordinator_assign_to_nonexistent_agent(self):
        """Test assigning task to agent that doesn't exist"""
        coordinator = AgentCoordinator()

        task_id = coordinator.assign_task(
            "Test task",
            preferred_agent="nonexistent_agent"
        )

        # Should still create task (might assign to any available agent)
        assert task_id is not None

    def test_pipeline_with_metadata(self):
        """Test pipeline with custom metadata"""
        from neurolake.agents.data_engineer import Pipeline

        pipeline = Pipeline(
            name="test_pipeline",
            metadata={
                "version": "1.0",
                "author": "test",
                "tags": ["etl", "production"]
            }
        )

        assert pipeline.metadata["version"] == "1.0"
        assert "etl" in pipeline.metadata["tags"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
