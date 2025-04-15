from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableSequence
from agent.graph.models.sentiment_grader import llm
import json

class GradeSentiment(BaseModel):
    binary_score: bool = Field(
        description="Comments are positive, 'true' or 'false'"
    )

def parse_sentiment(text: str) -> GradeSentiment:
    try:
        # Try to parse as JSON first
        data = json.loads(text)
        return GradeSentiment(**data)
    except json.JSONDecodeError:
        # If not JSON, try to parse yes/no response
        text = text.strip().lower()
        if text == "true":
            return GradeSentiment(binary_score=True)
        elif text == "false":
            return GradeSentiment(binary_score=False)
        else:
            # Default to False if we can't parse
            return GradeSentiment(binary_score=False)

system = """You are a grader assessing whether comments are positive or negative \n 
    You must choose between:
    - 'true' means that the comments are positive.
    - 'false' means that the comments are negative.

    (IMPORTANT!) Your answer must be either 'true' or 'false' only!
    You MUST output your response in the following JSON format:
    {{
        "binary_score": true/false
    }}
    """
sentiment_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Comments: \n\n {comments}"),
    ]
)

# Create the chain with parsing
sentiment_grader: RunnableSequence = sentiment_prompt | llm | parse_sentiment
sentiment_grader.with_fallbacks(
    [sentiment_grader]
)
