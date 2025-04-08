"""Security utilities for prompt sanitization and validation."""

import re
from typing import Dict, Any, List
import logging
from fastapi import HTTPException
import json

logger = logging.getLogger(__name__)

# Security patterns for code injection
CODE_INJECTION_PATTERNS = [
    # Code execution patterns
    r"eval\s*\(",  # eval() calls
    r"exec\s*\(",  # exec() calls
    r"os\.system\s*\(",  # system calls
    r"subprocess\.",  # subprocess calls
    r"commands\.",  # commands module
    r"popen\s*\(",  # popen calls
    r"spawn\s*\(",  # spawn calls
    r"fork\s*\(",  # fork calls
    r"vfork\s*\(",  # vfork calls
    
    # Dangerous imports
    r"import\s+os",
    r"import\s+subprocess",
    r"import\s+sys",
    r"import\s+commands",
    r"import\s+pty",
    r"import\s+signal",
    r"import\s+ctypes",
    r"import\s+mmap",
    r"import\s+fcntl",
    r"import\s+socket",
    r"import\s+threading",
    r"import\s+multiprocessing",
    
    # Dynamic imports and reflection
    r"__import__\s*\(",
    r"getattr\s*\(",
    r"setattr\s*\(",
    r"delattr\s*\(",
    r"hasattr\s*\(",
    r"globals\s*\(",
    r"locals\s*\(",
    
    # Code blocks and templates
    r"```.*?```",  # Code blocks
    r"`.*?`",      # Inline code
    r"<script>.*?</script>",  # Script tags
    r"<.*?>",      # Any HTML tags
    r"\{\{.*?\}\}",  # Template expressions
    r"\{%.*?%\}",  # Template statements
    
    # Shell commands and paths
    r"\.\./",      # Directory traversal
    r"\.\.\\",     # Windows directory traversal
    r"cmd\.exe",   # Windows command prompt
    r"powershell", # PowerShell
    r"bash",       # Bash shell
    r"sh",         # Shell
    r"\.exe",      # Executable files
    r"\.dll",      # Dynamic libraries
    r"\.so",       # Shared objects
    r"\.dylib",    # Dynamic libraries (macOS)
    
    # Network and file operations
    r"open\s*\(",  # File operations
    r"urllib\.",   # URL operations
    r"requests\.", # HTTP requests
    r"wget",       # wget command
    r"curl",       # curl command
    r"ftp",        # FTP operations
    r"sftp",       # SFTP operations
    r"scp",        # SCP operations
]

# Enhanced NSFW patterns with child protection
NSFW_PATTERNS = [
    # General NSFW content
    r"porn",
    r"xxx",
    r"adult",
    r"sex",
    r"nude",
    r"naked",
    r"explicit",
    r"erotic",
    r"mature",
    
    # Child exploitation and abuse
    r"child\s*porn",
    r"child\s*abuse",
    r"child\s*exploitation",
    r"child\s*trafficking",
    r"child\s*sexual",
    r"child\s*prostitution",
    r"child\s*molestation",
    r"child\s*rape",
    r"child\s*assault",
    r"child\s*violence",
    r"child\s*grooming",
    r"child\s*predator",
    r"child\s*exploitation",
    r"child\s*abuse\s*material",
    r"child\s*sexual\s*abuse",
    r"child\s*sexual\s*exploitation",
    r"child\s*sexual\s*material",
    r"child\s*sexual\s*content",
    r"child\s*sexual\s*images",
    r"child\s*sexual\s*videos",
    r"child\s*sexual\s*media",
    r"child\s*sexual\s*abuse\s*material",
    r"child\s*sexual\s*exploitation\s*material",
    r"child\s*sexual\s*abuse\s*content",
    r"child\s*sexual\s*exploitation\s*content",
    r"child\s*sexual\s*abuse\s*images",
    r"child\s*sexual\s*exploitation\s*images",
    r"child\s*sexual\s*abuse\s*videos",
    r"child\s*sexual\s*exploitation\s*videos",
    r"child\s*sexual\s*abuse\s*media",
    r"child\s*sexual\s*exploitation\s*media",
]

# Additional validation patterns
VALIDATION_PATTERNS = {
    "max_length": 10000,  # Maximum prompt length
    "min_length": 1,      # Minimum prompt length
    "allowed_chars": r"^[a-zA-Z0-9\s.,!?()\[\]{}:;\"'-_@#$%^&*+=/\\|<>~`]+$",  # Allowed characters
    "max_words": 500,     # Maximum number of words
    "max_lines": 50,      # Maximum number of lines
}

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

