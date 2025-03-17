"""FastAPI Application Definition"""

import os
from dotenv import load_dotenv
load_dotenv()

import logging
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from agent.graph.graph import app as agent_app
import datetime

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    force=True
)

# Configure specific loggers
logging.getLogger("graph.graph").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("fastapi").setLevel(logging.DEBUG)
logging.getLogger("copilotkit").setLevel(logging.DEBUG)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("Initializing FastAPI application...")

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create SDK instance
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="coding_agent",
            description="Expert coding agent that assists users with answering coding-related questions, code documentation, code completion and implementation.",
            graph=agent_app,
            config={
                "force_use": True,
                "priority": 1,
                "metadata": {
                    "requires_langgraph": True,
                    "timestamp": "auto"
                },
                "stream_mode": "all"
            }
        )
    ],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("\n=== Incoming Request ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Method: {request.method}")
    logger.info("Headers:")
    for header, value in request.headers.items():
        logger.info(f"  {header}: {value}")
    
    body = await request.body()
    if body:
        try:
            body_json = json.loads(body)
            logger.info("Original Body:")
            logger.info(json.dumps(body_json, indent=2))
            
            # Extract properties and assign to state if they exist
            if "properties" in body_json:
                properties = body_json["properties"]
                if "state" not in body_json:
                    body_json["state"] = {}
                body_json["state"].update(properties)
                logger.info("Updated Body with properties in state:")
                logger.info(json.dumps(body_json, indent=2))
                
                # Create a new request with the modified body
                request._body = json.dumps(body_json).encode()
        except:
            logger.info(f"Raw body: {body}")
    
    response = await call_next(request)
    logger.info("=== End Request ===\n")
    return response

# Add CopilotKit endpoint
add_fastapi_endpoint(app, sdk, "/copilotkitagent")

# Test endpoint
@app.get("/test")
async def test_endpoint():
    """Test the LangGraph agent."""
    logger.info("Received test request")
    try:
        # Create a simple test state
        state = {
            "comments": "Test query: How do I use FastAPI?",
            "language": "python",
            "current_node": "initialize"
        }
        
        logger.info(f"Testing workflow with state: {state}")
        result = await agent_app.ainvoke(state, config={
            "configurable": {
                "thread_id": "test-thread", 
                "checkpoint_ns": "test-ns", 
                "checkpoint_id": "test-checkpoint"
            },
            "stream_mode": "updates"
        })
        logger.info(f"Test workflow completed with result: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

# Add health check endpoint for serverless platforms
@app.get("/health")
async def health_check():
    """Health check endpoint for serverless platforms."""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "server_type": os.getenv("SERVER_TYPE", "local"),
        "timestamp": datetime.datetime.now().isoformat()
    }

# Add logging for agent initialization
logger.info("FastAPI application initialized with LangGraph agent") 