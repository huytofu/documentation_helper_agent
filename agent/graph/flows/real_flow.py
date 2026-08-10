from langgraph.graph import END, StateGraph
from langchain_core.documents import Document
from agent.graph.chains.answer_grader import GradeAnswer, grade_answer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import GradeHallucinations, grade_hallucinations
from langchain_core.messages import AIMessage
from agent.graph.consts import (
    GENERATE,
    REGENERATE,
    GRADE_DOCUMENTS,
    RETRIEVE,
    WEBSEARCH,
    ROUTE_AND_FRAMEWORK,
    ASK_CHUB_PERMISSION,
    CHUB_EXPERT,
    CHUB_TOOLS,
    HUMAN_IN_LOOP,
    INITIALIZE,
    CLASSIFY_INTENT,
    CHITCHAT,
    KB_META,
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
    ask_chub_permission,
    chub_expert,
    chub_tools,
    classify_intent,
    chitchat,
    kb_meta,
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
from agent.graph.utils.grade_routing import resolve_generation_grade_route
from agent.graph.chains.chub_expert import MAX_CHUB_TOOL_ROUNDS
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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
    """Grade generation for query relevance and (when docs exist) grounding.

    Runs answer grading always. When documents are present, also runs
    hallucination grading in parallel. Useful answers win even if ungrounded
    (general knowledge). Empty-doc / ungrounded + not useful triggers web search.
    
    Args:
        state: Current graph state
        
    Returns:
        str: Next node to execute
    """
    logger.info("---GRADE GENERATION (PARALLEL / EDGE CASES)---")
    
    # Validate state
    if not validate_state(state):
        cleanup_resources(state)
        return "end_misery"
        
    # Check iteration limit
    if not check_iteration_limit():
        cleanup_resources(state)
        return "end_misery"
    
    query = state.get("query", "")
    documents = state.get("documents", []) or []
    messages = state.get("messages", [])
    generation = get_last_ai_message_content(messages)
    has_documents = len(documents) > 0

    answer_score: GradeAnswer | None = None
    hallucination_score: GradeHallucinations | None = None

    try:
        if has_documents:
            logger.info("---CHECK HALLUCINATIONS + ANSWER (PARALLEL)---")
            docs_text = "\n\n".join([doc.page_content[:500] for doc in documents])
            with ThreadPoolExecutor(max_workers=2) as executor:
                hallucination_future = executor.submit(
                    grade_hallucinations,
                    documents=docs_text,
                    generation=generation,
                )
                answer_future = executor.submit(
                    grade_answer,
                    query=query,
                    answer=generation,
                )
                hallucination_score = hallucination_future.result()
                answer_score = answer_future.result()
        else:
            logger.info("---NO DOCUMENTS: ANSWER GRADING ONLY---")
            answer_score = grade_answer(query=query, answer=generation)
    except TimeoutError:
        logger.error("Grading timed out")
        cleanup_resources(state)
        return "end_misery"
    except Exception as e:
        logger.error(f"Error during grading: {str(e)}")
        cleanup_resources(state)
        return "end_misery"

    answer_useful = bool(answer_score and answer_score.binary_score)
    grounded = (
        bool(hallucination_score and hallucination_score.binary_score)
        if has_documents
        else None
    )
    route = resolve_generation_grade_route(
        has_documents=has_documents,
        answer_useful=answer_useful,
        grounded=grounded,
        retry_count=state.get("retry_count", 0),
    )

    if route == "useful":
        if has_documents and grounded is False:
            logger.info(
                "---DECISION: GENERATION ADDRESSES QUERY (UNGROUNDED / GENERAL KNOWLEDGE)---"
            )
        else:
            logger.info("---DECISION: GENERATION ADDRESSES QUERY---")
    elif route == "not useful":
        logger.info("---GROUNDED BUT NOT USEFUL: RE-TRY VIA HITL---")
    elif route == "need search web":
        if not has_documents:
            logger.info("---NO DOCUMENTS + NOT USEFUL: TRY WEB SEARCH---")
        else:
            logger.info("---NOT GROUNDED AND NOT USEFUL: TRY WEB SEARCH---")
    elif route == "end_misery":
        logger.info("---DECISION: TOO MANY RETRIES, I AM GONNA END THIS MISERY---")
        cleanup_resources(state)

    return route


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
    if datasource == "kb_meta":
        logger.info("---ROUTE TO KB_META---")
        return KB_META
    if datasource == "chub":
        logger.info("---ROUTE TO ASK CHUB PERMISSION---")
        return ASK_CHUB_PERMISSION
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
    """After grading: generate, ask chub permission, or fall back to websearch."""
    logger.info("---AFTER GRADE---")
    documents = state.get("documents") or []
    if len(documents) > 0:
        return GENERATE
    if state.get("chub_enrich_attempted"):
        logger.info("---CHUB ALREADY ATTEMPTED; WEB SEARCH---")
        return WEBSEARCH
    logger.info("---ROUTE TO ASK CHUB PERMISSION---")
    return ASK_CHUB_PERMISSION


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
workflow.add_node(KB_META, kb_meta)
workflow.add_node(ROUTE_AND_FRAMEWORK, route_and_framework)
workflow.add_node(RETRIEVE, retrieve)
workflow.add_node(GRADE_DOCUMENTS, grade_documents)
workflow.add_node(
    ASK_CHUB_PERMISSION,
    ask_chub_permission,
    destinations=(ASK_CHUB_PERMISSION, CHUB_EXPERT, GENERATE),
)
workflow.add_node(CHUB_EXPERT, chub_expert)
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
workflow.add_edge(KB_META, END)
workflow.add_edge(SUMMARIZE, ROUTE_AND_FRAMEWORK)
workflow.add_conditional_edges(
    ROUTE_AND_FRAMEWORK,
    after_route_and_framework,
    {
        WEBSEARCH: WEBSEARCH,
        RETRIEVE: RETRIEVE,
        GENERATE: GENERATE,
        KB_META: KB_META,
        ASK_CHUB_PERMISSION: ASK_CHUB_PERMISSION,
    },
)

workflow.add_edge(RETRIEVE, GRADE_DOCUMENTS)
workflow.add_conditional_edges(
    GRADE_DOCUMENTS,
    after_grade,
    {
        GENERATE: GENERATE,
        ASK_CHUB_PERMISSION: ASK_CHUB_PERMISSION,
        WEBSEARCH: WEBSEARCH,
    },
)
# ASK_CHUB_PERMISSION routes only via Command (no edges) — avoids parallel fan-out.
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
