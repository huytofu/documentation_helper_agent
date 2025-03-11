from dotenv import load_dotenv
load_dotenv()
from langgraph.checkpoint.memory import MemorySaver
# from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
import logging

from agent.graph.chains.answer_grader import answer_grader, GradeAnswer
from agent.graph.chains.hallucination_grader import hallucination_grader, GradeHallucinations
from agent.graph.chains.query_router import query_router, RouteQuery
from agent.graph.consts import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH, DECIDE_VECTORSTORE, HUMAN_IN_LOOP, INITIALIZE, DECIDE_LANGUAGE
from agent.graph.nodes import generate, grade_documents, retrieve, decide_vectorstore, decide_language, web_search, human_in_loop, initialize
from agent.graph.state import GraphState

# Configure logging
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# memory = SqliteSaver.from_conn_string(":memory:")
memory = MemorySaver()

def grade_generation_grounded_in_documents_and_query(state: GraphState) -> str:
    logger.info("---CHECK HALLUCINATIONS---")
    query = state["query"]
    documents = state["documents"]
    generation = state["generation"]
    score = {}

    while not hasattr(score, "binary_score"):
        score: GradeHallucinations = hallucination_grader.invoke(
            {"documents": "\n\n".join([doc.page_content for doc in documents]) , "generation": generation}
        )

    if hallucination_grade := score.binary_score:
        logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        logger.info("---GRADE GENERATION vs query---")
        score = {}
        while not hasattr(score, "binary_score"):
            score: GradeAnswer = answer_grader.invoke({"query": query, "generation": generation})
        
        if answer_grade := score.binary_score:
            logger.info("---DECISION: GENERATION ADDRESSES query---")
            return "useful"
        else:
            logger.info("---DECISION: GENERATION DOES NOT ADDRESS query---")
            return "not useful"
    else:
        logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        if state["retry_count"] < 3:
            return "not supported"
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
    
workflow = StateGraph(GraphState)

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
        "not supported": HUMAN_IN_LOOP,
        "end_misery": END,
        "useful": END,
        "not useful": WEBSEARCH,
    },
)
workflow.add_edge(HUMAN_IN_LOOP, GENERATE)


app = workflow.compile(checkpointer=memory)

#app.get_graph().draw_mermaid_png(output_file_path="graph.png")
