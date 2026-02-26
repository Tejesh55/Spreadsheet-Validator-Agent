"""
Builds and compiles the LangGraph workflow.
"""

from langgraph.graph import StateGraph
from src.graph.state import AgentState
from src.agent.agent import build_agent
from langgraph.checkpoint.memory import InMemorySaver


def build_graph():
    agent = build_agent()

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)

    graph.set_entry_point("agent")
    graph.set_finish_point("agent")

    return graph.compile(checkpointer=InMemorySaver())