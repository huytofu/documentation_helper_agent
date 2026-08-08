from langgraph.graph import END, StateGraph
from langchain_core.documents import Document
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer, grade_answer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations, grade_hallucinations
from langchain_core.messages import AIMessage
from agent.graph.consts import (
    GENERATE,
    REGENERATE,
    GRADE_DOCUMENTS,
    RETRIEVE,
    WEBSEARCH,
    ROUTE_AND_FRAMEWORK,
    CHUB_EXPERT,
    CHUB_TOOLS,
    HUMAN_IN_LOOP,
    INITIALIZE,
    CLASSIFY_INTENT,
    CHITCHAT,
    PRE_HUMAN_IN_LOOP,
    POST_HUMAN_IN_LOOP,
    SUMMARIZE,
    IMMEDIATE_MESSAGE_ONE,
    IMMEDIATE_MESSAGE_TWO,
)
from agent.graph.nodes import (
    generate,
    regenerate,
    grade_documents,
    retrieve,
    route_and_framework,
    chub_expert,
    chub_tools,
    classify_intent,
    chitchat,
    web_search,
    human_in_loop,
    initialize,
    pre_human_in_loop,
    post_human_in_loop,
    summarize,
    immediate_message_one,
    immediate_message_two,
)
from agent.graph.state import GraphState, InputGraphState, OutputGraphState, cleanup_resources
from agent.graph.utils.flow_state import check_iteration_limit, reset_flow_state
from agent.graph.chains.chub_expert import MAX_CHUB_TOOL_ROUNDS
from concurrent.futures import TimeoutError
from threading import Lock
import logging
logger = logging.getLogger("graph.real_flow")

