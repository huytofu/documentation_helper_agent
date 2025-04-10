from typing import List, Optional, Dict, Any
from copilotkit import CopilotKitState
import os
import logging
import shutil
import tempfile
import atexit
from pathlib import Path
import fcntl
import time
from langchain_core.messages import BaseMessage

logger = logging.getLogger("graph.state")

class FileLock:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lock_file = f"{file_path}.lock"
        self.lock_fd = None

    def acquire(self) -> bool:
        """Acquire an exclusive lock on the file"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.lockf(self.lock_fd, fcntl.F_TLOCK, 0)
            return True
        except (IOError, OSError):
            if self.lock_fd:
                self.lock_fd.close()
            return False

    def release(self):
        """Release the lock on the file"""
        if self.lock_fd:
            fcntl.lockf(self.lock_fd, fcntl.F_ULOCK, 0)
            self.lock_fd.close()
            try:
                os.remove(self.lock_file)
            except OSError:
                pass

def atomic_remove(path: str, is_dir: bool = False) -> bool:
    """
    Safely remove a file or directory using atomic operations.
    
    Args:
        path: Path to the file or directory
        is_dir: Whether the path is a directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    lock = FileLock(path)
    if not lock.acquire():
        logger.warning(f"Could not acquire lock for {path}")
        return False

    try:
        if is_dir:
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    except Exception as e:
        logger.error(f"Error removing {path}: {str(e)}")
        return False
    finally:
        lock.release()

def cleanup_resources(state: Dict[str, Any]) -> None:
    """
    Clean up temporary resources and handle errors gracefully.
    This function will attempt cleanup regardless of state validity.
    Uses atomic operations to prevent race conditions.
    
    Args:
        state (Dict[str, Any]): The state dictionary containing resource paths
    """
    if not isinstance(state, dict):
        logger.warning("State is not a dictionary, skipping cleanup")
        return

    cwd = os.getcwd()
    success_count = 0
    failure_count = 0

    def is_safe_path(path: str) -> bool:
        """Check if path is safe to delete (within workspace)"""
        try:
            abs_path = os.path.abspath(path)
            return abs_path.startswith(cwd)
        except Exception:
            return False

    def cleanup_file(path: str) -> bool:
        """Safely clean up a single file using atomic operations"""
        try:
            if not is_safe_path(path):
                logger.warning(f"Skipping unsafe file path: {path}")
                return False
            if os.path.exists(path):
                return atomic_remove(path)
            return True  # File doesn't exist, consider it cleaned up
        except Exception as e:
            logger.error(f"Error cleaning up file {path}: {str(e)}")
            return False

    def cleanup_directory(path: str) -> bool:
        """Safely clean up a directory using atomic operations"""
        try:
            if not is_safe_path(path):
                logger.warning(f"Skipping unsafe directory path: {path}")
                return False
            if os.path.exists(path):
                return atomic_remove(path, is_dir=True)
            return True  # Directory doesn't exist, consider it cleaned up
        except Exception as e:
            logger.error(f"Error cleaning up directory {path}: {str(e)}")
            return False

    # Clean up files
    for file_key in ['temp_file', 'temp_file_path', 'file_path']:
        if file_path := state.get(file_key):
            if cleanup_file(file_path):
                success_count += 1
            else:
                failure_count += 1

    # Clean up directories
    for dir_key in ['temp_dir', 'temp_dir_path', 'directory_path']:
        if dir_path := state.get(dir_key):
            if cleanup_directory(dir_path):
                success_count += 1
            else:
                failure_count += 1

    # Clean up any additional resources in the state
    for key, value in state.items():
        if isinstance(value, str) and any(key.endswith(suffix) for suffix in ['_file', '_dir', '_path']):
            if os.path.isfile(value):
                if cleanup_file(value):
                    success_count += 1
                else:
                    failure_count += 1
            elif os.path.isdir(value):
                if cleanup_directory(value):
                    success_count += 1
                else:
                    failure_count += 1

    # Log summary
    if success_count > 0 or failure_count > 0:
        logger.info(f"Resource cleanup completed: {success_count} successful, {failure_count} failed")

class InputGraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        language: coding language
        generation: LLM generation
    """

    language: str = ""
    comments: str = ""

class OutputGraphState(CopilotKitState):
    """
    Represents the state of our graph.

    Attributes:
        current_node: current node
    """
    current_node: str = ""
    query: str = ""
    rewritten_query: str = ""
    retry_count: int = 0
    framework: str = ""

class GraphState(InputGraphState, OutputGraphState):
    """
    Represents the state of our graph.

    Attributes:
        query: query
        framework: framework (vectorstore name)
        retry_count: number of retries
        documents: list of documents
        pass_summarize: graph execution has passed summarize node
        summarized: conversation has been summarized
    """
    pass_summarize: bool = False
    summarized: bool = False
    documents: List[Any] = []

