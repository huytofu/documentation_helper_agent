from dotenv import load_dotenv
load_dotenv()
import logging
import os

from agent.graph.langgraph_compat import ensure_compiled_graph_alias

ensure_compiled_graph_alias()

# Import the workflows instead of the compiled apps
# Depending on the FLOW environment variable, import the appropriate workflow
if os.environ.get("FLOW") == "test":
    from agent.graph.flows.test_flow import workflow
elif os.environ.get("FLOW") == "simple":
    from agent.graph.flows.simple_flow import workflow
else:
    from agent.graph.flows.real_flow import workflow

# Import the checkpointer factory and long-term store
from agent.graph.checkpointers import get_checkpointer
from agent.graph.stores import ensure_store_setup, get_store

# Configure logging for the graph module
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# Get the appropriate checkpointer based on environment
checkpointer = get_checkpointer()
logger.info(f"Using checkpointer: {checkpointer.__class__.__name__}")

# App-level long-term memory (chub package catalog, etc.)
store = get_store()
ensure_store_setup(store)
logger.info(f"Using store: {store.__class__.__name__}")

# The compiled app is used to manage the workflow execution
app = workflow.compile(checkpointer=checkpointer, store=store)
logger.debug("Graph compiled successfully")

# Uncomment the following line to generate a visual representation of the graph
# app.get_graph().draw_mermaid_png(output_file_path="graph.png")


