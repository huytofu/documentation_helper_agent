"""Demo"""

import os
import logging
import logging.config
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import uvicorn
# from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent, CopilotKitContext
from graph.graph import app as graph

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    force=True  # Force reconfiguration of the root logger
)

# Configure specific loggers
logging.getLogger("graph.graph").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("fastapi").setLevel(logging.DEBUG)
logging.getLogger("copilotkit").setLevel(logging.DEBUG)  # Add CopilotKit logger

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("Starting application...")

app = FastAPI()

# Configure the CopilotKit endpoint with proper logging
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="documentation_helper",
            description="Documentation helper agent that assists with code documentation and implementation.",
            graph=graph,
            config={
                "configurable": {
                    "thread_id": "default-thread",
                    "checkpoint_ns": "default-ns",
                    "checkpoint_id": "default-checkpoint"
                }
            }
        )
    ],
)

# Add the CopilotKit info endpoint with both GET and POST methods
@app.get("/copilotkit/info")
@app.post("/copilotkit/info")
async def copilotkit_info(request: Request):
    """Provide information about available agents."""
    logger.info("Received CopilotKit info request")
    try:
        # Get context from request headers
        context = CopilotKitContext(
            thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
            checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
            checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
        )
        name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
        info = sdk.info(context=context)
        logger.info("Successfully retrieved CopilotKit info")
        return info
    except Exception as e:
        logger.error(f"Error getting CopilotKit info: {str(e)}", exc_info=True)
        raise

# Add the CopilotKit GET endpoint for actions
@app.get("/copilotkit")
async def copilotkit_actions(request: Request):
    """Handle CopilotKit action fetching."""
    logger.info("Received CopilotKit actions request")
    try:
        # Get context from request headers
        context = CopilotKitContext(
            thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
            checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
            checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
        )
        name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
        actions = sdk._get_action(context=context, name=name)
        logger.info("Successfully retrieved CopilotKit actions")
        return actions
    except Exception as e:
        logger.error(f"Error getting CopilotKit actions: {str(e)}", exc_info=True)
        raise

# Add the CopilotKit POST endpoint for requests
@app.post("/copilotkit")
async def copilotkit_endpoint(request: Request):
    """Handle CopilotKit requests."""
    logger.info("Received CopilotKit request")
    try:
        # Get the request body
        body = await request.json()
        
        # Get context from request headers
        context = CopilotKitContext(
            thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
            checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
            checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
        )
        name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
        # Add context and name to the request body
        body["context"] = context
        body["name"] = name
        
        response = await sdk.handle_request(body)
        logger.info("Successfully processed CopilotKit request")
        return response
    except Exception as e:
        logger.error(f"Error processing CopilotKit request: {str(e)}", exc_info=True)
        raise

# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    logger.info("Health check endpoint called")
    return {"status": "ok"}

# Add test endpoint
@app.post("/test")
async def test():
    """Test endpoint to verify backend is working."""
    logger.info("Test endpoint called")
    try:
        # Test the graph workflow with required checkpointer keys
        state = {
            "language": "python",
            "query": "Please generate a simple python function that prints 'Hello, World!'",
            "documents": [],
            "framework": "",
            "generation": "",
            "comment": "",
            "retry_count": 0  # Add retry count for the workflow
        }
        logger.info(f"Starting test workflow with state: {state}")
        result = await graph.ainvoke(state, config={"configurable": {
            "thread_id": "test-thread", 
            "checkpoint_ns": "test-ns", 
            "checkpoint_id": "test-checkpoint"
        }})
        logger.info(f"Test workflow completed with result: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Add our graph logger to uvicorn's config
    log_config["loggers"]["graph.graph"] = {
        "handlers": ["default"],
        "level": "DEBUG",
        "propagate": False
    }
    
    # Add more loggers to uvicorn's config
    log_config["loggers"]["uvicorn"] = {
        "handlers": ["default"],
        "level": "DEBUG",
        "propagate": False
    }
    
    log_config["loggers"]["fastapi"] = {
        "handlers": ["default"],
        "level": "DEBUG",
        "propagate": False
    }
    
    log_config["loggers"]["copilotkit"] = {
        "handlers": ["default"],
        "level": "DEBUG",
        "propagate": False
    }
    
    logger.info("Starting uvicorn server with logging configuration")
    uvicorn.run(
        "graph.demo:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."],
        log_config=log_config,
        log_level="debug"  # Set uvicorn's log level to debug
    )

if __name__ == "__main__":
    main() 