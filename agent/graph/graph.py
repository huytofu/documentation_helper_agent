from dotenv import load_dotenv
load_dotenv()
import logging
import os

# Import the workflows instead of the compiled apps
if os.environ.get("FLOW") == "test":
    from agent.graph.test_flow import workflow
elif os.environ.get("FLOW") == "simple":
    from agent.graph.simple_flow import workflow
else:
    from agent.graph.real_flow import workflow

# Import the checkpointer factory
from agent.graph.checkpointers import get_checkpointer

# Configure logging
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# Get the appropriate checkpointer based on environment
checkpointer = get_checkpointer()
logger.info(f"Using checkpointer: {checkpointer.__class__.__name__}")

# Compile the workflow centrally with streaming enabled
app = workflow.compile(checkpointer=checkpointer, streaming=True)
logger.debug("Graph compiled successfully with streaming enabled")

#app.get_graph().draw_mermaid_png(output_file_path="graph.png")
