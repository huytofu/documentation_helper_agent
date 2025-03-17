"""ASGI Application Entry Point

This module exports the FastAPI application for ASGI servers like Uvicorn, Hypercorn, or Daphne.
"""

import logging
from agent.graph.app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("ASGI application initialized and ready to serve")

# Export the application
application = app 