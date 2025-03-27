"""Vercel KV Checkpointer for LangGraph

This module implements a LangGraph checkpointer using Vercel KV (Redis) for state persistence.
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List, Tuple
import asyncio
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class VercelKVCheckpointer(BaseCheckpointSaver):
    """LangGraph checkpointer implementation using Vercel KV (Redis).
    
    This checkpointer stores LangGraph state in Vercel KV, allowing for
    persistence across serverless function invocations.
    """
    
    def __init__(self, 
                 kv_url: Optional[str] = None, 
                 kv_rest_api_url: Optional[str] = None,
                 kv_rest_api_token: Optional[str] = None,
                 kv_rest_api_read_only_token: Optional[str] = None,
                 ttl: Optional[int] = None):
        """Initialize the Vercel KV checkpointer.
        
        Args:
            kv_url: Vercel KV Redis URL (KV_URL env var)
            kv_rest_api_url: Vercel KV REST API URL (KV_REST_API_URL env var)
            kv_rest_api_token: Vercel KV REST API token (KV_REST_API_TOKEN env var)
            kv_rest_api_read_only_token: Vercel KV REST API read-only token (KV_REST_API_READ_ONLY_TOKEN env var)
            ttl: Time-to-live for stored states in seconds (optional)
        """
        # Import here to avoid dependency issues if not using Vercel KV
        try:
            from vercel_kv import VercelKV
        except ImportError:
            raise ImportError(
                "The 'vercel-kv' package is required to use VercelKVCheckpointer. "
                "Install it with 'pip install vercel-kv'."
            )
        
        # Get credentials from parameters or environment variables
        self.kv_url = kv_url or os.getenv("KV_URL")
        self.kv_rest_api_url = kv_rest_api_url or os.getenv("KV_REST_API_URL")
        self.kv_rest_api_token = kv_rest_api_token or os.getenv("KV_REST_API_TOKEN")
        self.kv_rest_api_read_only_token = kv_rest_api_read_only_token or os.getenv("KV_REST_API_READ_ONLY_TOKEN")
        self.ttl = ttl
        
        # Validate credentials
        if not all([self.kv_url, self.kv_rest_api_url, self.kv_rest_api_token]):
            raise ValueError(
                "Vercel KV credentials are required. "
                "Set KV_URL, KV_REST_API_URL, and KV_REST_API_TOKEN environment variables "
                "or provide them as parameters."
            )
        
        # Initialize Vercel KV client
        self.kv = VercelKV()
        logger.info("Initialized Vercel KV checkpointer")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a state from Vercel KV.
        
        Args:
            key: The state key to retrieve
            
        Returns:
            The state dictionary if found, None otherwise
        """
        try:
            logger.debug(f"Getting state for key: {key}")
            state_json = await self.kv.get(key)
            if state_json is None:
                logger.debug(f"No state found for key: {key}")
                return None
            
            state = json.loads(state_json)
            logger.debug(f"Retrieved state for key: {key}")
            return state
        except Exception as e:
            logger.error(f"Error getting state for key {key}: {str(e)}")
            return None
    
    async def put(self, key: str, state: Dict[str, Any]) -> None:
        """Store a state in Vercel KV.
        
        Args:
            key: The state key
            state: The state dictionary to store
        """
        try:
            logger.debug(f"Storing state for key: {key}")
            state_json = json.dumps(state)
            
            if self.ttl:
                await self.kv.set(key, state_json, ex=self.ttl)
            else:
                await self.kv.set(key, state_json)
                
            logger.debug(f"Stored state for key: {key}")
        except Exception as e:
            logger.error(f"Error storing state for key {key}: {str(e)}")
            raise
    
    async def list(self) -> List[str]:
        """List all state keys in Vercel KV.
        
        Returns:
            List of state keys
        """
        try:
            logger.debug("Listing all state keys")
            # Vercel KV doesn't have a direct method to list all keys
            # This is a workaround using the KEYS command
            # Note: This is not recommended for production with large datasets
            keys = await self.kv.execute_command("KEYS", "*")
            logger.debug(f"Found {len(keys)} state keys")
            return keys
        except Exception as e:
            logger.error(f"Error listing state keys: {str(e)}")
            return []
    
    async def delete(self, key: str) -> None:
        """Delete a state from Vercel KV.
        
        Args:
            key: The state key to delete
        """
        try:
            logger.debug(f"Deleting state for key: {key}")
            await self.kv.delete(key)
            logger.debug(f"Deleted state for key: {key}")
        except Exception as e:
            logger.error(f"Error deleting state for key {key}: {str(e)}")
            raise 