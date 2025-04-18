from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from typing import Dict, Any, Set
import inspect
from agent.graph.state import OutputGraphState

def convert_to_raw_documents(documents):
    """Convert LangChain documents to raw format."""
    raw_documents = []
    for doc in documents:
        if isinstance(doc, dict) and "lc" in doc:  # LangChain serialized format
            raw_doc = {
                "metadata": doc.get("kwargs", {}).get("metadata", {}),
                "page_content": doc.get("kwargs", {}).get("page_content", ""),
                "type": doc.get("kwargs", {}).get("type", "Document")
            }
        else:  # Already in raw format
            raw_doc = doc
        raw_documents.append(raw_doc)
    return raw_documents

def trim_messages(messages: list, max_messages: int = 8) -> list:
    """Trim the messages list to contain only the last N messages."""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

def get_content(doc) -> str:
    if isinstance(doc, Document):
        return doc.get("page_content", "")[:500]
    else:
        if isinstance(doc, dict):
            if "page_content" in doc:
                return doc["page_content"][:500]
            elif "content" in doc:
                return doc["content"][:500]
            elif "markdown" in doc:
                return doc["markdown"][:500]
            else:
                return ""
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