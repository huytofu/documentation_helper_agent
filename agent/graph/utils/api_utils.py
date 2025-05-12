"""Utility functions for API error handling and response validation."""

import logging
from typing import Any, Dict, Optional, TypeVar, Generic
from pydantic import BaseModel, field_validator
import json
from datetime import datetime
from pathlib import Path
import asyncio
import functools
import time
logger = logging.getLogger(__name__)

# Standard timeout settings
STANDARD_TIMEOUT = 30  # seconds
GENERATION_TIMEOUT = 60   # seconds
GRADER_TIMEOUT = 10   # seconds

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Base class for API responses with validation."""
    success: bool = True
    error: Optional[str] = None
    data: Optional[T] = None
    timestamp: datetime = datetime.now()

    @field_validator('data')
    @classmethod
    def validate_data(cls, v):
        if v is None and not cls.error:
            raise ValueError('Data cannot be None when there is no error')
        return v

class GradingResponse(APIResponse[bool]):
    """Response model for grading operations."""
    binary_score: bool = False
    confidence: float = 0.0

    @field_validator('binary_score')
    @classmethod
    def validate_binary_score(cls, v):
        if not isinstance(v, bool):
            raise ValueError('binary_score must be a boolean')
        return v

class RouterResponse(APIResponse[str]):
    """Response model for router operations."""
    language: Optional[str] = None
    datasource: Optional[str] = None

class GenerationResponse(APIResponse[str]):
    """Response model for generation operations."""
    content: str = ""
    metadata: Dict[str, Any] = {}

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v

class APICostTracker:
    """Tracks API usage and costs."""
    
    def __init__(self):
        self.usage = {
            'embeddings': {'tokens': 0, 'cost': 0.0, 'requests': 0},
            'router': {'tokens': 0, 'cost': 0.0, 'requests': 0},
            'grader': {'tokens': 0, 'cost': 0.0, 'requests': 0},
            'generator': {'tokens': 0, 'cost': 0.0, 'requests': 0},
            'web_search': {'tokens': 0, 'cost': 0.0, 'requests': 0}
        }
        self.last_save = datetime.now()
        self.save_interval = 300  # 5 minutes
        self.usage_file = Path('api_usage.json')
        self._load_usage()

    def _load_usage(self):
        """Load existing usage data from file."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    self.usage = json.load(f)
            except Exception as e:
                logger.error(f"Error loading usage data: {e}")

    def _save_usage(self):
        """Save usage data to file."""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving usage data: {e}")

    def track_usage(self, api_type: str, tokens: int = 0, cost: float = 0.0, requests: int = 0):
        """Track API usage and costs."""
        if api_type not in self.usage:
            self.usage[api_type] = {'tokens': 0, 'cost': 0.0, 'requests': 0}

        print(tokens, cost, requests)
        self.usage[api_type]['tokens'] += tokens
        self.usage[api_type]['cost'] += cost
        self.usage[api_type]['requests'] += requests

        # Save if interval has passed
        if (datetime.now() - self.last_save).total_seconds() >= self.save_interval:
            self._save_usage()
            self.last_save = datetime.now()

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get a summary of API usage."""
        return {
            'total_tokens': sum(u['tokens'] for u in self.usage.values()),
            'total_cost': sum(u['cost'] for u in self.usage.values()),
            'total_requests': sum(u['requests'] for u in self.usage.values()),
            'by_type': self.usage
        }

# Global cost tracker instance
cost_tracker = APICostTracker()

def handle_api_error(func):
    """Decorator for handling API errors with retries."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper for synchronous functions"""
        try:
            return func(*args, **kwargs)
        except TimeoutError as e:
            logger.error(f"Timeout error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
        except ConnectionError as e:
            logger.error(f"Connection error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        """Wrapper for asynchronous functions"""
        try:
            return await func(*args, **kwargs)
        except TimeoutError as e:
            logger.error(f"Timeout error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
        except ConnectionError as e:
            logger.error(f"Connection error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return get_default_response(func.__name__)
    
    # Check if the function is a coroutine function
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper

def get_default_response(api_type: str) -> APIResponse:
    """Get default response based on API type."""
    if api_type == 'language_router':
        return RouterResponse(
            success=False,
            error="API call failed, using default language",
            language="python"  # Default language
        )
    elif api_type == 'vectorstore_router':
        return RouterResponse(
            success=False,
            error="API call failed, defaulting to None",
            datasource=None
        )
    elif 'grader' in api_type:
        return GradingResponse(
            success=False,
            error="API call failed, skipping grading",
            binary_score=False,
            confidence=0.0
        )
    elif api_type == 'generator':
        return GenerationResponse(
            success=False,
            error="API call failed, no generation available",
            content="",
            metadata={}
        )
    else:
        return APIResponse(
            success=False,
            error=f"API call failed for {api_type}",
            data=None
        )

async def standard_sleep():
    """Sleep for 1 seconds."""
    await asyncio.sleep(1)

def _sanitize_sensitive_data(data: Any) -> Any:
    """Sanitize sensitive data in request/response bodies."""
    if isinstance(data, dict):
        sensitive_keys = {"api_key", "password", "token", "secret"}
        return {
            k: "[REDACTED]" if any(sk in k.lower() for sk in sensitive_keys)
            else _sanitize_sensitive_data(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_sanitize_sensitive_data(item) for item in data]
    return data

def extract_properties_and_update_state(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Extract properties from request and update state.
    
    Args:
        request_body: The request body containing state and properties
        
    Returns:
        Updated request body with properties in state
    """
    state = request_body.get("state", {})
    properties = request_body.get("properties", {})
    
    # Update state with user_id if present
    for key, value in properties.items():
        state[key] = value
    
    # Update request body with modified state
    request_body["state"] = state
    
    return request_body