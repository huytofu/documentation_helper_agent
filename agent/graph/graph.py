from dotenv import load_dotenv
load_dotenv()
from langgraph.checkpoint.memory import MemorySaver
# from langgraph.checkpoint.sqlite import SqliteSaver
import logging
import os

# Import the compiled app with streaming enabled instead of the raw workflow
if os.environ.get("FLOW") == "test":
    from agent.graph.test_flow import app
elif os.environ.get("FLOW") == "simple":
    from agent.graph.simple_flow import app
else:
    from agent.graph.real_flow import app

# Configure logging
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized with streaming enabled")

# memory = SqliteSaver.from_conn_string(":memory:")
memory = MemorySaver()

# No need to compile again, the imported apps are already compiled with streaming
# app = workflow.compile(checkpointer=memory, streaming=True)

#app.get_graph().draw_mermaid_png(output_file_path="graph.png")
