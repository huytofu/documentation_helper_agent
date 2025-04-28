"""Serverless Handler Module

This module provides handler functions for various serverless platforms based on
the SERVER_TYPE environment variable.

Usage:
    Set the SERVER_TYPE environment variable to one of the following values:
    - "aws lambda" - For AWS Lambda deployment
    - "vercel" - For Vercel deployment
    - "gcp" - For Google Cloud Run deployment
    
    Example:
    ```
    # In your .env file
    SERVER_TYPE=gcp
    
    # Or set it directly in your environment
    export SERVER_TYPE="gcp"
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

# Google Cloud Run handler
elif SERVER_TYPE == "gcp":
    # For Google Cloud Run, we can use the app directly
    # Cloud Run automatically looks for a variable named "app" that's a WSGI/ASGI app
    # No special adapter needed, but we'll provide some configuration
    
    import uvicorn
    from gunicorn.app.base import BaseApplication
    
    class StandaloneApplication(BaseApplication):
        """Gunicorn application for Google Cloud Run."""
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()
            
        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)
                    
        def load(self):
            return self.application
    
    def gcp_handler():
        """Initialize app for Google Cloud Run.
        
        This handler is not used directly but is here to document the setup.
        For GCP, we export the 'app' variable which is picked up automatically.
        """
        port = int(os.getenv("PORT", "8080"))
        
        # Configuration for production
        if os.getenv("ENVIRONMENT") == "production":
            options = {
                "bind": f"0.0.0.0:{port}",
                "workers": int(os.getenv("GUNICORN_WORKERS", "1")),
                "worker_class": "uvicorn.workers.UvicornWorker",
                "timeout": 120,
                "keepalive": 5,
                "errorlog": "-",
                "accesslog": "-",
            }
            
            StandaloneApplication(app, options).run()
        else:
            # For local development
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    
    # For Cloud Run, we just need to expose the app
    # The actual server configuration will be in app_gcp.py
    handler = app
    logger.info("Google Cloud Run handler initialized")

else:
    logger.warning(f"Unknown or unspecified SERVER_TYPE: '{SERVER_TYPE}'. Using default handler.")
    
    # Default handler (will work for local development)
    def default_handler(scope, receive, send):
        """Default ASGI handler."""
        return app(scope, receive, send)
    
    # Export the app directly for ASGI servers
    handler = default_handler
    logger.info("Default handler initialized") 