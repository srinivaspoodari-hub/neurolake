"""
Agent Base Class

Implements the perceive-reason-act-learn cycle for autonomous agents.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    ACTING = "acting"
    LEARNING = "learning"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class Observation:
    """An observation from the environment."""
    timestamp: datetime
    type: str
    data: Any
    source: str = "environment"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """An action to be executed."""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tool: Optional[str] = None
    reasoning: str = ""
    confidence: float = 1.0


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent:
    """
    Autonomous agent with perceive-reason-act-learn cycle.

    Example:
        agent = Agent(
            name="analyst",
            description="Data analysis agent",
            llm_provider=llm
        )

        result = agent.execute("Analyze sales trends")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        llm_provider: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
        max_iterations: int = 10
    ):
        """
        Initialize agent.

        Args:
            name: Agent name
            description: Agent description
            llm_provider: LLM provider for reasoning
            tools: Available tools
            memory: Agent memory
            max_iterations: Maximum reasoning iterations
        """
        self.name = name
        self.description = description
        self.llm = llm_provider
        self.tools = tools or []
        self.memory = memory
        self.max_iterations = max_iterations

        self.state = AgentState.IDLE
        self.observations: List[Observation] = []
        self.actions_taken: List[Action] = []
        self.iteration = 0

        logger.info(f"Agent '{name}' initialized")

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a task using the perceive-reason-act-learn cycle.

        Args:
            task: Task description
            context: Optional context

        Returns:
            Task result
        """
        logger.info(f"Agent '{self.name}' executing task: {task}")

        self.iteration = 0
        result = None

        try:
            while self.iteration < self.max_iterations:
                self.iteration += 1

                # Perceive
                observations = self.perceive(task, context)

                # Reason
                action = self.reason(task, observations, context)

                if action is None:
                    # Task complete
                    break

                # Act
                action_result = self.act(action)

                # Learn from the result
                self.learn(action, action_result)

                if action_result.success:
                    result = action_result.output

                    # Check if task is complete
                    if self._is_task_complete(task, result):
                        break

            # Final learning
            self.learn_episode(task, result)

            return result

        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            self.state = AgentState.ERROR
            raise

        finally:
            self.state = AgentState.IDLE

    def perceive(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Observation]:
        """
        Perceive the environment and gather observations.

        Args:
            task: Current task
            context: Optional context

        Returns:
            List of observations
        """
        self.state = AgentState.PERCEIVING
        observations = []

        # Observe task
        observations.append(Observation(
            timestamp=datetime.now(),
            type="task",
            data=task,
            source="user"
        ))

        # Observe context
        if context:
            observations.append(Observation(
                timestamp=datetime.now(),
                type="context",
                data=context,
                source="environment"
            ))

        # Observe memory
        if self.memory:
            relevant_memories = self.memory.retrieve(task, limit=5)
            if relevant_memories:
                observations.append(Observation(
                    timestamp=datetime.now(),
                    type="memory",
                    data=relevant_memories,
                    source="memory"
                ))

        # Observe previous actions
        if self.actions_taken:
            observations.append(Observation(
                timestamp=datetime.now(),
                type="previous_actions",
                data=self.actions_taken[-3:],  # Last 3 actions
                source="self"
            ))

        self.observations.extend(observations)
        return observations

    def reason(
        self,
        task: str,
        observations: List[Observation],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Action]:
        """
        Reason about what action to take using LLM.

        Args:
            task: Current task
            observations: Current observations
            context: Optional context

        Returns:
            Next action to take, or None if complete
        """
        self.state = AgentState.REASONING

        if not self.llm:
            # No LLM - use simple rule-based reasoning
            return self._simple_reason(task, observations)

        # Construct reasoning prompt
        prompt = self._construct_reasoning_prompt(task, observations, context)

        # Get LLM response
        response = self.llm.generate(prompt, temperature=0.7)

        # Parse action from response
        action = self._parse_action(response.text)

        return action

    def act(self, action: Action) -> ActionResult:
        """
        Execute an action.

        Args:
            action: Action to execute

        Returns:
            Action result
        """
        self.state = AgentState.ACTING

        logger.info(f"Agent '{self.name}' acting: {action.name}")

        try:
            # Find and execute tool
            tool = self._find_tool(action.tool or action.name)

            if tool:
                output = tool.execute(**action.parameters)
                result = ActionResult(
                    success=True,
                    output=output
                )
            else:
                result = ActionResult(
                    success=False,
                    output=None,
                    error=f"Tool '{action.tool or action.name}' not found"
                )

            self.actions_taken.append(action)
            return result

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return ActionResult(
                success=False,
                output=None,
                error=str(e)
            )

    def learn(self, action: Action, result: ActionResult):
        """
        Learn from action result (short-term learning).

        Args:
            action: Action that was taken
            result: Result of the action
        """
        self.state = AgentState.LEARNING

        if not self.memory:
            return

        # Store experience in memory
        experience = {
            "action": action.name,
            "parameters": action.parameters,
            "success": result.success,
            "output": str(result.output)[:200] if result.output else None,
            "error": result.error,
            "timestamp": datetime.now().isoformat()
        }

        self.memory.store(
            content=f"Action: {action.name} - Success: {result.success}",
            metadata=experience,
            memory_type="experience"
        )

    def learn_episode(self, task: str, result: Any):
        """
        Learn from entire task episode (long-term learning).

        Args:
            task: Task that was completed
            result: Final result
        """
        if not self.memory:
            return

        # Store episode summary
        summary = {
            "task": task,
            "actions_count": len(self.actions_taken),
            "iterations": self.iteration,
            "success": result is not None,
            "timestamp": datetime.now().isoformat()
        }

        self.memory.store(
            content=f"Task: {task} - Actions: {len(self.actions_taken)}",
            metadata=summary,
            memory_type="episode"
        )

    def _find_tool(self, name: str) -> Optional[Any]:
        """Find a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def _is_task_complete(self, task: str, result: Any) -> bool:
        """Check if task is complete."""
        # Simple heuristic - can be enhanced
        return result is not None

    def _simple_reason(
        self,
        task: str,
        observations: List[Observation]
    ) -> Optional[Action]:
        """Simple rule-based reasoning without LLM."""
        # If we have tools, use the first available tool
        if self.tools:
            return Action(
                name=self.tools[0].name,
                parameters={"query": task}
            )
        return None

    def _construct_reasoning_prompt(
        self,
        task: str,
        observations: List[Observation],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Construct prompt for LLM reasoning."""
        prompt = f"""You are {self.name}, {self.description}.

Task: {task}

Observations:
"""
        for obs in observations:
            prompt += f"- {obs.type}: {obs.data}\n"

        prompt += f"""
Available Tools:
"""
        for tool in self.tools:
            prompt += f"- {tool.name}: {tool.description}\n"

        prompt += """
What action should you take next to complete the task?
Respond in JSON format:
{
  "action": "<tool_name>",
  "parameters": {"param": "value"},
  "reasoning": "why this action"
}

Or respond with {"action": "complete"} if the task is done.
"""
        return prompt

    def _parse_action(self, response: str) -> Optional[Action]:
        """Parse action from LLM response."""
        import json
        import re

        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            if data.get("action") == "complete":
                return None

            return Action(
                name=data["action"],
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", ""),
                tool=data.get("action")
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse action: {e}")
            return None


__all__ = ["Agent", "AgentState", "Observation", "Action", "ActionResult"]
