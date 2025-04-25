"""Serverless Handler Module

This module provides handler functions for various serverless platforms based on
the SERVER_TYPE environment variable.

Usage:
    Set the SERVER_TYPE environment variable to one of the following values:
    - "aws lambda" - For AWS Lambda deployment
    - "vercel" - For Vercel deployment
    
    Example:
    ```
    # In your .env file
    SERVER_TYPE=vercel
    
    # Or set it directly in your environment
    export SERVER_TYPE="vercel"
    ```
    
    The module will automatically load the appropriate adapter for the specified platform.
    If SERVER_TYPE is not set or is set to an unknown value, a default handler will be used.
"""

import os
import logging
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

# Vercel handler
elif SERVER_TYPE == "vercel":
    try:
        def vercel_handler(scope, receive, send):
            """Vercel handler for FastAPI app."""
            return app(scope, receive, send)
        
        handler = vercel_handler
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