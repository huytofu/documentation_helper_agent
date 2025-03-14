from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from typing import Dict, Any, Set
import inspect
from agent.graph.state import OutputGraphState

def get_page_content(doc: Document) -> str:
    if doc.metadata.get("source") == "web":
        return doc.page_content[:500]
    else:
        return ""
    
def get_last_message_type(messages):
    """Get the type of the last message in a list of messages.
    
    Args:
        messages: List of messages to check
        
    Returns:
        str: "human" for human messages, "ai" for AI messages, None for other types
    """
    if not messages:
        return None
    last_message = messages[-1]
    if last_message.type == "human" or isinstance(last_message, HumanMessage):
        return "human"
    elif last_message.type == "ai" or isinstance(last_message, AIMessage):
        return "ai"
    return None 

def get_output_state_properties() -> Set[str]:
    """Get all property names defined in the OutputGraphState class.
    
    Returns:
        Set of property names from OutputGraphState
    """
    # Get all class variables from OutputGraphState
    properties = set()
    
    # Inspect the class attributes
    for attr_name, attr_value in inspect.getmembers(OutputGraphState):
        # Skip private attributes and methods
        if attr_name.startswith('_') or callable(attr_value):
            continue
        # Add attribute to properties
        properties.add(attr_name)
    
    return properties

# Cache the output state properties to avoid repeated inspection
OUTPUT_STATE_PROPERTIES = get_output_state_properties()

def extract_output_state_properties(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only the properties that belong to OutputGraphState.
    
    Automatically detects properties from the OutputGraphState class definition.
    
    Args:
        state: The full state object
        
    Returns:
        Dict containing only OutputGraphState properties
    """
    output_properties = {}
    
    # Add all properties from OutputGraphState that exist in the state
    for prop in OUTPUT_STATE_PROPERTIES:
        if prop in state:
            output_properties[prop] = state[prop]
    
    return output_properties 