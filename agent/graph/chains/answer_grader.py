from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.grader import llm

class GradeAnswer(BaseModel):

    binary_score: bool = Field(
        description="Answer addresses the query, 'yes' or 'no'"
    )

structured_llm_grader = llm.with_structured_output(GradeAnswer)

system = """You are a grader assessing whether an answer addresses / resolves a query \n 
     Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the query."""
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User query: \n\n {query} \n\n LLM generation: {generation}"),
    ]
)

answer_grader: RunnableSequence = answer_prompt | structured_llm_grader
answer_grader.with_fallbacks(
    [answer_grader]
)
