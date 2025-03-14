from langgraph.graph import END, StateGraph
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.state import GraphState
from langchain_core.messages import AIMessage
from agent.graph.consts import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.nodes import generate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize, pre_human_in_loop, post_human_in_loop
from agent.graph.state import GraphState, InputGraphState, OutputGraphState

import logging

logger = logging.getLogger("graph.test_flow")

def get_last_ai_message_content(messages):
    # Reverse through messages to find the last AI message
    for message in reversed(messages):
        if message.type == "ai" or isinstance(message, AIMessage):  # Assuming AI messages have type "ai"
            return message.content
    return ""

def grade_generation_grounded_in_query(state: GraphState) -> str:
    logger.info("---GRADE GENERATION GROUNDED IN QUERY---")
    generation = get_last_ai_message_content(state["messages"])
    query = state["query"]
    score = {}

    answer_counter = 0
    while not hasattr(score, "binary_score") and answer_counter < 2:
        score: GradeAnswer = answer_grader.invoke({"query": query, "generation": generation})
        answer_counter += 1
    
    if score and score.binary_score:
        logger.info("---DECISION: GENERATION ADDRESSES QUERY---")
        return "useful"
    else:
        logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUERY, RE-TRY---")
        return "not useful"


def route_query(state: GraphState) -> str:
    logger.info("---ROUTE QUERY---")
    query = state["query"]
    source: RouteQuery = query_router.invoke({"query": query})
    if source.datasource in ["websearch", None]:
        logger.info("---ROUTE QUERY TO WEB SEARCH---")
        return WEBSEARCH
    else:
        language = state.get("language", "")
        if language in ["python", "javascript"]:
            logger.info("---ROUTE QUERY TO VECTORSTORE ROUTER---")
            return DECIDE_VECTORSTORE
        else:
            logger.info("---ROUTE QUERY TO WEB SEARCH---")
            return WEBSEARCH
        
def to_search_web_or_not(state: GraphState) -> str:
    logger.info("---TO SEARCH WEB OR NOT---")
    documents = state["documents"]
    if len(documents) > 0:
        return GENERATE
    else:
        return WEBSEARCH
    
def determine_user_sentiment(state: GraphState) -> str:
    logger.info("---DETERMINE USER SENTIMENT---")
    sentiment: GradeSentiment = sentiment_grader.invoke({"comments": state["comments"]})
    if sentiment and sentiment.binary_score:
        return "good"
    else:
        return "bad"
    
# Create the graph without executor parameter
workflow = StateGraph(GraphState, input=InputGraphState, output=OutputGraphState)

# Add the initialize node
workflow.add_node(INITIALIZE, initialize)
# Add other nodes
workflow.add_node(DECIDE_VECTORSTORE, decide_vectorstore)
workflow.add_node(RETRIEVE, retrieve)
workflow.add_node(GENERATE, generate)
workflow.add_node(WEBSEARCH, web_search)
workflow.add_node(HUMAN_IN_LOOP, human_in_loop)
workflow.add_node(PRE_HUMAN_IN_LOOP, pre_human_in_loop)
workflow.add_node(POST_HUMAN_IN_LOOP, post_human_in_loop)

# Set the entry point to initialize
workflow.set_entry_point(INITIALIZE)
workflow.add_conditional_edges(
    INITIALIZE,
    route_query,
    {
        WEBSEARCH: WEBSEARCH,
        DECIDE_VECTORSTORE: DECIDE_VECTORSTORE
    },
)

workflow.add_edge(DECIDE_VECTORSTORE, RETRIEVE)
workflow.add_conditional_edges(
    RETRIEVE,
    to_search_web_or_not,
    {
        WEBSEARCH: WEBSEARCH,
        GENERATE: GENERATE
    }
)
workflow.add_edge(WEBSEARCH, GENERATE)
workflow.add_conditional_edges(
    GENERATE,
    grade_generation_grounded_in_query,
    {
        "useful": POST_HUMAN_IN_LOOP,
        "not useful": PRE_HUMAN_IN_LOOP,
    },
)
workflow.add_edge(PRE_HUMAN_IN_LOOP, HUMAN_IN_LOOP)
workflow.add_conditional_edges(
    HUMAN_IN_LOOP,
    determine_user_sentiment,
    {
        "good": END,
        "bad": GENERATE,
    }
)
workflow.add_edge(POST_HUMAN_IN_LOOP, END)

# Compile the graph with streaming enabled
app = workflow.compile(streaming=True)