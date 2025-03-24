from langgraph.graph import END, StateGraph
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer, grade_answer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations, grade_hallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, REGENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.state import GraphState
from langchain_core.messages import AIMessage
from agent.graph.consts import GENERATE, REGENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.nodes import generate, regenerate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize, pre_human_in_loop, post_human_in_loop
from agent.graph.state import GraphState, InputGraphState, OutputGraphState
from concurrent.futures import TimeoutError
import logging
import os
import time

logger = logging.getLogger("graph.real_flow")

def validate_state(state: GraphState) -> bool:
    """Validate that all required fields are present in the state."""
    required_fields = ["query", "documents", "generation"]
    for field in required_fields:
        if field not in state:
            logger.error(f"Missing required state field: {field}")
            return False
    return True

def check_iteration_limit(state: GraphState) -> bool:
    """Check if the flow has exceeded maximum iterations."""
    MAX_ITERATIONS = 5
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    if state["iteration_count"] >= MAX_ITERATIONS:
        logger.error(f"Flow exceeded maximum iterations ({MAX_ITERATIONS})")
        return False
    return True

def cleanup_resources(state: GraphState) -> None:
    """Clean up any temporary resources."""
    if "temp_files" in state:
        for file in state["temp_files"]:
            try:
                os.remove(file)
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")

def get_last_ai_message_content(messages):
    # Reverse through messages to find the last AI message
    for message in reversed(messages):
        if message.type == "ai" or isinstance(message, AIMessage):  # Assuming AI messages have type "ai"
            return message.content
    return ""

def grade_generation_grounded_in_documents_and_query(state: GraphState) -> str:
    logger.info("---CHECK HALLUCINATIONS---")
    
    # Validate state
    if not validate_state(state):
        cleanup_resources(state)
        return "end_misery"
        
    # Check iteration limit
    if not check_iteration_limit(state):
        cleanup_resources(state)
        return "end_misery"
    
    query = state["query"]
    documents = state["documents"]
    generation = state["generation"]
    score = {}

    hallucination_counter = 0
    while not hasattr(score, "binary_score") and hallucination_counter < 1:
        hallucination_counter += 1
        try:
            score: GradeHallucinations = grade_hallucinations(
                documents="\n\n".join([doc.page_content for doc in documents]),
                generation=generation
            )
        except TimeoutError:
            logger.error("Hallucination grading timed out")
            cleanup_resources(state)
            return "end_misery"
        except Exception as e:
            logger.info(f"---ERROR: {e}---")
            logger.info("---RETRYING HALLUCINATION GRADING---")
            continue

    if score and score.binary_score:
        logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        logger.info("---GRADE GENERATION vs query---")
        
        try:
            score: GradeAnswer = grade_answer(query=query, answer=generation)
        except TimeoutError:
            logger.error("Answer grading timed out")
            cleanup_resources(state)
            return "end_misery"
        except Exception as e:
            logger.error(f"Error during answer grading: {str(e)}")
            cleanup_resources(state)
            return "end_misery"
        
        if score and score.binary_score:
            logger.info("---DECISION: GENERATION ADDRESSES QUERY---")
            return "useful"
        else:
            logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUERY, RE-TRY---")
            return "not useful"
    else:
        logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        if state["retry_count"] == 0:
            return "not supported"
        elif state["retry_count"] < 2:
            return "need search web"
        logger.info("---DECISION: TOO MANY RETRIES, I AM GONNA END THIS MISERY---")
        cleanup_resources(state)
        return "end_misery"

def grade_generation_grounded_in_query(state: GraphState) -> str:
    logger.info("---GRADE GENERATION GROUNDED IN QUERY---")
    generation = get_last_ai_message_content(state["messages"])
    # Rest of the function...

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
        # Clean up web search resources before generating
        cleanup_resources(state)
        return GENERATE
    else:
        # Clean up document resources before web search
        cleanup_resources(state)
        return WEBSEARCH
    
def determine_user_sentiment(state: GraphState) -> str:
    logger.info("---DETERMINE USER SENTIMENT---")
    try:
        sentiment: GradeSentiment = sentiment_grader.invoke({"comments": state["comments"]})
        if sentiment and sentiment.binary_score:
            return "good"
        else:
            return "bad"
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {str(e)}")
        cleanup_resources(state)
        return "good"  # Default to good on error
    finally:
        # Always clean up resources before ending
        cleanup_resources(state)

# Create the graph without executor parameter
workflow = StateGraph(GraphState, input=InputGraphState, output=OutputGraphState)

# Add the initialize node
workflow.add_node(INITIALIZE, initialize)
# Add other 
workflow.add_node(DECIDE_LANGUAGE, decide_language)
workflow.add_node(DECIDE_VECTORSTORE, decide_vectorstore)
workflow.add_node(RETRIEVE, retrieve)
workflow.add_node(GRADE_DOCUMENTS, grade_documents)
workflow.add_node(GENERATE, generate)
workflow.add_node(WEBSEARCH, web_search)
workflow.add_node(HUMAN_IN_LOOP, human_in_loop)
workflow.add_node(PRE_HUMAN_IN_LOOP, pre_human_in_loop)
workflow.add_node(POST_HUMAN_IN_LOOP, post_human_in_loop)

# Set the entry point to initialize
workflow.set_entry_point(INITIALIZE)
workflow.add_edge(INITIALIZE, DECIDE_LANGUAGE)
workflow.add_conditional_edges(
    DECIDE_LANGUAGE,
    route_query,
    {
        WEBSEARCH: WEBSEARCH,
        DECIDE_VECTORSTORE: DECIDE_VECTORSTORE
    },
)

workflow.add_edge(DECIDE_VECTORSTORE, RETRIEVE)
workflow.add_edge(RETRIEVE, GRADE_DOCUMENTS)
workflow.add_conditional_edges(
    GRADE_DOCUMENTS,
    to_search_web_or_not,
    {
        WEBSEARCH: WEBSEARCH,
        GENERATE: GENERATE
    }
)
workflow.add_edge(WEBSEARCH, GENERATE)
workflow.add_conditional_edges(
    GENERATE,
    grade_generation_grounded_in_documents_and_query,
    {
        "not supported": GENERATE,
        "need search web": WEBSEARCH,
        "end_misery": POST_HUMAN_IN_LOOP,
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
        "bad": REGENERATE,
    }
)
workflow.add_edge(REGENERATE, POST_HUMAN_IN_LOOP)
workflow.add_edge(POST_HUMAN_IN_LOOP, END)

# Workflow is compiled in graph.py