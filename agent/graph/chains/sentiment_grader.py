from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.grader import llm

class GradeSentiment(BaseModel):

    binary_score: bool = Field(
        description="Comments are positive, 'yes' or 'no'"
    )

structured_llm_grader = llm.with_structured_output(GradeSentiment)

system = """You are a grader assessing whether comments are positive or negative \n 
    You must choose between:
    - 'yes' means that the comments are positive.
    - 'no' means that the comments are negative.

    (IMPORTANT!) Your answer must be either 'yes' or 'no' only!
    """
sentiment_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Comments: \n\n {comments}"),
    ]
)

sentiment_grader: RunnableSequence = sentiment_prompt | structured_llm_grader
sentiment_grader.with_fallbacks(
    [sentiment_grader]
)
