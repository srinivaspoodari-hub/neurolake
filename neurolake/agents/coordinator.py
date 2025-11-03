"""
Multi-Agent Coordination and Task Queue

Coordinates multiple agents and manages task distribution.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from queue import PriorityQueue
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Compare tasks by priority."""
        return self.priority.value < other.priority.value


class TaskQueue:
    """
    Queue for managing agent tasks.

    Example:
        queue = TaskQueue()

        # Add tasks
        task_id = queue.add_task("Analyze sales data", priority="high")

        # Get next task
        task = queue.get_next_task()

        # Mark complete
        queue.complete_task(task_id, result={"trends": [...]})
    """

    def __init__(self):
        """Initialize task queue."""
        self.queue = PriorityQueue()
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []

    def add_task(
        self,
        description: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a task to the queue.

        Args:
            description: Task description
            priority: Task priority (low, normal, high, critical)
            metadata: Optional task metadata

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            description=description,
            priority=TaskPriority[priority.upper()],
            metadata=metadata or {}
        )

        self.tasks[task_id] = task
        self.queue.put((task.priority.value, task_id))

        logger.info(f"Added task: {task_id} - {description}")
        return task_id

    def get_next_task(self, agent_name: Optional[str] = None) -> Optional[Task]:
        """
        Get next task from queue.

        Args:
            agent_name: Optional agent name for assignment

        Returns:
            Next task or None
        """
        if self.queue.empty():
            return None

        _, task_id = self.queue.get()
        task = self.tasks.get(task_id)

        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = agent_name
            task.started_at = datetime.now()
            return task

        return self.get_next_task(agent_name)

    def complete_task(self, task_id: str, result: Any = None):
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            result: Task result
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self.completed_tasks.append(task)
            logger.info(f"Completed task: {task_id}")

    def fail_task(self, task_id: str, error: str):
        """
        Mark task as failed.

        Args:
            task_id: Task ID
            error: Error message
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = error
            logger.error(f"Failed task: {task_id} - {error}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks."""
        return self.completed_tasks

    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for status in TaskStatus:
            count = sum(1 for t in self.tasks.values() if t.status == status)
            status_counts[status.value] = count

        return {
            "total_tasks": len(self.tasks),
            "pending": self.queue.qsize(),
            "completed": len(self.completed_tasks),
            "by_status": status_counts
        }


class AgentCoordinator:
    """
    Coordinates multiple agents working together.

    Example:
        coordinator = AgentCoordinator()

        # Register agents
        coordinator.register_agent(analyst_agent)
        coordinator.register_agent(query_agent)

        # Assign task
        result = coordinator.assign_task(
            "Analyze sales trends",
            preferred_agent="analyst"
        )
    """

    def __init__(self):
        """Initialize agent coordinator."""
        self.agents: Dict[str, Any] = {}
        self.task_queue = TaskQueue()
        self.agent_assignments: Dict[str, List[str]] = {}  # agent -> [task_ids]

    def register_agent(self, agent: Any):
        """
        Register an agent.

        Args:
            agent: Agent to register
        """
        self.agents[agent.name] = agent
        self.agent_assignments[agent.name] = []
        logger.info(f"Registered agent: {agent.name}")

    def unregister_agent(self, agent_name: str):
        """
        Unregister an agent.

        Args:
            agent_name: Agent name
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            del self.agent_assignments[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")

    def assign_task(
        self,
        description: str,
        preferred_agent: Optional[str] = None,
        priority: str = "normal"
    ) -> str:
        """
        Assign a task to an agent.

        Args:
            description: Task description
            preferred_agent: Preferred agent name
            priority: Task priority

        Returns:
            Task ID
        """
        # Add to queue
        task_id = self.task_queue.add_task(description, priority)

        # Assign to agent
        if preferred_agent and preferred_agent in self.agents:
            agent = self.agents[preferred_agent]
        else:
            # Find least busy agent
            agent = self._find_available_agent()

        if agent:
            self.agent_assignments[agent.name].append(task_id)
            logger.info(f"Assigned task {task_id} to agent {agent.name}")
        else:
            logger.warning(f"No available agent for task {task_id}")

        return task_id

    def execute_task(self, task_id: str) -> Any:
        """
        Execute a task.

        Args:
            task_id: Task ID

        Returns:
            Task result
        """
        task = self.task_queue.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not task.assigned_to:
            raise ValueError(f"Task {task_id} not assigned")

        agent = self.agents.get(task.assigned_to)
        if not agent:
            raise ValueError(f"Agent {task.assigned_to} not found")

        try:
            # Execute task
            task.status = TaskStatus.IN_PROGRESS
            result = agent.execute(task.description, context=task.metadata)

            # Mark complete
            self.task_queue.complete_task(task_id, result)

            return result

        except Exception as e:
            # Mark failed
            self.task_queue.fail_task(task_id, str(e))
            raise

    def execute_all_pending(self) -> List[Dict[str, Any]]:
        """
        Execute all pending tasks.

        Returns:
            List of task results
        """
        results = []

        while True:
            task = self.task_queue.get_next_task()
            if not task:
                break

            try:
                # Find agent for task
                if task.assigned_to and task.assigned_to in self.agents:
                    agent = self.agents[task.assigned_to]
                else:
                    agent = self._find_available_agent()

                if not agent:
                    logger.warning(f"No available agent for task {task.id}")
                    continue

                # Execute
                task.status = TaskStatus.IN_PROGRESS
                result = agent.execute(task.description, context=task.metadata)

                # Complete
                self.task_queue.complete_task(task.id, result)

                results.append({
                    "task_id": task.id,
                    "agent": agent.name,
                    "result": result
                })

            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
                self.task_queue.fail_task(task.id, str(e))

                results.append({
                    "task_id": task.id,
                    "error": str(e)
                })

        return results

    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """
        Get agent status.

        Args:
            agent_name: Agent name

        Returns:
            Agent status
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")

        agent = self.agents[agent_name]
        tasks = self.agent_assignments.get(agent_name, [])

        completed = sum(
            1 for task_id in tasks
            if self.task_queue.get_task(task_id).status == TaskStatus.COMPLETED
        )

        return {
            "name": agent_name,
            "state": agent.state.value if hasattr(agent, 'state') else "unknown",
            "assigned_tasks": len(tasks),
            "completed_tasks": completed
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            "agents": len(self.agents),
            "queue": self.task_queue.get_statistics(),
            "agents_status": {
                name: self.get_agent_status(name)
                for name in self.agents.keys()
            }
        }

    def _find_available_agent(self) -> Optional[Any]:
        """Find least busy available agent."""
        if not self.agents:
            return None

        # Find agent with fewest assigned tasks
        min_tasks = float('inf')
        available_agent = None

        for agent_name, agent in self.agents.items():
            task_count = len(self.agent_assignments.get(agent_name, []))
            if task_count < min_tasks:
                min_tasks = task_count
                available_agent = agent

        return available_agent


__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskQueue",
    "AgentCoordinator",
]
