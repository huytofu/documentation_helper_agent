"""Demo"""

import os
from dotenv import load_dotenv
load_dotenv()

import logging
import logging.config
import yaml
from fastapi import FastAPI, Request
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent, CopilotKitContext
from agent.graph.graph import app as agent_app
from fastapi.middleware.cors import CORSMiddleware
import json

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
                "force_use": True,  # Force using the LangGraph agent
                "priority": 1,  # Highest priority
                "metadata": {
                    "requires_langgraph": True,
                    "timestamp": "auto"
                },
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
    
    # Extract user ID and update request state
    request, user_id = await extract_user_id_and_update_state(request)
    
    response = await call_next(request)
    logger.info("=== End Request ===\n")
    return response

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
            logger.info("Original Body:")
            logger.info(json.dumps(body_json, indent=2))
            
            # Update body with combined state
            body_json = update_request_state(body_json, user_id)
                
            logger.info("Updated Body with consolidated state:")
            logger.info(json.dumps(body_json, indent=2))
            
            # Create a new request with the modified body
            request._body = json.dumps(body_json).encode()
        except Exception as e:
            logger.error(f"Error processing request body: {str(e)}")
            logger.info(f"Raw body: {body}")
    
    return request, user_id

def update_request_state(body_json: dict, user_id: str | None) -> dict:
    """
    Update request state with user_id and other properties.
    
    Args:
        body_json: The request body JSON
        user_id: The extracted user ID
        
    Returns:
        Updated request body
    """
    # Initialize state if not present
    if "state" not in body_json:
        body_json["state"] = {}
    
    # Add user_id to state if available
    if user_id:
        body_json["state"]["user_id"] = user_id
    
    # Extract properties and assign to state if they exist
    if "properties" in body_json:
        properties = body_json["properties"]
        body_json["state"].update(properties)
    
    return body_json

add_fastapi_endpoint(app, sdk, "/copilotkitagent")

# # Add the CopilotKit info endpoint with both GET and POST methods
# @app.get("/copilotkit/info")
# @app.post("/copilotkit/info")
# async def copilotkit_info(request: Request):
#     """Provide information about available agents."""
#     logger.info("Received CopilotKit info request")
#     try:
#         # Get context from request headers
#         context = CopilotKitContext(
#             thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
#             checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
#             checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
#         )
#         name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
#         info = sdk.info(context=context)
#         logger.info("Successfully retrieved CopilotKit info")
#         return info
#     except Exception as e:
#         logger.error(f"Error getting CopilotKit info: {str(e)}", exc_info=True)
#         raise

# # Add the CopilotKit GET endpoint for actions
# @app.get("/copilotkit")
# async def copilotkit_actions(request: Request):
#     """Handle CopilotKit action fetching."""
#     logger.info("Received CopilotKit actions request")
#     try:
#         # Get context from request headers
#         context = CopilotKitContext(
#             thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
#             checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
#             checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
#         )
#         name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
#         actions = sdk._get_action(context=context, name=name)
#         logger.info("Successfully retrieved CopilotKit actions")
#         return actions
#     except Exception as e:
#         logger.error(f"Error getting CopilotKit actions: {str(e)}", exc_info=True)
#         raise

# # Add the CopilotKit POST endpoint for requests
# @app.post("/copilotkit")
# async def copilotkit_endpoint(request: Request):
#     """Handle CopilotKit requests."""
#     logger.info("Received CopilotKit request")
#     try:
#         # Get the request body
#         body = await request.json()
        
#         # Get context from request headers
#         context = CopilotKitContext(
#             thread_id=request.headers.get("x-copilotkit-thread-id", "default-thread"),
#             checkpoint_ns=request.headers.get("x-copilotkit-checkpoint-ns", "default-ns"),
#             checkpoint_id=request.headers.get("x-copilotkit-checkpoint-id", "default-checkpoint")
#         )
#         name = request.headers.get("x-copilotkit-name", "documentation_helper")
        
#         # Add context and name to the request body
#         body["context"] = context
#         body["name"] = name
        
#         response = await sdk.handle_request(body)
#         logger.info("Successfully processed CopilotKit request")
#         return response
#     except Exception as e:
#         logger.error(f"Error processing CopilotKit request: {str(e)}", exc_info=True)
#         raise

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
            "query": "Please generate a simple joke about Copilokit",
            "documents": [],
            "framework": "default",
            "generation": "",
            "comments": "",
            "retry_count": 0,
            "messages": []  # Initialize empty messages array
        }
        logger.info(f"Starting test workflow with state: {state}")
        result = await agent_app.ainvoke(state, config={
            "configurable": {
                "thread_id": "test-thread", 
                "checkpoint_ns": "test-ns", 
                "checkpoint_id": "test-checkpoint"
            },
        })
        logger.info(f"Test workflow completed with result: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

# Add conversation API endpoint
@app.post("/conversation")
async def save_conversation(request: Request):
    """
    Endpoint to save conversation history.
    
    This endpoint is called from the frontend API to save user questions
    and assistant answers in the database.
    """
    logger.info("Conversation endpoint called at /api/conversation")
    
    try:
        # Parse request body
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
            return {"success": False, "error": error_message}
            
        # Return successful response
        return {"success": True, "message_id": result.get("message_id")}
        
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}")
        return {"success": False, "error": f"Server error: {str(e)}"}

# Add logging for agent initialization
logger.info("Initialized LangGraph agent")

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
        "agent.graph.demo:app",
        host="0.0.0.0",
        port=port,
        log_config=log_config,
    )

if __name__ == "__main__":
    main() 