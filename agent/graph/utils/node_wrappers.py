"""Node wrappers module for LangGraph nodes to emit state changes to CopilotKit."""

from typing import Dict, Any, Callable, Awaitable, TypeVar, cast
import asyncio
import logging
from agent.graph.state import GraphState
from agent.graph.utils.state_emitter import emit_state_changes

logger = logging.getLogger(__name__)

# Type for LangGraph node functions
NodeFuncType = Callable[[GraphState, Dict[str, Any]], Awaitable[Dict[str, Any]]]
T = TypeVar('T', bound=NodeFuncType)

def wrap_node_for_state_emission(func: T) -> T:
    """
    Wrap a node function to emit state changes after execution.
    
    This wrapper:
    1. Executes the original node function
    2. Applies the returned changes to a copy of the state
    3. Emits relevant changes to CopilotKit
    4. Returns the original result
    
    Args:
        func: The async node function to wrap
        
    Returns:
        A wrapped function that emits state changes after execution
    """
    async def wrapped(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
        # Log before node execution 
        node_name = func.__name__
        logger.debug(f"Executing node {node_name}")
        
        # Execute the original function
        result = await func(state, config)
        
        # Create a new state with the result applied
        if isinstance(state, dict):
            new_state = {**state, **result}
        else:
            # For class-based state, create a new instance with updated properties
            new_state = state.copy()
            for key, value in result.items():
                setattr(new_state, key, value)
        
        # Log the result keys for debugging
        logger.debug(f"Node {node_name} returned keys: {list(result.keys())}")
        
        # Emit state changes if config is provided
        if config:
            logger.debug(f"Emitting state changes after node {node_name}")
            await emit_state_changes(new_state, config)
            
        return result
    
    # Preserve the original function name and docstring
    wrapped.__name__ = func.__name__
    wrapped.__doc__ = func.__doc__
    
    # Return with correct type
    return cast(T, wrapped)

def wrap_all_nodes(nodes_dict: Dict[str, NodeFuncType]) -> Dict[str, NodeFuncType]:
    """
    Wrap all node functions in a dictionary to emit state changes.
    
    Args:
        nodes_dict: Dictionary mapping node names to node functions
        
    Returns:
        Dictionary with wrapped node functions
    """
    wrapped_nodes = {}
    for node_name, node_func in nodes_dict.items():
        wrapped_nodes[node_name] = wrap_node_for_state_emission(node_func)
        logger.info(f"Wrapped node {node_name} for state emission")
    return wrapped_nodes 