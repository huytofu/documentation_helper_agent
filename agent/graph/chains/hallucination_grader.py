from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.grader import llm
from agent.graph.utils.timeout import timeout

class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: bool = Field(
        description="Generation is grounded in documents, 'yes' or 'no'"
    )


structured_llm_grader = llm.with_structured_output(GradeHallucinations)

system = """You are a grader assessing whether a generation is grounded in the provided documents.
    You must choose between:
    - 'yes' means that the generation is grounded in the documents.
    - 'no' means that the generation is not grounded in the documents.

    (IMPORTANT!) Your answer must be either 'yes' or 'no' only!
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
    return hallucination_grader.invoke({"documents": documents, "generation": generation})

hallucination_grader: RunnableSequence = hallucination_prompt | structured_llm_grader
hallucination_grader.with_fallbacks(
    [hallucination_grader]
)