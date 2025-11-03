"""
LangGraph Integration

Integrates NeuroLake agents with LangGraph for advanced workflows.
"""

import logging
from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AgentGraphState(TypedDict):
    """State for agent graph."""
    task: str
    observations: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    result: Optional[Any]
    iteration: int
    max_iterations: int
    error: Optional[str]


class LangGraphAgent:
    """
    Agent that uses LangGraph for state management.

    Example:
        agent = LangGraphAgent(
            name="analyst",
            description="Data analyst agent"
        )

        # Build graph
        graph = agent.build_graph()

        # Execute
        result = agent.execute_graph("Analyze sales data")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        llm_provider: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        max_iterations: int = 10
    ):
        """
        Initialize LangGraph agent.

        Args:
            name: Agent name
            description: Agent description
            llm_provider: LLM provider
            tools: Available tools
            max_iterations: Maximum iterations
        """
        self.name = name
        self.description = description
        self.llm = llm_provider
        self.tools = tools or []
        self.max_iterations = max_iterations

    def build_graph(self) -> Any:
        """
        Build LangGraph workflow.

        Returns:
            Compiled graph
        """
        try:
            from langgraph.graph import StateGraph, END

            # Create graph
            workflow = StateGraph(AgentGraphState)

            # Add nodes
            workflow.add_node("perceive", self._perceive_node)
            workflow.add_node("reason", self._reason_node)
            workflow.add_node("act", self._act_node)
            workflow.add_node("learn", self._learn_node)

            # Add edges
            workflow.set_entry_point("perceive")
            workflow.add_edge("perceive", "reason")
            workflow.add_conditional_edges(
                "reason",
                self._should_continue,
                {
                    "continue": "act",
                    "end": END
                }
            )
            workflow.add_edge("act", "learn")
            workflow.add_edge("learn", "perceive")

            # Compile
            return workflow.compile()

        except ImportError:
            logger.warning("LangGraph not installed")
            return None

    def execute_graph(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute task using graph.

        Args:
            task: Task to execute
            context: Optional context

        Returns:
            Task result
        """
        graph = self.build_graph()
        if not graph:
            raise RuntimeError("Failed to build graph")

        # Initialize state
        initial_state = AgentGraphState(
            task=task,
            observations=[],
            actions=[],
            result=None,
            iteration=0,
            max_iterations=self.max_iterations,
            error=None
        )

        # Run graph
        final_state = graph.invoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        return final_state.get("result")

    def _perceive_node(self, state: AgentGraphState) -> AgentGraphState:
        """Perceive node - gather observations."""
        observations = []

        # Add task observation
        observations.append({
            "type": "task",
            "data": state["task"]
        })

        # Add iteration info
        observations.append({
            "type": "iteration",
            "data": state["iteration"]
        })

        # Add previous actions if any
        if state["actions"]:
            observations.append({
                "type": "previous_actions",
                "data": state["actions"][-3:]
            })

        state["observations"] = observations
        return state

    def _reason_node(self, state: AgentGraphState) -> AgentGraphState:
        """Reason node - decide what to do."""
        if state["iteration"] >= state["max_iterations"]:
            return state

        if not self.llm:
            # Simple reasoning
            if self.tools:
                state["actions"].append({
                    "name": self.tools[0].name,
                    "parameters": {"query": state["task"]}
                })
            return state

        # LLM-based reasoning
        prompt = self._build_reasoning_prompt(state)
        response = self.llm.generate(prompt)

        # Parse action
        action = self._parse_action_from_response(response.text)
        if action:
            state["actions"].append(action)

        return state

    def _act_node(self, state: AgentGraphState) -> AgentGraphState:
        """Act node - execute action."""
        if not state["actions"]:
            return state

        last_action = state["actions"][-1]

        # Execute action
        tool_name = last_action.get("name")
        tool = next((t for t in self.tools if t.name == tool_name), None)

        if tool:
            try:
                result = tool.execute(**last_action.get("parameters", {}))
                state["result"] = result
            except Exception as e:
                state["error"] = str(e)
        else:
            state["error"] = f"Tool {tool_name} not found"

        return state

    def _learn_node(self, state: AgentGraphState) -> AgentGraphState:
        """Learn node - update from experience."""
        state["iteration"] += 1
        return state

    def _should_continue(self, state: AgentGraphState) -> str:
        """Decide whether to continue or end."""
        # Stop if error
        if state.get("error"):
            return "end"

        # Stop if max iterations
        if state["iteration"] >= state["max_iterations"]:
            return "end"

        # Stop if result obtained
        if state.get("result"):
            return "end"

        # Continue if no action decided
        if not state["actions"]:
            return "end"

        return "continue"

    def _build_reasoning_prompt(self, state: AgentGraphState) -> str:
        """Build prompt for reasoning."""
        prompt = f"""You are {self.name}, {self.description}.

Task: {state['task']}

Iteration: {state['iteration']}/{state['max_iterations']}

Available Tools:
"""
        for tool in self.tools:
            prompt += f"- {tool.name}: {tool.description}\n"

        prompt += """
What action should you take?
Respond in JSON format:
{
  "name": "<tool_name>",
  "parameters": {"param": "value"}
}

Or {"name": "complete"} if done.
"""
        return prompt

    def _parse_action_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse action from LLM response."""
        import json
        import re

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None

            action = json.loads(json_match.group())
            if action.get("name") == "complete":
                return None

            return action

        except (json.JSONDecodeError, KeyError):
            return None


@dataclass
class GraphNode:
    """A node in the agent graph."""
    name: str
    function: Any
    description: str = ""


@dataclass
class GraphEdge:
    """An edge in the agent graph."""
    from_node: str
    to_node: str
    condition: Optional[Any] = None


class AgentGraphBuilder:
    """
    Builder for creating custom agent graphs.

    Example:
        builder = AgentGraphBuilder()
        builder.add_node("start", start_func)
        builder.add_node("process", process_func)
        builder.add_edge("start", "process")
        graph = builder.build()
    """

    def __init__(self):
        """Initialize graph builder."""
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.entry_point: Optional[str] = None

    def add_node(
        self,
        name: str,
        function: Any,
        description: str = ""
    ):
        """
        Add a node to the graph.

        Args:
            name: Node name
            function: Node function
            description: Node description
        """
        self.nodes[name] = GraphNode(
            name=name,
            function=function,
            description=description
        )

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Any] = None
    ):
        """
        Add an edge between nodes.

        Args:
            from_node: Source node
            to_node: Target node
            condition: Optional condition function
        """
        self.edges.append(GraphEdge(
            from_node=from_node,
            to_node=to_node,
            condition=condition
        ))

    def set_entry_point(self, node_name: str):
        """
        Set the entry point node.

        Args:
            node_name: Entry node name
        """
        self.entry_point = node_name

    def build(self) -> Optional[Any]:
        """
        Build the graph.

        Returns:
            Compiled graph or None if LangGraph not available
        """
        try:
            from langgraph.graph import StateGraph, END

            if not self.entry_point:
                raise ValueError("No entry point set")

            # Create graph
            workflow = StateGraph(dict)

            # Add nodes
            for node in self.nodes.values():
                workflow.add_node(node.name, node.function)

            # Set entry point
            workflow.set_entry_point(self.entry_point)

            # Add edges
            for edge in self.edges:
                if edge.condition:
                    workflow.add_conditional_edges(
                        edge.from_node,
                        edge.condition,
                        {edge.to_node: edge.to_node}
                    )
                else:
                    workflow.add_edge(edge.from_node, edge.to_node)

            return workflow.compile()

        except ImportError:
            logger.warning("LangGraph not installed")
            return None


__all__ = [
    "LangGraphAgent",
    "AgentGraphState",
    "AgentGraphBuilder",
    "GraphNode",
    "GraphEdge",
]
