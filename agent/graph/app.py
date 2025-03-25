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
from agent.graph.models.config import get_model_config, with_concurrency_limit
from agent.graph.utils.batch_processor import BatchProcessor, BatchResult
import datetime
import asyncio
from typing import Dict, Any, List
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import re

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

# Initialize batch processor with rate limiting
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = datetime.datetime.now()
        
        # Clean up old requests
        self.requests = {
            ip: times for ip, times in self.requests.items()
            if (current_time - times[-1]).total_seconds() < 60
        }
        
        # Check rate limit
        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
            self.requests[client_ip].append(current_time)
        else:
            self.requests[client_ip] = [current_time]
        
        return await call_next(request)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=int(os.getenv("RATE_LIMIT", "60"))
)

# Initialize batch processor with validation
def validate_batch_size(size: int) -> int:
    max_size = int(os.getenv("MAX_BATCH_SIZE", "10"))
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {max_size}"
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
                "stream_mode": "all"
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
        # Validate state
        if not isinstance(state, dict):
            raise ValueError("Invalid state format")
        
        # Convert input state to GraphState
        graph_state = GraphState(**state)
        
        # Run the graph with concurrency limit
        result = await with_concurrency_limit(graph.ainvoke, graph_state)
        
        return result
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise

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
async def chat(
    state: Dict[str, Any],
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Main chat endpoint that processes user queries."""
    try:
        return await process_single_request(state)
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
        
        return await batch_processor.process_batch(
            items=states,
            process_fn=process_single_request
        )
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
    
    body = await request.body()
    if body:
        try:
            body_json = json.loads(body)
            if os.getenv("ENVIRONMENT") == "development":
                # Sanitize sensitive data
                sanitized_body = _sanitize_sensitive_data(body_json)
                logger.info("Sanitized Body:")
                logger.info(json.dumps(sanitized_body, indent=2))
            
            # Extract properties and assign to state if they exist
            if "properties" in body_json:
                properties = body_json["properties"]
                if "state" not in body_json:
                    body_json["state"] = {}
                body_json["state"].update(properties)
                
                if os.getenv("ENVIRONMENT") == "development":
                    logger.info("Updated Body with properties in state:")
                    logger.info(json.dumps(_sanitize_sensitive_data(body_json), indent=2))
                
                # Create a new request with the modified body
                request._body = json.dumps(body_json).encode()
        except:
            if os.getenv("ENVIRONMENT") == "development":
                logger.info("Raw body (sanitized): [REDACTED]")
    
    response = await call_next(request)
    logger.info("=== End Request ===\n")
    return response

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