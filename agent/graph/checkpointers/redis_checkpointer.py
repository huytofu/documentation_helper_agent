"""Redis Checkpointer for LangGraph

This module implements a LangGraph checkpointer using Redis for state persistence.
"""

import os
import json
import logging
import uuid
from typing import Any, Dict, Optional, List, Tuple, Iterator, Sequence
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, get_checkpoint_id, get_checkpoint_metadata
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_core.runnables import RunnableConfig

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

REDIS_KEY_SEPARATOR = "$"
WRITES_IDX_MAP = {}  # Channel to index mapping, similar to MemorySaver

# Utility functions for key construction and parsing

def _generate_new_checkpoint_id() -> str:
    """Generate a new unique checkpoint ID."""
    return str(uuid.uuid4())

def _make_redis_checkpoint_key(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
    """Make a Redis checkpoint key for a concrete checkpoint id (or '*' for SCAN)."""
    if checkpoint_id is None:
        raise ValueError("checkpoint_id is required to build a Redis checkpoint key")
    return REDIS_KEY_SEPARATOR.join(["checkpoint", thread_id, checkpoint_ns, checkpoint_id])


def _checkpoint_key_pattern(thread_id: str, checkpoint_ns: str) -> str:
    """Pattern that matches all checkpoints for a thread/namespace."""
    return _make_redis_checkpoint_key(thread_id, checkpoint_ns, "*")


def _as_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _load_pending_writes(
    redis_client: Any,
    serde: SerializerProtocol,
    thread_id: str,
    checkpoint_ns: str,
    checkpoint_id: str,
) -> List[Tuple[str, str, Any]]:
    """Load pending writes for a checkpoint as (task_id, channel, value) tuples."""
    writes_pattern = (
        f"writes{REDIS_KEY_SEPARATOR}{thread_id}{REDIS_KEY_SEPARATOR}"
        f"{checkpoint_ns}{REDIS_KEY_SEPARATOR}{checkpoint_id}{REDIS_KEY_SEPARATOR}*"
    )
    write_keys = redis_client.keys(writes_pattern)
    pending_writes: List[Tuple[str, str, Any]] = []
    for write_key in write_keys:
        write_data = redis_client.hgetall(write_key)
        if not write_data:
            continue
        try:
            channel = _as_str(write_data.get(b"channel") or write_data.get("channel"))
            task_id = _as_str(write_data.get(b"task_id") or write_data.get("task_id") or "")
            value_type = write_data.get(b"type") or write_data.get("type")
            value_blob = write_data.get(b"value") or write_data.get("value")
            if value_type is None or value_blob is None:
                continue
            value = serde.loads_typed((_as_str(value_type), value_blob))
            pending_writes.append((task_id, channel, value))
        except Exception as exc:
            logger.warning(f"Skipping corrupt write key {write_key}: {exc}")
    return pending_writes


async def _aload_pending_writes(
    redis_client: Any,
    serde: SerializerProtocol,
    thread_id: str,
    checkpoint_ns: str,
    checkpoint_id: str,
) -> List[Tuple[str, str, Any]]:
    """Async variant of pending-write loader."""
    writes_pattern = (
        f"writes{REDIS_KEY_SEPARATOR}{thread_id}{REDIS_KEY_SEPARATOR}"
        f"{checkpoint_ns}{REDIS_KEY_SEPARATOR}{checkpoint_id}{REDIS_KEY_SEPARATOR}*"
    )
    write_keys = await redis_client.keys(writes_pattern)
    pending_writes: List[Tuple[str, str, Any]] = []
    for write_key in write_keys:
        write_data = await redis_client.hgetall(write_key)
        if not write_data:
            continue
        try:
            channel = _as_str(write_data.get(b"channel") or write_data.get("channel"))
            task_id = _as_str(write_data.get(b"task_id") or write_data.get("task_id") or "")
            value_type = write_data.get(b"type") or write_data.get("type")
            value_blob = write_data.get(b"value") or write_data.get("value")
            if value_type is None or value_blob is None:
                continue
            value = serde.loads_typed((_as_str(value_type), value_blob))
            pending_writes.append((task_id, channel, value))
        except Exception as exc:
            logger.warning(f"Skipping corrupt write key {write_key}: {exc}")
    return pending_writes


def _serialize_metadata(serde: SerializerProtocol, config: RunnableConfig, metadata: Any) -> Tuple[bytes, bytes]:
    """Serialize checkpoint metadata as (type, blob) for Redis hash fields."""
    meta_type, meta_blob = serde.dumps_typed(get_checkpoint_metadata(config, metadata))
    return (
        meta_type.encode() if isinstance(meta_type, str) else bytes(meta_type),
        meta_blob if isinstance(meta_blob, bytes) else str(meta_blob).encode(),
    )


def _deserialize_metadata(serde: SerializerProtocol, data: dict) -> dict:
    """Deserialize metadata from Redis hash fields; never return None."""
    meta_type = data.get(b"metadata_type") or data.get("metadata_type")
    meta_blob = data.get(b"metadata") or data.get("metadata")
    if meta_type is not None and meta_blob is not None:
        try:
            parsed = serde.loads_typed((_as_str(meta_type), meta_blob))
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning(f"Error decoding typed metadata: {exc}")
    # Backward-compat: older rows stored a stringified dumps_typed tuple
    if meta_blob is not None:
        try:
            raw = _as_str(meta_blob)
            # Attempt loads_typed if it was stored as "('type', b'...')" is hopeless;
            # prefer empty dict over crashing CopilotKit final sync.
            if raw.startswith("{"):
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            pass
    return {}

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

def _parse_redis_checkpoint_data(
    serde: SerializerProtocol,
    key: str,
    data: dict,
    pending_writes: Optional[List[Tuple[str, str, Any]]] = None,
) -> Optional[CheckpointTuple]:
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

        checkpoint_type = data.get(b"type") or data.get("type")
        checkpoint_data = data.get(b"checkpoint") or data.get("checkpoint")
        parent_checkpoint_id = data.get(b"parent_checkpoint_id") or data.get("parent_checkpoint_id")

        if not checkpoint_type or not checkpoint_data:
            logger.error(f"Missing required checkpoint data for key: {key}")
            return None

        parent_checkpoint_id_str = _as_str(parent_checkpoint_id) if parent_checkpoint_id else ""

        try:
            checkpoint = serde.loads_typed((_as_str(checkpoint_type), checkpoint_data))
            metadata_dict = _deserialize_metadata(serde, data)

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
                pending_writes=pending_writes or [],
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

    def _latest_checkpoint_key(self, thread_id: str, checkpoint_ns: str) -> Optional[str]:
        """Return the lexicographically latest checkpoint key for a thread."""
        pattern = _checkpoint_key_pattern(thread_id, checkpoint_ns)
        keys = self.redis.keys(pattern)
        if not keys:
            return None
        keys = sorted(
            keys,
            key=lambda k: _parse_redis_checkpoint_key(_as_str(k))["checkpoint_id"],
            reverse=True,
        )
        return _as_str(keys[0])

    async def _alatest_checkpoint_key(self, thread_id: str, checkpoint_ns: str) -> Optional[str]:
        """Async: return the lexicographically latest checkpoint key for a thread."""
        pattern = _checkpoint_key_pattern(thread_id, checkpoint_ns)
        keys = await self.async_redis.keys(pattern)
        if not keys:
            return None
        keys = sorted(
            keys,
            key=lambda k: _parse_redis_checkpoint_key(_as_str(k))["checkpoint_id"],
            reverse=True,
        )
        return _as_str(keys[0])

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_id = get_checkpoint_id(config)
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

            if checkpoint_id:
                key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
            else:
                # CopilotKit / LangGraph call get without checkpoint_id to read "latest".
                # Never invent a new UUID here — that made every lookup miss.
                key = self._latest_checkpoint_key(thread_id, checkpoint_ns)
                if not key:
                    logger.debug(
                        f"No checkpoints found for thread_id={thread_id} ns={checkpoint_ns!r}"
                    )
                    return None
                checkpoint_id = _parse_redis_checkpoint_key(key)["checkpoint_id"]

            logger.debug(f"Attempting to get checkpoint data for key: {key}")
            data = self.redis.hgetall(key)
            if not data:
                logger.debug(f"No checkpoint data found for key: {key}")
                return None

            pending_writes = _load_pending_writes(
                self.redis, self.serde, thread_id, checkpoint_ns, checkpoint_id
            )
            return _parse_redis_checkpoint_data(self.serde, key, data, pending_writes)
        except Exception as e:
            logger.error(f"Error in get_tuple: {e}")
            return None

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_id = get_checkpoint_id(config)
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

            if checkpoint_id:
                key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
            else:
                key = await self._alatest_checkpoint_key(thread_id, checkpoint_ns)
                if not key:
                    logger.debug(
                        f"No checkpoints found for thread_id={thread_id} ns={checkpoint_ns!r}"
                    )
                    return None
                checkpoint_id = _parse_redis_checkpoint_key(key)["checkpoint_id"]

            logger.debug(f"Attempting to get checkpoint data for key: {key}")
            data = await self.async_redis.hgetall(key)
            if not data:
                logger.debug(f"No checkpoint data found for key: {key}")
                return None

            pending_writes = await _aload_pending_writes(
                self.async_redis, self.serde, thread_id, checkpoint_ns, checkpoint_id
            )
            return _parse_redis_checkpoint_data(self.serde, key, data, pending_writes)
        except Exception as e:
            logger.error(f"Error in aget_tuple: {e}")
            return None

    def put(self, config: RunnableConfig, checkpoint: Any, metadata: Any, new_versions: Any) -> RunnableConfig:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            current_checkpoint_id = config["configurable"].get("checkpoint_id")
            checkpoint_id = checkpoint["id"]

            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            meta_type, meta_blob = _serialize_metadata(self.serde, config, metadata)

            data = {
                b"checkpoint": serialized_checkpoint if isinstance(serialized_checkpoint, bytes) else str(serialized_checkpoint).encode(),
                b"type": type_.encode() if isinstance(type_, str) else str(type_).encode(),
                b"metadata_type": meta_type,
                b"metadata": meta_blob,
                b"parent_checkpoint_id": (current_checkpoint_id or "").encode(),
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
            current_checkpoint_id = config["configurable"].get("checkpoint_id")
            # Always persist under the new checkpoint id (parent is current_checkpoint_id).
            checkpoint_id = checkpoint["id"]

            key = _make_redis_checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)

            type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
            meta_type, meta_blob = _serialize_metadata(self.serde, config, metadata)

            data = {
                b"checkpoint": serialized_checkpoint if isinstance(serialized_checkpoint, bytes) else str(serialized_checkpoint).encode(),
                b"type": type_.encode() if isinstance(type_, str) else str(type_).encode(),
                b"metadata_type": meta_type,
                b"metadata": meta_blob,
                b"parent_checkpoint_id": (current_checkpoint_id or "").encode(),
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

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = config["configurable"]["checkpoint_id"]
            
            # Create outer key pattern for checking existing writes
            outer_key_pattern = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}*"
            existing_writes = self.redis.keys(outer_key_pattern)
            existing_write_map = {}
            
            # Create map of existing writes
            for write_key in existing_writes:
                write_data = self.redis.hgetall(write_key)
                if write_data:
                    channel = write_data[b"channel"].decode()
                    idx = int(write_key.split(REDIS_KEY_SEPARATOR)[-1])
                    existing_write_map[(task_id, WRITES_IDX_MAP.get(channel, idx))] = True
            
            # Process new writes
            for idx, (channel, value) in enumerate(writes):
                inner_key = (task_id, WRITES_IDX_MAP.get(channel, idx))
                
                # Skip if write already exists
                if inner_key[1] >= 0 and inner_key in existing_write_map:
                    continue
                
                # Create write key
                key = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}${task_id}${idx}"
                
                # Serialize value
                type_, serialized_value = self.serde.dumps_typed(value)
                
                # Store write data
                data = {
                    "channel": channel,
                    "type": type_,
                    "value": serialized_value,
                    "task_id": task_id,
                    "task_path": task_path
                }
                
                self.redis.hset(key, mapping=data)
                
        except Exception as e:
            logger.error(f"Error in put_writes: {e}")
            raise

    async def aput_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        try:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            checkpoint_id = config["configurable"]["checkpoint_id"]
            
            # Create outer key pattern for checking existing writes
            outer_key_pattern = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}*"
            existing_writes = await self.async_redis.keys(outer_key_pattern)
            existing_write_map = {}
            
            # Create map of existing writes
            for write_key in existing_writes:
                write_data = await self.async_redis.hgetall(write_key)
                if write_data:
                    channel = write_data[b"channel"].decode()
                    idx = int(write_key.split(REDIS_KEY_SEPARATOR)[-1])
                    existing_write_map[(task_id, WRITES_IDX_MAP.get(channel, idx))] = True
            
            # Process new writes
            for idx, (channel, value) in enumerate(writes):
                inner_key = (task_id, WRITES_IDX_MAP.get(channel, idx))
                
                # Skip if write already exists
                if inner_key[1] >= 0 and inner_key in existing_write_map:
                    continue
                
                # Create write key
                key = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}${task_id}${idx}"
                
                # Serialize value
                type_, serialized_value = self.serde.dumps_typed(value)
                
                # Store write data
                data = {
                    "channel": channel,
                    "type": type_,
                    "value": serialized_value,
                    "task_id": task_id,
                    "task_path": task_path
                }
                
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
            config_checkpoint_id = get_checkpoint_id(config)
            pattern = _checkpoint_key_pattern(thread_id, checkpoint_ns)
            keys = self.redis.keys(pattern)
            keys = sorted(keys, key=lambda k: _parse_redis_checkpoint_key(k.decode())["checkpoint_id"], reverse=True)
            
            if limit:
                keys = keys[:limit]
                
            for key in keys:
                data = self.redis.hgetall(key)
                if not data or b"checkpoint" not in data or b"metadata" not in data:
                    continue
                    
                parsed_key = _parse_redis_checkpoint_key(key.decode())
                checkpoint_id = parsed_key["checkpoint_id"]
                
                # Filter by checkpoint ID from config
                if config_checkpoint_id and checkpoint_id != config_checkpoint_id:
                    continue
                    
                # Filter by checkpoint ID from `before` config
                if before and (before_checkpoint_id := get_checkpoint_id(before)) and checkpoint_id >= before_checkpoint_id:
                    continue
                    
                # Parse metadata using loads_typed
                metadata = self.serde.loads_typed(data[b"metadata"].decode())
                
                # Filter by metadata
                if filter and not all(
                    query_value == metadata.get(query_key)
                    for query_key, query_value in filter.items()
                ):
                    continue
                    
                # Get writes for this checkpoint
                writes_pattern = f"writes${thread_id}${checkpoint_ns}${checkpoint_id}*"
                write_keys = self.redis.keys(writes_pattern)
                writes = []
                for write_key in write_keys:
                    write_data = self.redis.hgetall(write_key)
                    if write_data:
                        channel = write_data[b"channel"].decode()
                        value = self.serde.loads_typed(write_data[b"value"].decode())
                        writes.append((channel, value))
                        
                # Get parent checkpoint ID
                parent_checkpoint_id = data.get(b"parent_checkpoint_id")
                if parent_checkpoint_id:
                    parent_checkpoint_id = parent_checkpoint_id.decode()
                    
                # Parse checkpoint
                checkpoint_type = data[b"type"].decode()
                checkpoint_data = data[b"checkpoint"]
                checkpoint = self.serde.loads_typed((checkpoint_type, checkpoint_data))
                
                # Create parent config if parent_checkpoint_id exists
                parent_config = None
                if parent_checkpoint_id:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config,
                    pending_writes=writes,
                )
                
        except Exception as e:
            logger.error(f"Error in list: {e}")
            return iter([])

    async def alist(self, config: Optional[RunnableConfig], filter: Optional[dict] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None):
        try:
            if config is None:
                return
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            pattern = _checkpoint_key_pattern(thread_id, checkpoint_ns)
            keys = await self.async_redis.keys(pattern)
            keys = sorted(
                keys,
                key=lambda k: _parse_redis_checkpoint_key(_as_str(k))["checkpoint_id"],
                reverse=True,
            )
            if limit:
                keys = keys[:limit]
            for key in keys:
                key_str = _as_str(key)
                data = await self.async_redis.hgetall(key)
                if data and (b"checkpoint" in data or "checkpoint" in data):
                    checkpoint_id = _parse_redis_checkpoint_key(key_str)["checkpoint_id"]
                    pending_writes = await _aload_pending_writes(
                        self.async_redis, self.serde, thread_id, checkpoint_ns, checkpoint_id
                    )
                    parsed = _parse_redis_checkpoint_data(
                        self.serde, key_str, data, pending_writes
                    )
                    if parsed is not None:
                        yield parsed
        except Exception as e:
            logger.error(f"Error in alist: {e}")
            return 