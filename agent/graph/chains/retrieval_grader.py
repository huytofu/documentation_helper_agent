from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.grader import llm


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the query, 'yes' or 'no'"
    )


structured_llm_grader = llm.with_structured_output(GradeDocuments)

system = """You are a grader assessing relevance of a retrieved document to a user query. \n 
    If the document contains keyword(s) or semantic meaning related to the query, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the query."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Retrieved document: \n\n {document} \n\n User query: {query}"),
    ]
)

retrieval_grader = grade_prompt | structured_llm_grader
