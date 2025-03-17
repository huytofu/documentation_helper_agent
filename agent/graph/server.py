"""Server Startup Module

This module handles starting the uvicorn server for local development.
It will only start the server if SERVER_TYPE is set to 'local' or not set.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import logging
import uvicorn

# Get logger for this module
logger = logging.getLogger(__name__)

def configure_logging():
    """Configure logging for the server."""
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
    
    return log_config

def start_server():
    """Start the uvicorn server."""
    # Check if we should start the server based on SERVER_TYPE
    server_type = os.getenv("SERVER_TYPE", "local").lower()
    
    if server_type != "local" and server_type:
        logger.info(f"SERVER_TYPE is set to '{server_type}', not starting local server")
        logger.info("To start the local server, set SERVER_TYPE to 'local' or leave it unset")
        return
    
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting local server on port {port}")
    
    log_config = configure_logging()
    
    logger.info("Starting uvicorn server with logging configuration")
    uvicorn.run(
        "agent.graph.app:app",
        host="0.0.0.0",
        port=port,
        log_config=log_config,
    )

if __name__ == "__main__":
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        force=True
    )
    start_server() 