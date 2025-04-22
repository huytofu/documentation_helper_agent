"""Checkpointers for LangGraph

This package provides various checkpointer implementations for LangGraph.
"""

import os
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver
from agent.graph.checkpointers.vercel_kv_checkpointer import VercelKVCheckpointer

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
    
    elif CHECKPOINTER_TYPE == "vercel_kv":
        from .vercel_kv_checkpointer import VercelKVCheckpointer
        return VercelKVCheckpointer()
    
    else:
        # Default to memory saver
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

# Export the checkpointer classes
try:
    from .vercel_kv_checkpointer import VercelKVCheckpointer
except ImportError:
    pass

__all__ = ['VercelKVCheckpointer', 'get_checkpointer'] 