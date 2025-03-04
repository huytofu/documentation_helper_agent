"""Demo"""

import os
import logging
import logging.config
import yaml
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from graph.graph import app as graph

# Configure logging
logger = logging.getLogger(__name__)

# Load logging configuration
try:
    with open('logging_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        logger.info("Logging configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load logging configuration: {e}")
    # Fallback to basic configuration
    logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="documentation_helper",
            description="Documentation helper agent that assists with code documentation and implementation.",
            graph=graph,
        )
    ],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")

# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "graph.demo:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."]
    )

if __name__ == "__main__":
    main() 