"""Checkpointers for LangGraph

This package provides various checkpointer implementations for LangGraph.
"""

import os
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver

# Load environment variables
load_dotenv()

# Get the checkpointer type from environment variable
CHECKPOINTER_TYPE = os.getenv("CHECKPOINTER_TYPE", "memory").lower()

def get_checkpointer() -> BaseCheckpointSaver:
    """Get the appropriate checkpointer based on CHECKPOINTER_TYPE environment variable.
    
    Returns:
        A LangGraph checkpointer instance
    """
    if CHECKPOINTER_TYPE == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    
    elif CHECKPOINTER_TYPE == "redis":
        from .redis_checkpointer import RedisCheckpointer
        return RedisCheckpointer()
    
    else:
        # Default to memory saver
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

# Export the checkpointer classes
try:
    from .redis_checkpointer import RedisCheckpointer
except ImportError:
    pass

__all__ = ['RedisCheckpointer', 'get_checkpointer'] 