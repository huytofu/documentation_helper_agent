"""FastAPI Application Definition for Vercel Serverless"""

# Import necessary modules and load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

import logging
import json
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from agent.graph.graph import app as agent_app, graph
from agent.graph.state import GraphState
from agent.graph.models.config import with_concurrency_limit
from agent.graph.utils.batch_processor import BatchProcessor, BatchResult
from agent.graph.utils.security import (
    validate_state,
    validate_batch_states,
    sanitize_response,
    SecurityError
)
import datetime
import asyncio
from typing import Dict, Any, List
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import re
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import time
from collections import defaultdict
import hashlib

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
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

# Security Configuration
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
CIRCUIT_BREAKER_THRESHOLD = float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "0.8"))  # 80% error rate
CIRCUIT_BREAKER_RESET = int(os.getenv("CIRCUIT_BREAKER_RESET", "60"))  # seconds

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

# Add GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY = os.getenv("API_KEY", "")
if not API_KEY:
    logger.warning("API_KEY not set in environment variables")

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not API_KEY:
        return None
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

# Initialize batch processor with validation
def validate_batch_size(size: int) -> int:
    if size > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE}"
        )
    return size

batch_processor = BatchProcessor(
    max_batch_size=validate_batch_size(int(os.getenv("MAX_BATCH_SIZE", "10"))),
    max_workers=int(os.getenv("MAX_WORKERS", "5")),
    timeout=float(os.getenv("BATCH_TIMEOUT", "30.0"))
)

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

# Store the last warm-up time in memory (will reset on cold start)
last_warmup_time = 0
WARMUP_INTERVAL = 300  # 5 minutes

