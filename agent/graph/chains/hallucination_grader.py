from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.grader import llm

class GradeHallucinations(BaseModel):
    """Binary score for hallucination present in generation answer."""

    binary_score: bool = Field(
        description="Answer is grounded in retrieved facts, 'yes' or 'no'"
    )


structured_llm_grader = llm.with_structured_output(GradeHallucinations)

system = """You are a grader assessing whether an LLM generation is grounded in a set of retrieved facts. \n 
    You must choose between:
    - 'yes' means that the answer is grounded in the set of facts.
    - 'no' means that the answer is not grounded in the set of facts.

    (IMPORTANT!) Your answer must be either 'yes' or 'no' only!
    """
hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    ]
)

hallucination_grader: RunnableSequence = hallucination_prompt | structured_llm_grader
hallucination_grader.with_fallbacks(
    [hallucination_grader]
)