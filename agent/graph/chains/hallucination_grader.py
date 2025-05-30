from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.hallucinate_grader import llm
from agent.graph.utils.timeout import timeout
import json

class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: bool = Field(
        description="Generation is grounded in documents, 'true' or 'false'"
    )

def parse_hallucination(message) -> GradeHallucinations:
    # Extract content from AIMessage
    content = message.content if hasattr(message, 'content') else str(message)
    
    try:
        # Try to parse as JSON first
        data = json.loads(content)
        return GradeHallucinations(**data)
    except json.JSONDecodeError:
        # If not JSON, try to parse yes/no response
        content = content.strip().lower()
        if content == "true":
            return GradeHallucinations(binary_score=True)
        elif content == "false":
            return GradeHallucinations(binary_score=False)
        else:
            # Default to False if we can't parse
            return GradeHallucinations(binary_score=False)

system = """You are a grader assessing whether a generation is grounded in the provided documents.
    You must choose between:
    - 'true' means that the generation is grounded in the documents.
    - 'false' means that the generation is not grounded in the documents.

    (IMPORTANT!) Your answer must be either 'true' or 'false' only!
    You MUST output your response in the following JSON format:
    {{
        "binary_score": true/false
    }}
    """
hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Documents: \n {documents}. \n\n Generation: \n {generation}"),
    ]
)

@timeout(15)  # 15 second timeout for hallucination grading
def grade_hallucinations(documents: str, generation: str) -> GradeHallucinations:
    """Grade hallucinations with timeout"""
    documents = documents.strip()
    generation = generation.strip()
    if documents == "":
        return GradeHallucinations(binary_score=True)
    if generation == "":
        return GradeHallucinations(binary_score=False)
    return hallucination_grader.invoke({"documents": documents, "generation": generation})

# Create the chain with parsing
hallucination_grader: RunnableSequence = hallucination_prompt | llm | parse_hallucination
hallucination_grader.with_fallbacks(
    [hallucination_grader]
)