async def process_single_request(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single chat request."""
    try:
        # Validate and sanitize state
        try:
            state = validate_state(state)
        except SecurityError as e:
            logger.warning(f"Security validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Convert input state to GraphState
        graph_state = GraphState(**state)
        
        # Run the graph with concurrency limit
        result = await with_concurrency_limit(graph.ainvoke, graph_state)
        
        # Sanitize response before returning
        return sanitize_response(result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise

async def warmup_function():
    """Warm up the model and graph by making a lightweight request."""
    try:
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
async def chat(
    state: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Main chat endpoint that processes user queries."""
    try:
        return await process_single_request(state)
    except SecurityError as e:
        logger.warning(f"Security error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/batch")
async def chat_batch(
    states: List[Dict[str, Any]],
    api_key: str = Depends(verify_api_key)
) -> List[BatchResult]:
    """Batch chat endpoint that processes multiple queries in parallel."""
    try:
        # Validate batch size
        validate_batch_size(len(states))
        
        # Validate and sanitize states
        try:
            states = validate_batch_states(states)
        except SecurityError as e:
            logger.warning(f"Security validation failed in batch: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        results = await batch_processor.process_batch(
            items=states,
            process_fn=process_single_request
        )
        
        # Sanitize results before returning
        return [sanitize_response(result) for result in results]
    except SecurityError as e:
        logger.warning(f"Security error in batch endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in batch chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add request logging middleware with sanitization
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests with sanitization."""
    logger.info("\n=== Incoming Request ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Method: {request.method}")
    
    # Only log non-sensitive headers in development
    if os.getenv("ENVIRONMENT") == "development":
        sensitive_headers = {"authorization", "cookie", "x-api-key"}
        logger.info("Headers:")
        for header, value in request.headers.items():
            if header.lower() not in sensitive_headers:
                logger.info(f"  {header}: {value}")
    
    # Extract user ID and update request state
    request, user_id = await extract_user_id_and_update_state(request)
    
    response = await call_next(request)
    logger.info("=== End Request ===\n")
    return response

def update_request_state(body_json: dict, user_id: str | None) -> dict:
    """Update request body with consolidated state including properties and user_id."""
    # Ensure state exists
    if "state" not in body_json:
        body_json["state"] = {}
    
    # Merge properties into state if they exist
    if "properties" in body_json:
        body_json["state"].update(body_json["properties"])
    
    # Add user_id to state if found
    if user_id:
        body_json["state"]["user_id"] = user_id
        logger.info(f"Added user_id to state: {user_id}")
    
    return body_json

async def extract_user_id_and_update_state(request: Request) -> tuple[Request, str | None]:
    """
    Extract user_id from request and update state in request body.
    
    This function consolidates all user_id extraction logic in one place:
    1. Extract from user_id cookie
    2. Extract from Firebase auth cookie
    3. Extract from x-user-id header
    
    Returns:
        Updated request and extracted user_id
    """
    user_id = None
    
    # 1. Try user_id cookie (simplest direct path)
    user_id = request.cookies.get("user_id")
    if user_id:
        logger.info(f"Found user_id in cookie: {user_id}")
    
    # 2. Try Firebase auth cookie
    if not user_id:
        firebase_auth = request.cookies.get("firebase:authUser")
        if firebase_auth:
            try:
                # Parse firebase auth cookie (JSON with possible domain prefix)
                if ":" in firebase_auth:
                    firebase_auth = firebase_auth.split(":", 1)[1]
                auth_data = json.loads(firebase_auth)
                user_id = auth_data.get("uid")
                if user_id:
                    logger.info(f"Extracted user_id from Firebase auth: {user_id}")
            except Exception as e:
                logger.error(f"Error parsing Firebase auth cookie: {str(e)}")
    
    # 3. Try custom header
    if not user_id and request.headers.get("x-user-id"):
        user_id = request.headers.get("x-user-id")
        logger.info(f"Using user_id from custom header: {user_id}")
    
    # Parse and update request body if present
    body = await request.body()
    if body:
        try:
            body_json = json.loads(body)
            if os.getenv("ENVIRONMENT") == "development":
                # Sanitize sensitive data for logging
                sanitized_body = _sanitize_sensitive_data(body_json)
                logger.info("Sanitized Body:")
                logger.info(json.dumps(sanitized_body, indent=2))
            
            # Update body with combined state
            body_json = update_request_state(body_json, user_id)
                
            if os.getenv("ENVIRONMENT") == "development":
                logger.info("Updated Body with consolidated state:")
                logger.info(json.dumps(_sanitize_sensitive_data(body_json), indent=2))
            
            # Create a new request with the modified body
            request._body = json.dumps(body_json).encode()
        except Exception as e:
            logger.error(f"Error processing request body: {str(e)}")
            if os.getenv("ENVIRONMENT") == "development":
                logger.info("Raw body (sanitized): [REDACTED]")
    
    return request, user_id

def _sanitize_sensitive_data(data: Any) -> Any:
    """Sanitize sensitive data in request/response bodies."""
    if isinstance(data, dict):
        sensitive_keys = {"api_key", "password", "token", "secret"}
        return {
            k: "[REDACTED]" if any(sk in k.lower() for sk in sensitive_keys)
            else _sanitize_sensitive_data(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_sanitize_sensitive_data(item) for item in data]
    return data

# Add CopilotKit endpoint with API key protection
add_fastapi_endpoint(app, sdk, "/api/copilotkitagent")

# Health check endpoint for Vercel
@app.get("/api/health")
async def health_check():
    """Health check endpoint for Vercel to verify server status."""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.datetime.now().isoformat(),
        "batch_processor": {
            "max_batch_size": batch_processor.max_batch_size,
            "max_workers": batch_processor.max_workers,
            "timeout": batch_processor.timeout
        }
    }

# Add logging for agent initialization
logger.info("FastAPI application initialized with LangGraph agent for Vercel")

# Add conversation endpoint
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
    try:
        # Extract user ID and update request state
        request, user_id = await extract_user_id_and_update_state(request)
        
        # Parse request body
        data = await request.json()
        
        # Log the request (but sanitize any sensitive information)
        safe_data = _sanitize_sensitive_data(data)
        logger.info(f"Conversation save request received: {safe_data}")
        
        # Add user_id to data if found and not already present
        if user_id and not data.get("user_id"):
            data["user_id"] = user_id
            logger.info(f"Added user_id to conversation data: {user_id}")
        
        # Import database utils (only when needed to avoid circular imports)
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