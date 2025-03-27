from typing import List, Optional, Dict, Any
from copilotkit import CopilotKitState
import os
import logging
import shutil

logger = logging.getLogger("graph.state")

def cleanup_resources(state: Dict[str, Any]) -> None:
    """Clean up any temporary resources and handle cleanup errors gracefully.
    
    Args:
        state: Current graph state containing resources to clean up
    """
    if not isinstance(state, dict):
        logger.error("Invalid state type for cleanup")
        return
        
    # Get current working directory once
    cwd = os.path.abspath(os.getcwd())
    
    # Track cleanup status
    success_count = 0
    failed_count = 0
    
    def is_safe_path(path: str) -> bool:
        """Check if path is within allowed directory."""
        try:
            return os.path.abspath(path).startswith(cwd)
        except Exception:
            return False
    
    def cleanup_file(file_path: str) -> bool:
        """Clean up a single file."""
        try:
            if not isinstance(file_path, str) or not is_safe_path(file_path):
                return False
                
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return True  # Consider non-existent files as successfully cleaned
        except Exception:
            return False
    
    def cleanup_directory(dir_path: str) -> bool:
        """Clean up a single directory."""
        try:
            if not isinstance(dir_path, str) or not is_safe_path(dir_path):
                return False
                
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                return True
            return True  # Consider non-existent directories as successfully cleaned
        except Exception:
            return False
    
    # Clean up temporary files
    if "temp_files" in state:
        for file_path in state["temp_files"]:
            if cleanup_file(file_path):
                success_count += 1
            else:
                failed_count += 1
    
    # Clean up temporary directories
    if "temp_dirs" in state:
        for dir_path in state["temp_dirs"]:
            if cleanup_directory(dir_path):
                success_count += 1
            else:
                failed_count += 1
    
    # Log summary only if there were any operations
    if success_count > 0 or failed_count > 0:
        if success_count > 0:
            logger.info(f"Successfully cleaned up {success_count} resources")
        if failed_count > 0:
            logger.error(f"Failed to clean up {failed_count} resources")

class InputGraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        framework: framework (vectorstore name)
        language: coding language
        generation: LLM generation
        web_search: whether to add search
        retry_count: number of retries
        documents: list of documents
    """

    language: str = ""
    comments: str = ""
    # messages: List[Dict[str, Any]] = []
    # copilotkit: Dict[str, Any] = {}

class OutputGraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        current_node: current node
        generation: LLM generation
    """
    current_node: str = ""

class GraphState(InputGraphState, OutputGraphState):
    query: str
    framework: str = ""
    retry_count: int = 0
    documents: List[str] = []
    

