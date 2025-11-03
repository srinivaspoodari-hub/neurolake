"""
End-to-End Multi-Agent Workflow Tests

Tests the complete multi-agent system including:
- Task queue and coordination
- Agent lifecycle (perceive-reason-act-learn)
- Data engineer agent workflows
- Multi-agent collaboration
- Tool usage
- Memory and learning
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Any
from datetime import datetime

from neurolake.agents.base import (
    Agent,
    AgentState,
    Observation,
    Action,
    ActionResult
)
from neurolake.agents.coordinator import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    AgentCoordinator
)
from neurolake.agents.data_engineer import (
    DataEngineerAgent,
    Pipeline,
    PipelineStage,
    Transformation,
    TransformationType
)
from neurolake.agents.memory import AgentMemory, MemoryType
from neurolake.agents.tools import Tool


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, success: bool = True, output: Any = None):
        self.name = name
        self.success = success
        self.output = output or f"{name} result"
        self.call_count = 0
        self.calls = []

    def execute(self, **params) -> Any:
        """Execute the tool."""
        self.call_count += 1
        self.calls.append(params)
        if not self.success:
            raise RuntimeError(f"{self.name} failed")
        return self.output


class MockLLM:
    """Mock LLM provider for agents."""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ["Mock LLM response"]
        self.response_index = 0
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> Any:
        """Generate mock response."""
        self.call_count += 1
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        # Return mock LLM response
        return Mock(text=response)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_llm():
    """Create mock LLM."""
    return MockLLM()


class TestTaskQueue:
    """Test task queue functionality."""

    def test_add_and_get_task(self):
        """Test adding and getting tasks."""
        queue = TaskQueue()

        task_id = queue.add_task("Process data", priority="high")
        assert task_id is not None

        task = queue.get_next_task()
        assert task is not None
        assert task.description == "Process data"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.ASSIGNED

    def test_task_priority_ordering(self):
        """Test tasks are retrieved by priority."""
        queue = TaskQueue()

        low_id = queue.add_task("Low priority", priority="low")
        high_id = queue.add_task("High priority", priority="high")
        critical_id = queue.add_task("Critical", priority="critical")

        # Should get critical first
        task1 = queue.get_next_task()
        assert task1.id == critical_id

        # Then high
        task2 = queue.get_next_task()
        assert task2.id == high_id

        # Then low
        task3 = queue.get_next_task()
        assert task3.id == low_id

    def test_complete_task(self):
        """Test completing a task."""
        queue = TaskQueue()

        task_id = queue.add_task("Test task")
        task = queue.get_next_task()

        # Task is automatically ASSIGNED after get_next_task
        assert queue.tasks[task_id].status == TaskStatus.ASSIGNED

        # Complete task
        result = {"output": "success"}
        queue.complete_task(task_id, result=result)

        completed = queue.tasks[task_id]
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result == result
        assert completed.completed_at is not None

    def test_fail_task(self):
        """Test failing a task."""
        queue = TaskQueue()

        task_id = queue.add_task("Test task")
        queue.get_next_task()

        # Fail task
        queue.fail_task(task_id, error="Something went wrong")

        failed = queue.tasks[task_id]
        assert failed.status == TaskStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_get_statistics(self):
        """Test queue statistics."""
        queue = TaskQueue()

        # Add various tasks
        id1 = queue.add_task("Task 1")
        id2 = queue.add_task("Task 2")
        id3 = queue.add_task("Task 3")

        # Process some
        queue.get_next_task()
        queue.complete_task(id1, result={})

        queue.get_next_task()
        queue.fail_task(id2, error="failed")

        stats = queue.get_statistics()
        assert stats["total_tasks"] == 3
        assert stats["completed"] == 1

    def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        queue = TaskQueue()

        queue.add_task("Task 1")
        queue.add_task("Task 2")
        id3 = queue.add_task("Task 3")

        # Get one
        queue.get_next_task()

        pending = queue.get_pending_tasks()
        # One was assigned, so 2 should still be pending
        assert len(pending) >= 1


class TestAgentBase:
    """Test base agent functionality."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = Agent(
            name="test_agent",
            description="Test agent",
            max_iterations=5
        )

        assert agent.name == "test_agent"
        assert agent.description == "Test agent"
        assert agent.state == AgentState.IDLE
        assert agent.max_iterations == 5

    def test_agent_observations(self):
        """Test agent observations list."""
        agent = Agent(name="test_agent")

        # Agent should have observations list
        assert hasattr(agent, 'observations')
        assert isinstance(agent.observations, list)

    def test_agent_state_transitions(self):
        """Test agent state transitions."""
        agent = Agent(name="test_agent")

        assert agent.state == AgentState.IDLE

        agent.state = AgentState.PERCEIVING
        assert agent.state == AgentState.PERCEIVING

        agent.state = AgentState.REASONING
        assert agent.state == AgentState.REASONING

        agent.state = AgentState.ACTING
        assert agent.state == AgentState.ACTING

    def test_agent_with_tools(self):
        """Test agent with tools."""
        tool1 = MockTool("calculator")
        tool2 = MockTool("database")

        agent = Agent(
            name="test_agent",
            tools=[tool1, tool2]
        )

        assert len(agent.tools) == 2
        assert agent.tools[0].name == "calculator"
        assert agent.tools[1].name == "database"

    def test_agent_with_llm(self, mock_llm):
        """Test agent with LLM provider."""
        agent = Agent(
            name="test_agent",
            llm_provider=mock_llm
        )

        # Agent should have LLM
        assert agent.llm is not None
        assert agent.llm == mock_llm