def validate_prompt_length(prompt: str) -> None:
    """Validate prompt length and content.
    
    Args:
        prompt: Prompt to validate
        
    Raises:
        SecurityError: If validation fails
    """
    # Check length
    if len(prompt) > VALIDATION_PATTERNS["max_length"]:
        raise SecurityError("Prompt exceeds maximum length")
    if len(prompt) < VALIDATION_PATTERNS["min_length"]:
        raise SecurityError("Prompt is too short")
    
    # Check word count
    word_count = len(prompt.split())
    if word_count > VALIDATION_PATTERNS["max_words"]:
        raise SecurityError("Prompt contains too many words")
    
    # Check line count
    line_count = len(prompt.splitlines())
    if line_count > VALIDATION_PATTERNS["max_lines"]:
        raise SecurityError("Prompt contains too many lines")
    
    # Check allowed characters
    if not re.match(VALIDATION_PATTERNS["allowed_chars"], prompt):
        raise SecurityError("Prompt contains invalid characters")

def sanitize_prompt(prompt: str) -> str:
    """Sanitize user prompt to prevent code injection and malicious content.
    
    Args:
        prompt: User input prompt
        
    Returns:
        Sanitized prompt
        
    Raises:
        SecurityError: If prompt contains malicious content
    """
    # Validate prompt length and content
    validate_prompt_length(prompt)
    
    # Convert to lowercase for case-insensitive matching
    prompt_lower = prompt.lower()
    
    # Check for code injection patterns
    for pattern in CODE_INJECTION_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE | re.DOTALL):
            logger.warning(f"Potential code injection detected in prompt: {pattern}")
            raise SecurityError("Code injection attempt detected")
    
    # Check for NSFW content
    for pattern in NSFW_PATTERNS:
        if re.search(pattern, prompt_lower):
            logger.warning(f"NSFW content detected in prompt: {pattern}")
            raise SecurityError("NSFW content detected")
    
    # Remove any HTML tags
    prompt = re.sub(r"<[^>]*>", "", prompt)
    
    # Remove any markdown code blocks
    prompt = re.sub(r"```.*?```", "", prompt, flags=re.DOTALL)
    
    # Remove any inline code
    prompt = re.sub(r"`.*?`", "", prompt)
    
    # Remove any URLs
    prompt = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", prompt)
    
    # Remove any file paths
    prompt = re.sub(r"(?:[a-zA-Z]:\\|/|\\|\.\./|\.\.\\).*?(?:/|\\|$)", "", prompt)
    
    # Remove any command line arguments
    prompt = re.sub(r"-[a-zA-Z0-9]+(?:\s+[^-\s]+)*", "", prompt)
    
    return prompt.strip()

def validate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize state dictionary.
    
    Args:
        state: State dictionary to validate
        
    Returns:
        Validated and sanitized state
        
    Raises:
        SecurityError: If state contains invalid or malicious content
    """
    if not isinstance(state, dict):
        raise SecurityError("Invalid state format")
    
    # Validate required fields
    required_fields = ["query", "documents", "messages"]
    for field in required_fields:
        if field not in state:
            raise SecurityError(f"Missing required field: {field}")
    
    # Sanitize query
    if isinstance(state["query"], str):
        state["query"] = sanitize_prompt(state["query"])
    
    # Sanitize messages
    if isinstance(state["messages"], list):
        for message in state["messages"]:
            if isinstance(message, dict) and "content" in message:
                message["content"] = sanitize_prompt(message["content"])
    
    # Validate documents
    if isinstance(state["documents"], list):
        for doc in state["documents"]:
            if isinstance(doc, dict):
                if "content" in doc:
                    doc["content"] = sanitize_prompt(doc["content"])
                if "metadata" in doc:
                    # Remove any sensitive metadata
                    sensitive_keys = {"password", "token", "secret", "key"}
                    doc["metadata"] = {
                        k: v for k, v in doc["metadata"].items()
                        if k.lower() not in sensitive_keys
                    }
    
    return state

def validate_batch_states(states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and sanitize a batch of states.
    
    Args:
        states: List of state dictionaries
        
    Returns:
        List of validated and sanitized states
        
    Raises:
        SecurityError: If any state contains invalid or malicious content
    """
    return [validate_state(state) for state in states]

def sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize response data before sending to client.
    
    Args:
        response: Response dictionary to sanitize
        
    Returns:
        Sanitized response
    """
    if not isinstance(response, dict):
        return response
    
    # Remove any sensitive information
    sensitive_keys = {"password", "token", "secret", "key", "api_key"}
    sanitized = {
        k: v for k, v in response.items()
        if k.lower() not in sensitive_keys
    }
    
    # Sanitize any nested dictionaries
    for key, value in sanitized.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_response(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_response(item) if isinstance(item, dict) else item
                for item in value
            ]
    
    return sanitized 