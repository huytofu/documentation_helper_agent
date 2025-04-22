"""Serverless Handler Module

This module provides handler functions for various serverless platforms based on
the SERVER_TYPE environment variable.

Usage:
    Set the SERVER_TYPE environment variable to one of the following values:
    - "aws lambda" - For AWS Lambda deployment
    - "azure functions" - For Azure Functions deployment
    - "google cloud functions" - For Google Cloud Functions deployment
    - "vercel" - For Vercel deployment
    
    Example:
    ```
    # In your .env file
    SERVER_TYPE=aws lambda
    
    # Or set it directly in your environment
    export SERVER_TYPE="aws lambda"
    ```
    
    The module will automatically load the appropriate adapter for the specified platform.
    If SERVER_TYPE is not set or is set to an unknown value, a default handler will be used.
"""

import os
import logging
import json
from dotenv import load_dotenv
from agent.graph.app import app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("Serverless handler initializing")

# Get server type from environment variable
SERVER_TYPE = os.getenv("SERVER_TYPE", "").lower()
logger.info(f"Detected SERVER_TYPE: {SERVER_TYPE}")

# AWS Lambda handler
if SERVER_TYPE == "aws lambda":
    try:
        from mangum import Mangum
        handler = Mangum(app)
        logger.info("AWS Lambda handler initialized with Mangum")
    except ImportError:
        logger.error("Mangum not installed. Run 'pip install mangum' to deploy to AWS Lambda.")
        raise

# Azure Functions handler
elif SERVER_TYPE == "azure functions":
    try:
        import azure.functions as func
        
        async def main(req: func.HttpRequest) -> func.HttpResponse:
            """Azure Functions handler for FastAPI app."""
            from urllib.parse import urlparse
            
            # Convert Azure request to ASGI format
            path = req.url.replace(req.url.split("/api")[0], "")
            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": req.method,
                "path": path,
                "raw_path": path.encode(),
                "query_string": urlparse(req.url).query.encode(),
                "headers": [(k.encode(), v.encode()) for k, v in req.headers.items()],
            }
            
            # Create response objects
            async def receive():
                return {"type": "http.request", "body": req.get_body() or b""}
            
            response_body = []
            response_status = None
            response_headers = []
            
            async def send(message):
                nonlocal response_body, response_status, response_headers
                if message["type"] == "http.response.start":
                    response_status = message["status"]
                    response_headers = message["headers"]
                elif message["type"] == "http.response.body":
                    response_body.append(message.get("body", b""))
            
            # Call the ASGI app
            await app(scope, receive, send)
            
            # Convert ASGI response to Azure response
            headers = {k.decode(): v.decode() for k, v in response_headers}
            body = b"".join(response_body)
            
            return func.HttpResponse(
                body=body,
                status_code=response_status,
                headers=headers,
                mimetype=headers.get("content-type", "text/plain"),
            )
        
        logger.info("Azure Functions handler initialized")
    except ImportError:
        logger.error("Azure Functions SDK not installed. Run 'pip install azure-functions' to deploy to Azure.")
        raise

# Google Cloud Functions handler
elif SERVER_TYPE == "google cloud functions":
    try:
        from functions_framework import logging as ff_logging
        
        def gcp_handler(request):
            """Google Cloud Functions handler for FastAPI app."""
            from asgiref.wsgi import WsgiToAsgi
            from flask import Flask, request as flask_request, Response
            
            # Create a minimal Flask app
            flask_app = Flask(__name__)
            
            @flask_app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'])
            @flask_app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'])
            def catch_all(path):
                """Route all requests to the FastAPI app."""
                asgi_app = WsgiToAsgi(app)
                return asgi_app(flask_request.environ)
            
            # Process the request using the Flask app
            return flask_app(request.environ, lambda s, h, b: Response(b, status=s, headers=h))
        
        logger.info("Google Cloud Functions handler initialized")
    except ImportError:
        logger.error("Functions Framework not installed. Run 'pip install functions-framework' to deploy to GCP.")
        raise

# Vercel handler
elif SERVER_TYPE == "vercel":
    try:
        from fastapi.middleware.wsgi import WSGIMiddleware
        
        def vercel_handler(scope, receive, send):
            """Vercel handler for FastAPI app."""
            return app(scope, receive, send)
        
        logger.info("Vercel handler initialized")
    except ImportError:
        logger.error("Required dependencies not installed for Vercel deployment.")
        raise

else:
    logger.warning(f"Unknown or unspecified SERVER_TYPE: '{SERVER_TYPE}'. Using default handler.")
    
    # Default handler (will work for local development)
    def default_handler(scope, receive, send):
        """Default ASGI handler."""
        return app(scope, receive, send)
    
    # Export the app directly for ASGI servers
    handler = default_handler
    logger.info("Default handler initialized") 