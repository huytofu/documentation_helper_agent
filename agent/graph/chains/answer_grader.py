from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.grader import llm
from agent.graph.utils.timeout import timeout

class GradeAnswer(BaseModel):

    binary_score: bool = Field(
        description="Answer addresses the query, 'yes' or 'no'"
    )

structured_llm_grader = llm.with_structured_output(GradeAnswer)

system = """You are a grader assessing whether an answer addresses or resolves the user's query.
    You must choose between:
    - 'yes' means that the answer addresses or resolves the query.
    - 'no' means that the answer does not address or resolve the query.

    (IMPORTANT!) Your answer must be either 'yes' or 'no' only!
    """
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User's query: \n {query}. \n\n Answer: \n {answer}"),
    ]
)

@timeout(15)  # 15 second timeout for answer grading
def grade_answer(query: str, answer: str) -> GradeAnswer:
    """Grade answer with timeout"""
    return answer_grader.invoke({"query": query, "answer": answer})

answer_grader: RunnableSequence = answer_prompt | structured_llm_grader
answer_grader.with_fallbacks(
    [answer_grader]
)
