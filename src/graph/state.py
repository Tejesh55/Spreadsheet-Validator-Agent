"""
Defines the Agent State Schema for LangGraph.
"""

from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    State shared across the graph execution.
    """
    messages: List[BaseMessage]
    file_path: Optional[str]
    validation_errors: Optional[str]
    output_files: Optional[dict]