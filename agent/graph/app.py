"""FastAPI Application Definition for Vercel Serverless"""

# Import necessary modules and load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

import logging
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from agent.graph.graph import app as agent_app, graph
from agent.graph.state import GraphState
from agent.graph.models.config import get_model_config, with_concurrency_limit
import datetime
import asyncio
from typing import Dict, Any
import uvicorn

# Configure root logger
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    force=True
)

# Configure specific loggers
logging.getLogger("graph.graph").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)
logging.getLogger("copilotkit").setLevel(logging.INFO)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("Initializing FastAPI application for Vercel...")

# Create FastAPI app
app = FastAPI()

# Configure CORS for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],  # Use environment variable for frontend URL
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

# Store the last warm-up time in memory (will reset on cold start)
last_warmup_time = 0
WARMUP_INTERVAL = 300  # 5 minutes

async def warmup_function():
    """Warm up the model and graph by making a lightweight request."""
    try:
        # Get model config to ensure models are loaded
        config = get_model_config()
        
        # Create a minimal state for warm-up
        warmup_state = GraphState(
            query="test",
            documents=[],
            messages=[],
            current_node="INITIALIZE"
        )
        
        # Run a minimal graph iteration with concurrency limit
        result = await with_concurrency_limit(graph.ainvoke, warmup_state)
        
        logger.info("Warm-up successful")
        return True
    except Exception as e:
        logger.error(f"Warm-up failed: {str(e)}")
        return False

@app.get("/api/warmup")
async def warmup():
    """Endpoint to warm up the serverless function."""
    global last_warmup_time
    current_time = asyncio.get_event_loop().time()
    
    # Only warm up if enough time has passed since last warm-up
    if current_time - last_warmup_time < WARMUP_INTERVAL:
        return {"status": "already_warm", "last_warmup": last_warmup_time}
    
    success = await warmup_function()
    if success:
        last_warmup_time = current_time
        return {"status": "warmed_up", "timestamp": last_warmup_time}
    else:
        raise HTTPException(status_code=500, detail="Warm-up failed")

@app.post("/api/chat")
async def chat(state: Dict[str, Any]) -> Dict[str, Any]:
    """Main chat endpoint that processes user queries."""
    try:
        # Convert input state to GraphState
        graph_state = GraphState(**state)
        
        # Run the graph with concurrency limit
        result = await with_concurrency_limit(graph.ainvoke, graph_state)
        
        return result
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests and modify request body if needed."""
    logger.info("\n=== Incoming Request ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Method: {request.method}")
    
    # Only log headers in development
    if os.getenv("ENVIRONMENT") == "development":
        logger.info("Headers:")
        for header, value in request.headers.items():
            logger.info(f"  {header}: {value}")
    
    body = await request.body()
    if body:
        try:
            body_json = json.loads(body)
            if os.getenv("ENVIRONMENT") == "development":
                logger.info("Original Body:")
                logger.info(json.dumps(body_json, indent=2))
            
            # Extract properties and assign to state if they exist
            if "properties" in body_json:
                properties = body_json["properties"]
                if "state" not in body_json:
                    body_json["state"] = {}
                body_json["state"].update(properties)
                
                if os.getenv("ENVIRONMENT") == "development":
                    logger.info("Updated Body with properties in state:")
                    logger.info(json.dumps(body_json, indent=2))
                
                # Create a new request with the modified body
                request._body = json.dumps(body_json).encode()
        except:
            if os.getenv("ENVIRONMENT") == "development":
                logger.info(f"Raw body: {body}")
    
    response = await call_next(request)
    logger.info("=== End Request ===\n")
    return response

# Add CopilotKit endpoint
add_fastapi_endpoint(app, sdk, "/api/copilotkitagent")

# Health check endpoint for Vercel
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Vercel to verify server status."""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.datetime.now().isoformat()
    }

# Add logging for agent initialization
logger.info("FastAPI application initialized with LangGraph agent for Vercel")

# Remove the main block as it's not needed for Vercel 