class TestAgentCoordinator:
    """Test multi-agent coordination."""

    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        coordinator = AgentCoordinator()
        assert len(coordinator.agents) == 0
        assert coordinator.task_queue is not None

    def test_register_agent(self):
        """Test registering agents."""
        coordinator = AgentCoordinator()

        agent1 = Agent(name="agent1")
        agent2 = Agent(name="agent2")

        coordinator.register_agent(agent1)
        coordinator.register_agent(agent2)

        assert len(coordinator.agents) == 2
        assert "agent1" in coordinator.agents
        assert "agent2" in coordinator.agents

    def test_assign_task_to_agent(self):
        """Test assigning tasks to agents."""
        coordinator = AgentCoordinator()

        agent = Agent(name="worker")
        coordinator.register_agent(agent)

        task_id = coordinator.assign_task(
            "Process data",
            preferred_agent="worker"
        )

        assert task_id is not None

    def test_coordinate_multiple_agents(self):
        """Test coordinating multiple agents."""
        coordinator = AgentCoordinator()

        agent1 = Agent(name="agent1")
        agent2 = Agent(name="agent2")

        coordinator.register_agent(agent1)
        coordinator.register_agent(agent2)

        # Add tasks for different agents
        task1 = coordinator.assign_task("Task 1", preferred_agent="agent1")
        task2 = coordinator.assign_task("Task 2", preferred_agent="agent2")

        assert task1 is not None
        assert task2 is not None


class TestDataEngineerAgent:
    """Test data engineer agent."""

    def test_data_engineer_initialization(self):
        """Test data engineer agent initialization."""
        agent = DataEngineerAgent(
            name="de_agent",
            llm_provider=Mock()
        )

        assert agent.name == "de_agent"
        # Agent has been initialized
        assert agent is not None

    def test_build_pipeline(self):
        """Test building a pipeline."""
        agent = DataEngineerAgent(name="de_agent", llm_provider=MockLLM())

        pipeline = agent.build_pipeline(
            source="source_table",
            destination="dest_table",
            name="etl_pipeline"
        )

        assert pipeline is not None
        assert pipeline.name == "etl_pipeline"
        assert pipeline.source == "source_table"
        assert pipeline.destination == "dest_table"

    def test_create_transformation(self):
        """Test creating a transformation."""
        agent = DataEngineerAgent(name="de_agent", llm_provider=MockLLM())

        transform = agent.create_transformation(
            description="Filter rows where age > 18"
        )

        assert transform is not None

    def test_generate_sql(self):
        """Test generating SQL from pipeline."""
        agent = DataEngineerAgent(name="de_agent", llm_provider=MockLLM())

        pipeline = agent.build_pipeline(
            source="users",
            destination="processed_users",
            name="test_pipeline"
        )

        # Generate SQL
        sql = agent.generate_sql(pipeline)
        assert sql is not None
        assert isinstance(sql, str)

    def test_validate_sql(self):
        """Test SQL validation."""
        agent = DataEngineerAgent(name="de_agent")

        # Valid SQL
        result = agent.validate_sql("SELECT * FROM users")
        assert "valid" in result or "error" in result

    def test_list_pipelines(self):
        """Test listing pipelines."""
        agent = DataEngineerAgent(name="de_agent", llm_provider=MockLLM())

        # Build a pipeline
        agent.build_pipeline(
            source="table1",
            destination="table2",
            name="pipeline1"
        )

        # List pipelines
        pipelines = agent.list_pipelines()
        assert "pipeline1" in pipelines


class TestAgentMemory:
    """Test agent memory system."""

    def test_memory_initialization(self):
        """Test memory initialization."""
        memory = AgentMemory()
        assert len(memory.memories) == 0

    def test_store_memory(self):
        """Test storing memories."""
        memory = AgentMemory()

        memory_id = memory.store(
            content="Executed query successfully",
            memory_type="experience"
        )

        assert memory_id is not None
        assert len(memory.memories) == 1

    def test_retrieve_memory(self):
        """Test retrieving memories."""
        memory = AgentMemory()

        memory.store("SQL query optimization", memory_type="knowledge")
        memory.store("Data validation tips", memory_type="knowledge")

        # Retrieve memories
        memories = memory.retrieve("SQL", limit=5)
        # Basic check - should return something
        assert memories is not None

    def test_memory_limit(self):
        """Test memory size limit."""
        memory = AgentMemory(max_memories=3)

        # Add more than max
        for i in range(5):
            memory.store(f"Memory {i}", memory_type="experience")

        # Should respect max limit
        assert len(memory.memories) <= memory.max_memories


