from typing import List, Optional, Dict, Any
from copilotkit import CopilotKitState


class GraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        framework: framework (vectorstore name)
        language: coding language
        generation: LLM generation
        web_search: whether to add search
        retry_count: number of retries
        documents: list of documents
    """

    query: str
    framework: str = ""
    language: str = ""
    generation: Optional[str] = None
    final_generation: Optional[str] = None
    comments: List[str] = []
    retry_count: int = 0
    documents: List[str] = []
    messages: List[Dict[str, Any]] = []
    copilotkit: Dict[str, Any] = {}
    current_node: str = ""
