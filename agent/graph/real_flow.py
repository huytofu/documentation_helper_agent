from langgraph.graph import END, StateGraph
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer, grade_answer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations, grade_hallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, REGENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.state import GraphState, cleanup_resources
from langchain_core.messages import AIMessage
from agent.graph.consts import GENERATE, REGENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.nodes import generate, regenerate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize, pre_human_in_loop, post_human_in_loop
from agent.graph.state import GraphState, InputGraphState, OutputGraphState
from concurrent.futures import TimeoutError
import logging
import os
import time
import asyncio
from typing import Dict, Any
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger("graph.real_flow")

# Global lock for state mutations
state_lock = Lock()

@dataclass
class FlowState:
    """Thread-safe state container for flow execution."""
    iteration_count: int = 0
    retry_count: int = 0
    current_node: str = "INITIALIZE"
    _lock: Lock = field(default_factory=Lock)

    def increment_iteration(self) -> bool:
        """Atomically increment iteration count and check limit."""
        with self._lock:
            self.iteration_count += 1
            return self.iteration_count < 5  # MAX_ITERATIONS

    def increment_retry(self) -> bool:
        """Atomically increment retry count and check limit."""
        with self._lock:
            self.retry_count += 1
            return self.retry_count < 2  # MAX_RETRIES

    def set_node(self, node: str) -> None:
        """Atomically set current node."""
        with self._lock:
            self.current_node = node

# Global flow state
flow_state = FlowState()

def validate_state(state: GraphState) -> bool:
    """Validate that all required fields are present and valid in the state.
    
    Args:
        state: The state to validate
        
    Returns:
        bool: True if state is valid, False otherwise
    """
    # Define required fields and their validation rules
    required_fields = {
        "query": {
            "type": str,
            "min_length": 1,
            "max_length": 1000,
            "validate": lambda x: x.strip() != ""
        },
        "documents": {
            "type": list,
            "min_length": 0,
            "validate": lambda x: all(isinstance(doc, str) and len(doc.strip()) > 0 for doc in x)
        },
        # "current_node": {
        #     "type": str,
        #     "allowed_values": ["INITIALIZE", "DECIDE_LANGUAGE", "DECIDE_VECTORSTORE", 
        #                       "RETRIEVE", "GRADE_DOCUMENTS", "GENERATE", "WEBSEARCH", 
        #                       "HUMAN_IN_LOOP", "PRE_HUMAN_IN_LOOP", "POST_HUMAN_IN_LOOP"],
        #     "validate": lambda x: x in ["INITIALIZE", "DECIDE_LANGUAGE", "DECIDE_VECTORSTORE", 
        #                               "RETRIEVE", "GRADE_DOCUMENTS", "GENERATE", "WEBSEARCH", 
        #                               "HUMAN_IN_LOOP", "PRE_HUMAN_IN_LOOP", "POST_HUMAN_IN_LOOP"]
        # },
        "language": {
            "type": str,
            "allowed_values": ["python", "javascript", ""],
            "validate": lambda x: x in ["python", "javascript", ""]
        },
    }

    # Check each required field
    for field, rules in required_fields.items():
        # Check presence
        if field not in state:
            logger.error(f"Missing required field: {field}")
            return False
            
        value = state[field]
        
        # Check type
        if not isinstance(value, rules["type"]):
            logger.error(f"Invalid type for {field}: expected {rules['type']}, got {type(value)}")
            return False
            
        # Check length constraints if specified
        if "min_length" in rules and len(value) < rules["min_length"]:
            logger.error(f"Field {field} length {len(value)} is less than minimum {rules['min_length']}")
            return False
            
        if "max_length" in rules and len(value) > rules["max_length"]:
            logger.error(f"Field {field} length {len(value)} exceeds maximum {rules['max_length']}")
            return False
            
        # Check numeric constraints if specified
        if "min_value" in rules and value < rules["min_value"]:
            logger.error(f"Field {field} value {value} is less than minimum {rules['min_value']}")
            return False
            
        if "max_value" in rules and value > rules["max_value"]:
            logger.error(f"Field {field} value {value} exceeds maximum {rules['max_value']}")
            return False
            
        # Run custom validation if specified
        if "validate" in rules and not rules["validate"](value):
            logger.error(f"Custom validation failed for field: {field}")
            return False
            
    return True

def check_iteration_limit(state: GraphState) -> bool:
    """Check if the flow has exceeded maximum iterations."""
    if not flow_state.increment_iteration():
        logger.error("Flow exceeded maximum iterations (5)")
        return False
    return True

def get_last_ai_message_content(messages):
    # Reverse through messages to find the last AI message
    for message in reversed(messages):
        if message.type == "ai" or isinstance(message, AIMessage):  # Assuming AI messages have type "ai"
            return message.content
    return ""

def grade_generation_grounded_in_documents_and_query(state: GraphState) -> str:
    """Grade generation for hallucinations and query relevance.
    
    Args:
        state: Current graph state
        
    Returns:
        str: Next node to execute
    """
    logger.info("---CHECK HALLUCINATIONS---")
    
    # Validate state
    if not validate_state(state):
        cleanup_resources(state)
        return "end_misery"
        
    # Check iteration limit
    if not check_iteration_limit(state):
        cleanup_resources(state)
        return "end_misery"
    
    query = state.get("query", "")
    documents = state.get("documents", [])
    generation = state.get("generation", "")
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
            return "end_misery"
        except Exception as e:
            logger.error(f"Error during answer grading: {str(e)}")
            return "end_misery"
        
        if score and score.binary_score:
            logger.info("---DECISION: GENERATION ADDRESSES QUERY---")
            return "useful"
        else:
            logger.info("---DECISION: GENERATION DOES NOT ADDRESS QUERY, RE-TRY---")
            return "not useful"
    else:
        logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        retry_count = state.get("retry_count", 0)
        if retry_count == 0:
            return "not supported"
        elif retry_count < 2:
            return "need search web"
        logger.info("---DECISION: TOO MANY RETRIES, I AM GONNA END THIS MISERY---")
        cleanup_resources(state)
        return "end_misery"

def route_query(state: GraphState) -> str:
    logger.info("---ROUTE QUERY---")
    query = state.get("query", "")
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
workflow.add_node(REGENERATE, regenerate)
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