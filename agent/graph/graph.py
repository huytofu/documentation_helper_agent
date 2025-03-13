from dotenv import load_dotenv
load_dotenv()
from langgraph.checkpoint.memory import MemorySaver
# from langgraph.checkpoint.sqlite import SqliteSaver
import logging
import os
if os.environ.get("FLOW") == "test":
    from agent.graph.test_flow import workflow
else:
    from agent.graph.real_flow import workflow

# Configure logging
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# memory = SqliteSaver.from_conn_string(":memory:")
memory = MemorySaver()

app = workflow.compile(checkpointer=memory)

#app.get_graph().draw_mermaid_png(output_file_path="graph.png")
