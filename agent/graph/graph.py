from dotenv import load_dotenv
load_dotenv()
import logging
import os

# Import the workflows instead of the compiled apps
# Depending on the FLOW environment variable, import the appropriate workflow
if os.environ.get("FLOW") == "test":
    from agent.graph.test_flow import workflow
elif os.environ.get("FLOW") == "simple":
    from agent.graph.simple_flow import workflow
else:
    from agent.graph.real_flow import workflow

# Import the checkpointer factory
from agent.graph.checkpointers import get_checkpointer

# Configure logging for the graph module
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# Get the appropriate checkpointer based on environment
checkpointer = get_checkpointer()
logger.info(f"Using checkpointer: {checkpointer.__class__.__name__}")

# Compile the workflow centrally with streaming enabled
# The compiled app is used to manage the workflow execution
app = workflow.compile(checkpointer=checkpointer)
logger.debug("Graph compiled successfully with streaming enabled")

# Uncomment the following line to generate a visual representation of the graph
app.get_graph().draw_mermaid_png(output_file_path="graph.png")
