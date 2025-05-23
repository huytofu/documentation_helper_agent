from langgraph.graph import END, StateGraph
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, REGENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP, SUMMARIZE, IMMEDIATE_MESSAGE_ONE, IMMEDIATE_MESSAGE_TWO
from agent.graph.nodes import (
    generate, regenerate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize, pre_human_in_loop, post_human_in_loop, summarize, immediate_message_one, immediate_message_two
)
from agent.graph.state import GraphState, InputGraphState, OutputGraphState, cleanup_resources
import logging

logger = logging.getLogger("graph.test_flow")

def to_search_web_or_not(state: GraphState) -> str:
    logger.info("---TO SEARCH WEB OR NOT---")
    documents = state.get("documents", [])
    if len(documents) > 0:
        return GENERATE
    else:
        return WEBSEARCH
    
def determine_user_sentiment(state: GraphState) -> str:
    logger.info("---DETERMINE USER SENTIMENT---")
    try:
        sentiment: GradeSentiment = sentiment_grader.invoke({"comments": state.get("comments", "")})
        if sentiment and sentiment.binary_score:
            return "good"
        else:
            return "bad"
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {str(e)}")
        return "good"  # Default to good on error
    finally:
        # Always clean up resources before ending
        cleanup_resources(state)
    
def grade_generation_grounded_in_query(state: GraphState) -> str:
    logger.info("---GRADE GENERATION GROUNDED IN QUERY---")
    random_number = 0
    if random_number == 0:
        return "useful"
    else:
        return "not useful"
    
# Create the graph without executor parameter
workflow = StateGraph(GraphState, input=InputGraphState, output=OutputGraphState)

# Add the initialize node
workflow.add_node(INITIALIZE, initialize)
# Add other 
workflow.add_node(DECIDE_VECTORSTORE, decide_vectorstore)
workflow.add_node(RETRIEVE, retrieve)
workflow.add_node(GENERATE, generate)
workflow.add_node(REGENERATE, regenerate)
workflow.add_node(WEBSEARCH, web_search)
workflow.add_node(SUMMARIZE, summarize)
workflow.add_node(HUMAN_IN_LOOP, human_in_loop)
workflow.add_node(PRE_HUMAN_IN_LOOP, pre_human_in_loop)
workflow.add_node(POST_HUMAN_IN_LOOP, post_human_in_loop)
workflow.add_node(IMMEDIATE_MESSAGE_ONE, immediate_message_one)
workflow.add_node(IMMEDIATE_MESSAGE_TWO, immediate_message_two)

# Set the entry point to initialize
workflow.set_entry_point(INITIALIZE)
workflow.add_edge(INITIALIZE, SUMMARIZE)
workflow.add_edge(SUMMARIZE, DECIDE_VECTORSTORE)
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
        "bad": IMMEDIATE_MESSAGE_TWO,
    }
)
workflow.add_edge(IMMEDIATE_MESSAGE_TWO, REGENERATE)
workflow.add_edge(REGENERATE, POST_HUMAN_IN_LOOP)
workflow.add_edge(POST_HUMAN_IN_LOOP, END)

# Workflow is compiled in graph.py