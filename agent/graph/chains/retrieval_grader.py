from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.retrieval_grader import llm
from agent.graph.utils.timeout import timeout
from langchain_core.output_parsers import PydanticOutputParser


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the query, 'yes' or 'no'"
    )


# Create a PydanticOutputParser instead of using with_structured_output
parser = PydanticOutputParser(pydantic_object=GradeDocuments)

system = """You are a grader assessing relevance of a retrieved document to a user query. \n 
    If the document contains keyword(s) or semantic meaning related to the query, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the query.
    
    {format_instructions}"""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Retrieved document: \n\n {document} \n\n User query: {query}"),
    ]
)

# Use the traditional approach
retrieval_grader = grade_prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser

@timeout(10)  # 10 second timeout for document grading
def grade_single_document(query: str, document: str) -> GradeDocuments:
    """Grade a single document with timeout"""
    return retrieval_grader.invoke({"query": query, "document": document})
