from langgraph.graph import END, StateGraph
from agent.graph.chains.answer_grader import answer_grader, GradeAnswer
from agent.graph.chains.sentiment_grader import sentiment_grader, GradeSentiment
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.state import GraphState

from agent.graph.consts import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE, PRE_HUMAN_IN_LOOP, POST_HUMAN_IN_LOOP
from agent.graph.nodes import generate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize, pre_human_in_loop, post_human_in_loop
from agent.graph.state import GraphState, InputGraphState, OutputGraphState

import logging

logger = logging.getLogger("graph.real_flow")

def grade_generation_grounded_in_documents_and_query(state: GraphState) -> str:
    logger.info("---CHECK HALLUCINATIONS---")
    query = state["query"]
    documents = state["documents"]
    generation = state["generation"]
    score = {}

    hallucination_counter = 0
    while not hasattr(score, "binary_score") and hallucination_counter < 1:
        score: GradeHallucinations = hallucination_grader.invoke(
            {"documents": "\n\n".join([doc.page_content for doc in documents]) , "generation": generation}
        )
        hallucination_counter += 1

    if score and score.binary_score:
        logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        logger.info("---GRADE GENERATION vs query---")
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
    else:
        logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        if state["retry_count"] == 0:
            return "not supported"
        elif state["retry_count"] < 2:
            return "need search web"
        logger.info("---DECISION: TOO MANY RETRIES, I AM GONNA END THIS MISERY---")
        return "end_misery"


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
        "bad": GENERATE,
    }
)
workflow.add_edge(POST_HUMAN_IN_LOOP, END)