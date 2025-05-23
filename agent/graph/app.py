"""FastAPI Application Definition for Vercel Serverless"""

# Import necessary modules and load environment variables
import os
import datetime
import asyncio
import uvicorn
import time
import json
from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from agent.graph.graph import app as agent_app
from agent.graph.state import GraphState
from agent.graph.models.config import with_concurrency_limit
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.responses import JSONResponse
from collections import defaultdict
from agent.graph.utils.api_utils import (
    _sanitize_sensitive_data,
    extract_properties_and_update_state
)

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
logger.info("Initializing FastAPI application for Vercel...")

# Create FastAPI app
app = FastAPI()

# Debug log the app instance
logger.info(f"FastAPI app instance: {id(app)} at {app}")

# Security Configuration
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
CIRCUIT_BREAKER_THRESHOLD = float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "0.8"))  # 80% error rate
CIRCUIT_BREAKER_RESET = int(os.getenv("CIRCUIT_BREAKER_RESET", "60"))

# Enhanced Rate Limit Middleware
class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.circuit_breaker_state = defaultdict(lambda: {"open": False, "last_failure": 0})
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Check circuit breaker
        async with self.lock:
            if self.circuit_breaker_state[client_ip]["open"]:
                if current_time - self.circuit_breaker_state[client_ip]["last_failure"] < CIRCUIT_BREAKER_RESET:
                    raise HTTPException(
                        status_code=503,
                        detail="Service temporarily unavailable due to high error rate"
                    )
                else:
                    self.circuit_breaker_state[client_ip]["open"] = False
                    self.error_counts[client_ip] = 0

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Request too large"
            )

        # Clean up old requests
        async with self.lock:
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if current_time - t < RATE_LIMIT_WINDOW
            ]

            # Check rate limit
            if len(self.requests[client_ip]) >= RATE_LIMIT_REQUESTS:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )

            # Add current request
            self.requests[client_ip].append(current_time)

        try:
            # Add timeout to request handling
            response = await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT)
            
            # Update circuit breaker on success
            async with self.lock:
                if self.error_counts[client_ip] > 0:
                    self.error_counts[client_ip] = max(0, self.error_counts[client_ip] - 1)

            return response

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Request timeout"
            )
        except Exception as e:
            # Update error counts and circuit breaker
            async with self.lock:
                self.error_counts[client_ip] += 1
                if self.error_counts[client_ip] / RATE_LIMIT_REQUESTS > CIRCUIT_BREAKER_THRESHOLD:
                    self.circuit_breaker_state[client_ip]["open"] = True
                    self.circuit_breaker_state[client_ip]["last_failure"] = current_time
            raise

# Add enhanced rate limiting middleware
app.add_middleware(EnhancedRateLimitMiddleware)

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
DOCUMENTATION_HELPER_API_KEY = os.getenv("DOCUMENTATION_HELPER_API_KEY", "")
if not DOCUMENTATION_HELPER_API_KEY:
    logger.warning("DOCUMENTATION_HELPER_API_KEY not set in environment variables")

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not DOCUMENTATION_HELPER_API_KEY:
        return None
    if not api_key or api_key != DOCUMENTATION_HELPER_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

# Configure CORS with strict settings
FRONTEND_URL = os.getenv("FRONTEND_URL")
if not FRONTEND_URL:
    logger.error("FRONTEND_URL not set in environment variables")
    raise ValueError("FRONTEND_URL environment variable is required")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=3600,
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log requests and responses."""
    # Log request details
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Get request body if it exists
    try:
        body = await request.json()
        # Sanitize sensitive data before logging
        sanitized_body = _sanitize_sensitive_data(body)
        logger.info(f"Request body: {sanitized_body}")
        
        # Extract user_id and update state
        updated_body = extract_properties_and_update_state(body)
        # Update the request with the modified body
        request._body = json.dumps(updated_body).encode()
    except Exception as e:
        logger.warning(f"Could not parse request body: {e}")
    
    # Process the request
    response = await call_next(request)
    
    # Log response details
    logger.info(f"Response status: {response.status_code}")
    
    return response

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
            }
        )
    ],
)

add_fastapi_endpoint(app, sdk, "/api/copilotkitagent")

# Store the last warm-up time in memory (will reset on cold start)
last_warmup_time = 0
WARMUP_INTERVAL = 600 # 10 minutes

async def warmup_function():
    """Warm up the model and graph by making a lightweight request."""
    try:
        # Create a minimal state for warm-up
        warmup_state = GraphState(
            query="print: please ask me a question",
            documents=[],
            messages=[],
            user_id="test",
            language="python",
            comments="",
            current_node="",
            rewritten_query="print: please ask me a question",
            retry_count=0,
            framework="",
            pass_summarize=False,
            summarized=False

        )
        
        # Run a minimal graph iteration with concurrency limit
        result = await with_concurrency_limit(agent_app.ainvoke, warmup_state)
        
        logger.info("Warm-up successful. Result: %s", result)
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

# Add conversation history endpoint
@app.post("/api/conversation")
async def save_conversation(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Endpoint to save conversation history.
    
    This endpoint is called from the frontend API to save user questions
    and assistant answers in the database.
    """
    logger.info("Conversation endpoint called at /api/conversation")
    
    try:
        data = await request.json()

        # Log the request data
        logger.info(f"Conversation save request received: {data}")
        
        # Import database utils
        from agent.graph.utils.firebase_utils import handle_conversation_history_request
        
        
        # Forward the request to the database handler
        result = handle_conversation_history_request(data)
        
        # Check if the operation was successful
        if not result.get("success", False):
            error_message = result.get("error", "Unknown database error")
            logger.error(f"Failed to save conversation: {error_message}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": error_message}
            )
            
        # Return successful response
        return JSONResponse(
            status_code=200,
            content={"success": True, "message_id": result.get("message_id")}
        )
        
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Server error: {str(e)}"}
        )

# Add simple health check endpoint
@app.get("/health")
def health():
    """Simple health check."""
    logger.info("Health check endpoint called")
    return {"status": "ok"}

# Add logging for agent initialization
logger.info("FastAPI application initialized with LangGraph agent for Vercel")

# Add a simple test endpoint to check if FastAPI is working correctly
@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint to verify that the FastAPI app is accessible."""
    return {"message": "FastAPI is working!"}

# At the bottom of your file, add this if statement to directly run with uvicorn
if __name__ == "__main__":
    import uvicorn
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
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=log_config) 