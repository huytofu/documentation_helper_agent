from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document

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