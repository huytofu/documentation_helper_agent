from typing import List, TypedDict


class GraphState(TypedDict):
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
    framework: str
    language: str
    generation: str
    comments: str
    retry_count: int
    documents: List[str]
