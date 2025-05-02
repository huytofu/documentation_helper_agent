"""Redis Checkpointer for LangGraph

This module implements a LangGraph checkpointer using Redis for state persistence.
"""

import os
import json
import logging
import uuid
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

def _generate_new_checkpoint_id() -> str:
    """Generate a new unique checkpoint ID."""
    return str(uuid.uuid4())

def _make_redis_checkpoint_key(thread_id: str, checkpoint_ns: str, checkpoint_id: Optional[str]) -> str:
    """Make a Redis checkpoint key.
    
    Args:
        thread_id: The thread ID
        checkpoint_ns: The checkpoint namespace
        checkpoint_id: The checkpoint ID (can be None for new conversations)
        
    Returns:
        A Redis key string
    """
    # If checkpoint_id is None, generate a new one
    if checkpoint_id is None:
        checkpoint_id = _generate_new_checkpoint_id()
    return REDIS_KEY_SEPARATOR.join(["checkpoint", thread_id, checkpoint_ns, checkpoint_id])

def _parse_redis_checkpoint_key(redis_key: str) -> dict:
    try:
        # Ensure redis_key is a string
        if isinstance(redis_key, bytes):
            redis_key = redis_key.decode()
        
        parts = redis_key.split(REDIS_KEY_SEPARATOR)
        if len(parts) != 4:
            logger.error(f"Invalid Redis key format: {redis_key}")
            return {
                "thread_id": "",
                "checkpoint_ns": "",
                "checkpoint_id": "",
            }
            
        namespace, thread_id, checkpoint_ns, checkpoint_id = parts
        if namespace != "checkpoint":
            logger.error(f"Expected checkpoint key to start with 'checkpoint', got: {namespace}")
            return {
                "thread_id": "",
                "checkpoint_ns": "",
                "checkpoint_id": "",
            }
            
        return {
            "thread_id": thread_id or "",
            "checkpoint_ns": checkpoint_ns or "",
            "checkpoint_id": checkpoint_id or "",
        }
    except Exception as e:
        logger.error(f"Error parsing Redis key {redis_key}: {str(e)}")
        return {
            "thread_id": "",
            "checkpoint_ns": "",
            "checkpoint_id": "",
        }

def _parse_redis_checkpoint_data(serde: SerializerProtocol, key: str, data: dict) -> Optional[CheckpointTuple]:
    if not data:
        logger.debug(f"No data found for key: {key}")
        return None
        
    try:
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
        
        # Log the raw data for debugging
        logger.debug(f"Raw data for key {key}: {data}")
        
        # Extract and validate required fields
        checkpoint_type = data.get(b"type")
        checkpoint_data = data.get(b"checkpoint")
        metadata = data.get(b"metadata")
        parent_checkpoint_id = data.get(b"parent_checkpoint_id")
        
        # Log extracted values
        logger.debug(f"Extracted values - type: {checkpoint_type}, data: {checkpoint_data}, metadata: {metadata}, parent_id: {parent_checkpoint_id}")
        
        if not checkpoint_type or not checkpoint_data:
            logger.error(f"Missing required checkpoint data for key: {key}")
            return None
            
        # Handle parent_checkpoint_id safely
        parent_checkpoint_id_str = ""
        if parent_checkpoint_id is not None:
            try:
                parent_checkpoint_id_str = parent_checkpoint_id.decode()
            except (AttributeError, UnicodeDecodeError) as e:
                logger.warning(f"Error decoding parent_checkpoint_id: {e}")
                parent_checkpoint_id_str = ""
        
        # Parse checkpoint and metadata
        try:
            checkpoint = serde.loads_typed((checkpoint_type.decode(), checkpoint_data))
            
            # Ensure metadata has the required structure
            metadata_dict = {"writes": {}}
            if metadata is not None:
                try:
                    parsed_metadata = serde.loads(metadata.decode())
                    if isinstance(parsed_metadata, dict):
                        # Preserve existing metadata but ensure 'writes' exists
                        metadata_dict.update(parsed_metadata)
                        if "writes" not in metadata_dict:
                            metadata_dict["writes"] = {}
                except (AttributeError, UnicodeDecodeError) as e:
                    logger.warning(f"Error decoding metadata: {e}")
            
            # Create parent config only if we have a valid parent_checkpoint_id
            parent_config = None
            if parent_checkpoint_id_str:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id_str,
                    }
                }
            
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata_dict,
                parent_config=parent_config,
                pending_writes=None,
            )
        except Exception as e:
            logger.error(f"Error parsing checkpoint data: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error in _parse_redis_checkpoint_data for key {key}: {str(e)}")
        return None

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
            
            # Get the current checkpoint_id from config (could be None for new conversations)
            current_checkpoint_id = config["configurable"].get("checkpoint_id")
            
            # For new checkpoints, use the ID from the checkpoint object
            # For resumed conversations, use the existing checkpoint_id
            checkpoint_id = current_checkpoint_id if current_checkpoint_id else checkpoint["id"]
            
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            serialized_metadata = self.serde.dumps(metadata)
            data = {
                "checkpoint": serialized_checkpoint,
                "type": type_,
                "metadata": serialized_metadata,
                "parent_checkpoint_id": current_checkpoint_id if current_checkpoint_id else "",
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
            
            # Get the current checkpoint_id from config (could be None for new conversations)
            current_checkpoint_id = config["configurable"].get("checkpoint_id")
            
            # For new checkpoints, use the ID from the checkpoint object
            # For resumed conversations, use the existing checkpoint_id
            checkpoint_id = current_checkpoint_id if current_checkpoint_id else checkpoint["id"]
            
            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            serialized_metadata = self.serde.dumps(metadata)
            data = {
                "checkpoint": serialized_checkpoint,
                "type": type_,
                "metadata": serialized_metadata,
                "parent_checkpoint_id": current_checkpoint_id if current_checkpoint_id else "",
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