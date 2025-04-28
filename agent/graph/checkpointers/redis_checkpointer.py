"""Redis Checkpointer for LangGraph

This module implements a LangGraph checkpointer using Redis for state persistence.
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class RedisCheckpointer(BaseCheckpointSaver):
    """LangGraph checkpointer implementation using Redis.
    
    This checkpointer stores LangGraph state in Redis, allowing for
    persistence across serverless function invocations.
    """
    
    def __init__(self, 
                 redis_url: Optional[str] = None,
                 ttl: Optional[int] = None):
        """Initialize the Redis checkpointer.
        
        Args:
            redis_url: Redis URL (REDIS_URL env var)
            ttl: Time-to-live for stored states in seconds (optional)
        """
        # Import here to avoid dependency issues if not using Redis
        try:
            # Try importing the async Redis client
            import redis
            # Check if the package supports asyncio
            if not hasattr(redis, 'asyncio'):
                raise ImportError("The installed redis package doesn't support asyncio")
            self.redis_module = redis.asyncio
        except ImportError:
            raise ImportError(
                "Redis asyncio support is required. "
                "Make sure you have redis>=4.2.0 installed via 'pip install redis>=4.2.0'."
            )
        
        # Get Redis URL from parameter or environment variable
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.ttl = ttl
        
        # Validate Redis URL
        if not self.redis_url:
            raise ValueError(
                "Redis URL is required. "
                "Set REDIS_URL environment variable or provide it as a parameter."
            )
        
        # Initialize Redis client
        self.redis = self.redis_module.from_url(self.redis_url)
        logger.info("Initialized Redis checkpointer")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a state from Redis.
        
        Args:
            key: The state key to retrieve
            
        Returns:
            The state dictionary if found, None otherwise
        """
        try:
            logger.debug(f"Getting state for key: {key}")
            state_json = await self.redis.get(key)
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
        """Store a state in Redis.
        
        Args:
            key: The state key
            state: The state dictionary to store
        """
        try:
            logger.debug(f"Storing state for key: {key}")
            state_json = json.dumps(state)
            
            if self.ttl:
                await self.redis.setex(key, self.ttl, state_json)
            else:
                await self.redis.set(key, state_json)
                
            logger.debug(f"Stored state for key: {key}")
        except Exception as e:
            logger.error(f"Error storing state for key {key}: {str(e)}")
            raise
    
    async def list(self) -> List[str]:
        """List all state keys in Redis.
        
        Returns:
            List of state keys
        """
        try:
            logger.debug("Listing all state keys")
            # Warning: KEYS is not recommended for production with large datasets
            # Consider using SCAN for production environments
            keys = await self.redis.keys("*")
            logger.debug(f"Found {len(keys)} state keys")
            return keys
        except Exception as e:
            logger.error(f"Error listing state keys: {str(e)}")
            return []
    
    async def delete(self, key: str) -> None:
        """Delete a state from Redis.
        
        Args:
            key: The state key to delete
        """
        try:
            logger.debug(f"Deleting state for key: {key}")
            await self.redis.delete(key)
            logger.debug(f"Deleted state for key: {key}")
        except Exception as e:
            logger.error(f"Error deleting state for key {key}: {str(e)}")
            raise

    async def aget_tuple(self, config):
        """
        Retrieve a tuple (state, version) for the given config.
        The version is set to None by default unless your state includes a 'version' key.
        """
        # You may need to adjust this key logic based on your usage
        key = str(config)
        state = await self.get(key)
        version = state.get("version") if state and isinstance(state, dict) and "version" in state else None
        return (state, version) 