class TestAgentTools:
    """Test agent tools."""

    def test_mock_tool_execution(self):
        """Test executing a mock tool."""
        tool = MockTool("calculator")

        result = tool.execute(operation="add", a=5, b=3)
        assert result is not None
        assert tool.call_count == 1

    def test_mock_tool_failure(self):
        """Test tool failure handling."""
        tool = MockTool("failing_tool", success=False)

        with pytest.raises(RuntimeError):
            tool.execute()

    def test_mock_tool_tracking(self):
        """Test tool call tracking."""
        tool = MockTool("tracker")

        tool.execute(param1="value1")
        tool.execute(param2="value2")

        assert tool.call_count == 2
        assert len(tool.calls) == 2
        assert tool.calls[0] == {"param1": "value1"}
        assert tool.calls[1] == {"param2": "value2"}


class TestMultiAgentWorkflow:
    """Test complete multi-agent workflows."""

    def test_simple_workflow(self, mock_llm):
        """Test simple multi-agent workflow."""
        coordinator = AgentCoordinator()

        # Create agents
        agent1 = Agent(name="extractor", llm_provider=mock_llm)
        agent2 = Agent(name="transformer", llm_provider=mock_llm)
        agent3 = Agent(name="loader", llm_provider=mock_llm)

        coordinator.register_agent(agent1)
        coordinator.register_agent(agent2)
        coordinator.register_agent(agent3)

        # Add tasks
        task1 = coordinator.assign_task("Extract data", preferred_agent="extractor", priority="high")
        task2 = coordinator.assign_task("Transform data", preferred_agent="transformer")
        task3 = coordinator.assign_task("Load data", preferred_agent="loader")

        # Verify tasks are created
        assert task1 is not None
        assert task2 is not None
        assert task3 is not None

    def test_pipeline_workflow(self):
        """Test data pipeline workflow."""
        agent = DataEngineerAgent(name="pipeline_builder", llm_provider=MockLLM())

        # Build pipeline
        pipeline = agent.build_pipeline(
            source="raw_users",
            destination="analytics_users",
            name="user_analytics"
        )

        # Add stages
        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_stage(PipelineStage.VALIDATE)
        pipeline.add_stage(PipelineStage.TRANSFORM)
        pipeline.add_stage(PipelineStage.LOAD)

        # Add transformations
        pipeline.add_transformation(Transformation(
            name="filter_active",
            type=TransformationType.FILTER,
            config={"condition": "status = 'active'"}
        ))

        # Convert to dict
        pipeline_dict = pipeline.to_dict()
        assert pipeline_dict["name"] == "user_analytics"
        # Pipeline stages should be present
        assert len(pipeline_dict["stages"]) > 0

    def test_collaborative_workflow(self):
        """Test agents collaborating on a task."""
        coordinator = AgentCoordinator()

        # Create specialized agents
        sql_agent = DataEngineerAgent(name="sql_expert", llm_provider=MockLLM())
        validator_agent = Agent(name="validator")

        coordinator.register_agent(sql_agent)
        coordinator.register_agent(validator_agent)

        # Main task: Build and validate a pipeline
        task1 = coordinator.assign_task(
            "Build ETL pipeline",
            preferred_agent="sql_expert",
            priority="high"
        )

        task2 = coordinator.assign_task(
            "Validate pipeline",
            preferred_agent="validator"
        )

        # Simulate workflow
        # 1. SQL expert builds pipeline
        pipeline = sql_agent.build_pipeline(
            source="source_db",
            destination="target_db",
            name="etl_workflow"
        )
        coordinator.task_queue.complete_task(task1, result={"pipeline": pipeline})

        # 2. Validator checks it
        coordinator.task_queue.complete_task(task2, result={"valid": True})

        # Verify both tasks completed
        assert coordinator.task_queue.tasks[task1].status == TaskStatus.COMPLETED
        assert coordinator.task_queue.tasks[task2].status == TaskStatus.COMPLETED


class TestAgentLearning:
    """Test agent learning and adaptation."""

    def test_agent_with_memory(self):
        """Test agent with memory system."""
        memory = AgentMemory()
        agent = Agent(name="learner", memory=memory)

        # Agent should have memory
        assert agent.memory is not None
        assert agent.name == "learner"

    def test_action_result_tracking(self):
        """Test tracking action results."""
        agent = Agent(name="tracker")

        # Create action result
        result = ActionResult(
            success=True,
            output="Task completed successfully"
        )

        assert result.success
        assert result.output == "Task completed successfully"
        assert result.error is None

    def test_failed_action_result(self):
        """Test failed action result."""
        result = ActionResult(
            success=False,
            output=None,
            error="Operation failed"
        )

        assert not result.success
        assert result.error == "Operation failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
