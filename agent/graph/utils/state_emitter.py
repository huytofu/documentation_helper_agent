"""State emitter module for LangGraph state changes to CopilotKit."""

from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
import asyncio
import logging
from agent.graph.state import GraphState
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger(__name__)

# Empty set means track all properties
TRACKED_PROPERTIES = set()

class StateChangeEmitter:
    """
    Monitors and emits state changes for LangGraph nodes.
    
    This class acts as a wrapper around state updates, detecting changes
    to specified properties and emitting them to CopilotKit.
    """
    
    def __init__(self, tracked_properties: Optional[Set[str]] = None):
        """Initialize the state change emitter.
        
        Args:
            tracked_properties: Set of state property names to track.
                If None or empty set, tracks ALL properties.
        """
        self.tracked_properties = tracked_properties if tracked_properties is not None else TRACKED_PROPERTIES
        self.previous_state: Dict[str, Any] = {}
        logger.info(f"Initialized StateChangeEmitter to track: {'ALL properties' if not self.tracked_properties else self.tracked_properties}")
    
    def extract_tracked_properties(self, state: GraphState) -> Dict[str, Any]:
        """Extract properties from the state.
        
        If tracked_properties is empty, extract all properties.
        """
        result = {}
        
        # If no specific properties are tracked, extract all properties
        if not self.tracked_properties:
            # For class-based state
            if hasattr(state, "__dict__"):
                # Filter out private attributes (starting with _)
                result = {k: v for k, v in state.__dict__.items() if not k.startswith('_')}
            # For dict-based state
            elif isinstance(state, dict):
                result = dict(state)
            return result
        
        # Otherwise, extract only tracked properties
        for prop in self.tracked_properties:
            if hasattr(state, prop):
                result[prop] = getattr(state, prop)
            elif isinstance(state, dict) and prop in state:
                result[prop] = state[prop]
        return result
    
    def detect_changes(self, current_state: GraphState) -> Dict[str, Any]:
        """Detect changes between current state and previous state."""
        current_tracked = self.extract_tracked_properties(current_state)
        changed_props = {}
        
        # Detect which properties have changed
        for prop, value in current_tracked.items():
            if prop not in self.previous_state or self.previous_state[prop] != value:
                changed_props[prop] = value
                
        # Update previous state
        self.previous_state.update(current_tracked)
        return changed_props
    
    async def emit_if_changed(self, state: GraphState, config: Dict[str, Any]) -> None:
        """Detect changes and emit them if any are found."""
        changes = self.detect_changes(state)
        
        if changes:
            logger.info(f"Detected state changes: {changes}")
            await copilotkit_emit_state(config, changes)
        else:
            logger.debug("No state changes detected")

# Global instance for use across the application
state_emitter = StateChangeEmitter()

async def emit_state_changes(state: GraphState, config: Dict[str, Any] = None) -> None:
    """Convenience function to emit state changes.
    
    Args:
        state: The current graph state
        config: The configuration for copilotkit_emit_state
    """
    if config:
        await state_emitter.emit_if_changed(state, config)

# Decorator to automatically emit state changes after a node function
def emit_state_changes_after(
    func: Callable[[GraphState, Dict[str, Any]], Awaitable[Dict[str, Any]]]
) -> Callable[[GraphState, Dict[str, Any]], Awaitable[Dict[str, Any]]]:
    """Decorator to emit state changes after a node function completes.
    
    This decorator wraps an async node function and emits state changes after it completes.
    
    Args:
        func: The async node function to wrap
        
    Returns:
        A wrapped function that emits state changes after execution
    """
    async def wrapper(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
        # Execute the original function
        result = await func(state, config)
        
        # Create a new state with the result applied
        if isinstance(state, dict):
            new_state = {**state, **result}
        else:
            # For class-based state, create a new instance
            new_state = state.copy()
            for key, value in result.items():
                setattr(new_state, key, value)
        
        # Emit state changes if config is provided
        if config:
            await emit_state_changes(new_state, config)
            
        return result
    
    return wrapper 