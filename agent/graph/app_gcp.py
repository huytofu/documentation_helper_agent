"""Google Cloud Run entry point.

This file serves as the entry point for deploying the application to Google Cloud Run.
It sets up the FastAPI app with the appropriate configuration and exposes it as a WSGI app
that can be directly used by Cloud Run.
"""

import os
import logging
import gunicorn.app.base
from dotenv import load_dotenv
from agent.graph.app import app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set server type for serverless handling
os.environ["SERVER_TYPE"] = "gcp"

# Gunicorn application for production deployment
class StandaloneApplication(gunicorn.app.base.BaseApplication):
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

# Main entry point
if __name__ == "__main__":
    # Get port from environment variable (Cloud Run sets this automatically)
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting server on port {port}")
    
    # In production, we use Gunicorn for better performance
    if os.getenv("ENVIRONMENT") == "production":
        # Configure Gunicorn
        options = {
            "bind": f"0.0.0.0:{port}",
            "workers": int(os.getenv("GUNICORN_WORKERS", "2")),
            "worker_class": "uvicorn.workers.UvicornWorker",
            "timeout": 120,
            "keepalive": 5,
            "errorlog": "-",
            "accesslog": "-",
            "loglevel": "info",
        }
        
        # Start Gunicorn server
        logger.info("Starting Gunicorn server with production settings")
        StandaloneApplication(app, options).run()
    else:
        # For local development/testing
        import uvicorn
        logger.info("Starting Uvicorn server with development settings")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info") 