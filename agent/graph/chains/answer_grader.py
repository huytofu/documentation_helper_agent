from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.answer_grader import llm
from agent.graph.utils.timeout import timeout
import json

class GradeAnswer(BaseModel):
    binary_score: bool = Field(
        description="Answer addresses the query, 'true' or 'false'"
    )

def parse_answer(text: str) -> GradeAnswer:
    try:
        # Try to parse as JSON first
        data = json.loads(text)
        return GradeAnswer(**data)
    except json.JSONDecodeError:
        # If not JSON, try to parse yes/no response
        text = text.strip().lower()
        if text == "true":
            return GradeAnswer(binary_score=True)
        elif text == "false":
            return GradeAnswer(binary_score=False)
        else:
            # Default to False if we can't parse
            return GradeAnswer(binary_score=False)

system = """You are a grader assessing whether an answer addresses or resolves the user's query.
    You must choose between:
    - 'true' means that the answer addresses or resolves the query.
    - 'false' means that the answer does not address or resolve the query.

    (IMPORTANT!) Your answer must be either 'true' or 'false' only!
    You MUST output your response in the following JSON format:
    {{
        "binary_score": true/false
    }}
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

# Create the chain with parsing
answer_grader: RunnableSequence = answer_prompt | llm | parse_answer
answer_grader.with_fallbacks(
    [answer_grader]
)
