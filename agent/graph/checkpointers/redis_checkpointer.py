"""Redis Checkpointer for LangGraph

This module implements a LangGraph checkpointer using Redis for state persistence.
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List, Tuple, Iterator
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, get_checkpoint_id
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_core.runnables import RunnableConfig

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

REDIS_KEY_SEPARATOR = "$"

# Utility functions for key construction and parsing

def _make_redis_checkpoint_key(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
    return REDIS_KEY_SEPARATOR.join(["checkpoint", thread_id, checkpoint_ns, checkpoint_id])

def _parse_redis_checkpoint_key(redis_key: str) -> dict:
    namespace, thread_id, checkpoint_ns, checkpoint_id = redis_key.split(REDIS_KEY_SEPARATOR)
    if namespace != "checkpoint":
        raise ValueError("Expected checkpoint key to start with 'checkpoint'")
    return {
        "thread_id": thread_id,
        "checkpoint_ns": checkpoint_ns,
        "checkpoint_id": checkpoint_id,
    }

def _parse_redis_checkpoint_data(serde: SerializerProtocol, key: str, data: dict) -> Optional[CheckpointTuple]:
    if not data:
        return None
    parsed_key = _parse_redis_checkpoint_key(key)
    thread_id = parsed_key["thread_id"]
    checkpoint_ns = parsed_key["checkpoint_ns"]
    checkpoint_id = parsed_key["checkpoint_id"]
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint_id,
        }
    }
    checkpoint = serde.loads_typed((data[b"type"].decode(), data[b"checkpoint"]))
    metadata = serde.loads(data[b"metadata"].decode())
    parent_checkpoint_id = data.get(b"parent_checkpoint_id", b"").decode()
    parent_config = (
        {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": parent_checkpoint_id,
            }
        }
        if parent_checkpoint_id else None
    )
    return CheckpointTuple(
        config=config,
        checkpoint=checkpoint,
        metadata=metadata,
        parent_config=parent_config,
        pending_writes=None,
    )

class RedisCheckpointer(BaseCheckpointSaver):
    """LangGraph checkpointer implementation using Redis (sync and async)."""
    def __init__(self, redis_url: Optional[str] = None, ttl: Optional[int] = None, serde: Optional[SerializerProtocol] = None):
        super().__init__()
        try:
            import redis
            if not hasattr(redis, 'asyncio'):
                raise ImportError("The installed redis package doesn't support asyncio")
            self.redis_module = redis
            self.async_redis_module = redis.asyncio
        except ImportError:
            raise ImportError(
                "Redis asyncio support is required. Make sure you have redis>=4.2.0 installed via 'pip install redis>=4.2.0'."
            )
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.ttl = ttl
        if not self.redis_url:
            raise ValueError("Redis URL is required. Set REDIS_URL environment variable or provide it as a parameter.")
        self.redis = self.redis_module.from_url(self.redis_url)
        self.async_redis = self.async_redis_module.from_url(self.redis_url)
        self.serde = serde or JsonPlusSerializer()
        logger.info("Initialized Redis checkpointer")

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_id = get_checkpoint_id(config)
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
            data = self.redis.hgetall(key)
            if not data:
                logger.warning(f"No checkpoint data found for key: {key}")
                return None
            return _parse_redis_checkpoint_data(self.serde, key, data)
        except Exception as e:
            logger.error(f"Error in get_tuple: {e}")
            return None

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_id = get_checkpoint_id(config)
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
            data = await self.async_redis.hgetall(key)
            if not data:
                logger.warning(f"No checkpoint data found for key: {key}")
                return None
            return _parse_redis_checkpoint_data(self.serde, key, data)
        except Exception as e:
            logger.error(f"Error in aget_tuple: {e}")
            return None

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
    
    async def put(self, config: RunnableConfig, checkpoint: Any, metadata: Any, new_versions: Any) -> RunnableConfig:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = checkpoint["id"]
            parent_checkpoint_id = config["configurable"].get("checkpoint_id")
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            serialized_metadata = self.serde.dumps(metadata)
            data = {
                "checkpoint": serialized_checkpoint,
                "type": type_,
                "metadata": serialized_metadata,
                "parent_checkpoint_id": parent_checkpoint_id if parent_checkpoint_id else "",
            }
            self.redis.hset(key, mapping=data)
            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }
        except Exception as e:
            logger.error(f"Error in put: {e}")
            raise

    async def aput(self, config: RunnableConfig, checkpoint: Any, metadata: Any, new_versions: Any) -> RunnableConfig:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = checkpoint["id"]
            parent_checkpoint_id = config["configurable"].get("checkpoint_id")
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            serialized_metadata = self.serde.dumps(metadata)
            data = {
                "checkpoint": serialized_checkpoint,
                "type": type_,
                "metadata": serialized_metadata,
                "parent_checkpoint_id": parent_checkpoint_id if parent_checkpoint_id else "",
            }
            await self.async_redis.hset(key, mapping=data)
            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }
        except Exception as e:
            logger.error(f"Error in aput: {e}")
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

    def put_writes(self, config: RunnableConfig, writes: List[Tuple[str, Any]], task_id: str) -> None:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = config["configurable"]["checkpoint_id"]
            for idx, (channel, value) in enumerate(writes):
                key = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}${task_id}${idx}"
                type_, serialized_value = self.serde.dumps_typed(value)
                data = {"channel": channel, "type": type_, "value": serialized_value}
                self.redis.hset(key, mapping=data)
        except Exception as e:
            logger.error(f"Error in put_writes: {e}")
            raise

    async def aput_writes(self, config: RunnableConfig, writes: List[Tuple[str, Any]], task_id: str) -> None:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = config["configurable"]["checkpoint_id"]
            for idx, (channel, value) in enumerate(writes):
                key = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}${task_id}${idx}"
                type_, serialized_value = self.serde.dumps_typed(value)
                data = {"channel": channel, "type": type_, "value": serialized_value}
                await self.async_redis.hset(key, mapping=data)
        except Exception as e:
            logger.error(f"Error in aput_writes: {e}")
            raise

    def list(self, config: Optional[RunnableConfig], filter: Optional[dict] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        try:
            if config is None:
                return iter([])
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            pattern = _make_redis_checkpoint_key(thread_id, checkpoint_ns, "*")
            keys = self.redis.keys(pattern)
            keys = sorted(keys, key=lambda k: _parse_redis_checkpoint_key(k.decode())["checkpoint_id"], reverse=True)
            if limit:
                keys = keys[:limit]
            for key in keys:
                data = self.redis.hgetall(key)
                if data and b"checkpoint" in data and b"metadata" in data:
                    yield _parse_redis_checkpoint_data(self.serde, key.decode(), data)
        except Exception as e:
            logger.error(f"Error in list: {e}")
            return iter([])

    async def alist(self, config: Optional[RunnableConfig], filter: Optional[dict] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None):
        try:
            if config is None:
                return
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            pattern = _make_redis_checkpoint_key(thread_id, checkpoint_ns, "*")
            keys = await self.async_redis.keys(pattern)
            keys = sorted(keys, key=lambda k: _parse_redis_checkpoint_key(k.decode())["checkpoint_id"], reverse=True)
            if limit:
                keys = keys[:limit]
            for key in keys:
                data = await self.async_redis.hgetall(key)
                if data and b"checkpoint" in data and b"metadata" in data:
                    yield _parse_redis_checkpoint_data(self.serde, key.decode(), data)
        except Exception as e:
            logger.error(f"Error in alist: {e}")
            return 