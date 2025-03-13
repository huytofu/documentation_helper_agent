from typing import List, Optional, Dict, Any
from copilotkit import CopilotKitState


class InputGraphState(CopilotKitState):
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

    language: str = ""
    comments: str = ""
    # messages: List[Dict[str, Any]] = []
    # copilotkit: Dict[str, Any] = {}

class OutputGraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        current_node: current node
        generation: LLM generation
    """
    current_node: str = ""
    generation: Optional[str] = None

class GraphState(InputGraphState, OutputGraphState):
    query: str
    framework: str = ""
    retry_count: int = 0
    documents: List[str] = []
    