# Global lock for state mutations
state_lock = Lock()

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
            "validate": lambda x: all(isinstance(doc, Document) for doc in x)
        },
        "language": {
            "type": str,
            "allowed_values": ["python", "javascript", "others", "none"],
            "validate": lambda x: x in ["python", "javascript", "others", "none"]
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
            logger.error(f"Value: {value}")
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
    if not check_iteration_limit():
        cleanup_resources(state)
        return "end_misery"
    
    query = state.get("query", "")
    documents = state.get("documents", [])
    messages = state.get("messages", [])
    generation = get_last_ai_message_content(messages)
    score = {}

    hallucination_counter = 0
    while not hasattr(score, "binary_score") and hallucination_counter < 1:
        hallucination_counter += 1
        try:
            score: GradeHallucinations = grade_hallucinations(
                documents="\n\n".join([doc.page_content[:500] for doc in documents]),
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
        if retry_count < 1:
            return "need search web"
        logger.info("---DECISION: TOO MANY RETRIES, I AM GONNA END THIS MISERY---")
        cleanup_resources(state)
        return "end_misery"


def after_classify_intent(state: GraphState) -> str:
    """Branch after intent classification: chitchat vs programming pipeline."""
    logger.info("---AFTER CLASSIFY INTENT---")
    if state.get("intent") == "chitchat":
        logger.info("---ROUTE TO CHITCHAT---")
        return CHITCHAT
    logger.info("---ROUTE TO SUMMARIZE---")
    return SUMMARIZE


def after_route_and_framework(state: GraphState) -> str:
    """Branch after the merged router node (framework/language already on state)."""
    logger.info("---AFTER ROUTE AND FRAMEWORK---")
    datasource = state.get("datasource")
    if datasource == "vectorstore":
        logger.info("---ROUTE TO RETRIEVE---")
        return RETRIEVE
    if datasource == "direct":
        logger.info("---ROUTE TO GENERATE (direct)---")
        return GENERATE
    logger.info("---ROUTE TO WEB SEARCH---")
    return WEBSEARCH


def after_generate(state: GraphState) -> str:
    """Skip graders/HITL for direct answers; otherwise run existing grading."""
    if state.get("datasource") == "direct":
        logger.info("---DIRECT GENERATE: END (skip graders/HITL)---")
        reset_flow_state()
        return "direct_end"
    return grade_generation_grounded_in_documents_and_query(state)


def after_grade(state: GraphState) -> str:
    """After grading: generate, try chub enrich, or fall back to websearch."""
    logger.info("---AFTER GRADE---")
    documents = state.get("documents") or []
    if len(documents) > 0:
        return GENERATE
    if state.get("chub_enrich_attempted"):
        logger.info("---CHUB ALREADY ATTEMPTED; WEB SEARCH---")
        return WEBSEARCH
    logger.info("---ROUTE TO CHUB EXPERT---")
    return CHUB_EXPERT


def after_chub_expert(state: GraphState) -> str:
    """Continue tool loop, or finish to GENERATE / WEBSEARCH."""
    logger.info("---AFTER CHUB EXPERT---")
    msgs = state.get("chub_messages") or []
    last = msgs[-1] if msgs else None
    tool_calls = getattr(last, "tool_calls", None) if last is not None else None
    rounds = int(state.get("chub_tool_rounds") or 0)
    if tool_calls and rounds < MAX_CHUB_TOOL_ROUNDS:
        logger.info("---CHUB TOOLS (round %s)---", rounds + 1)
        return CHUB_TOOLS
    docs = state.get("documents") or []
    if docs:
        logger.info("---CHUB ENRICH PRODUCED DOCS; GENERATE---")
        return GENERATE
    logger.info("---CHUB ENRICH EMPTY; WEB SEARCH---")
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
workflow.add_node(IMMEDIATE_MESSAGE_ONE, immediate_message_one)
workflow.add_node(IMMEDIATE_MESSAGE_TWO, immediate_message_two)
workflow.add_node(CLASSIFY_INTENT, classify_intent)
workflow.add_node(CHITCHAT, chitchat)
workflow.add_node(ROUTE_AND_FRAMEWORK, route_and_framework)
workflow.add_node(RETRIEVE, retrieve)
workflow.add_node(GRADE_DOCUMENTS, grade_documents)
workflow.add_node(
    CHUB_EXPERT,
    chub_expert,
    destinations=(CHUB_EXPERT, GENERATE),
)
workflow.add_node(CHUB_TOOLS, chub_tools)
workflow.add_node(GENERATE, generate)
workflow.add_node(REGENERATE, regenerate)
workflow.add_node(WEBSEARCH, web_search)
workflow.add_node(SUMMARIZE, summarize)
workflow.add_node(HUMAN_IN_LOOP, human_in_loop)
workflow.add_node(PRE_HUMAN_IN_LOOP, pre_human_in_loop)
workflow.add_node(POST_HUMAN_IN_LOOP, post_human_in_loop)

# Set the entry point to initialize
workflow.set_entry_point(INITIALIZE)
workflow.add_edge(INITIALIZE, CLASSIFY_INTENT)
workflow.add_conditional_edges(
    CLASSIFY_INTENT,
    after_classify_intent,
    {
        CHITCHAT: CHITCHAT,
        SUMMARIZE: SUMMARIZE,
    },
)
workflow.add_edge(CHITCHAT, END)
workflow.add_edge(SUMMARIZE, ROUTE_AND_FRAMEWORK)
workflow.add_conditional_edges(
    ROUTE_AND_FRAMEWORK,
    after_route_and_framework,
    {
        WEBSEARCH: WEBSEARCH,
        RETRIEVE: RETRIEVE,
        GENERATE: GENERATE,
    },
)

workflow.add_edge(RETRIEVE, GRADE_DOCUMENTS)
workflow.add_conditional_edges(
    GRADE_DOCUMENTS,
    after_grade,
    {
        GENERATE: GENERATE,
        CHUB_EXPERT: CHUB_EXPERT,
        WEBSEARCH: WEBSEARCH,
    },
)
workflow.add_conditional_edges(
    CHUB_EXPERT,
    after_chub_expert,
    {
        CHUB_TOOLS: CHUB_TOOLS,
        GENERATE: GENERATE,
        WEBSEARCH: WEBSEARCH,
    },
)
workflow.add_edge(CHUB_TOOLS, CHUB_EXPERT)
workflow.add_edge(WEBSEARCH, GENERATE)
workflow.add_conditional_edges(
    GENERATE,
    after_generate,
    {
        "direct_end": END,
        "need search web": IMMEDIATE_MESSAGE_ONE,
        "end_misery": POST_HUMAN_IN_LOOP,
        "useful": POST_HUMAN_IN_LOOP,
        "not useful": PRE_HUMAN_IN_LOOP,
    },
)
workflow.add_edge(IMMEDIATE_MESSAGE_ONE, WEBSEARCH)
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
