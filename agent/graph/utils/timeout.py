import asyncio
import functools
from typing import Any, Callable, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging

logger = logging.getLogger("graph.timeout")

T = TypeVar("T")

def timeout(seconds: Union[int, float]) -> Callable:
    """
    Decorator that adds timeout functionality to a function.
    If the function takes longer than the specified seconds, it will raise a TimeoutError.
    
    Args:
        seconds: Number of seconds before timeout
        
    Returns:
        Decorated function with timeout
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except TimeoutError:
                    logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                    raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        return wrapper
    return decorator

async def async_timeout(seconds: Union[int, float]) -> Callable:
    """
    Decorator that adds timeout functionality to an async function.
    If the function takes longer than the specified seconds, it will raise a TimeoutError.
    
    Args:
        seconds: Number of seconds before timeout
        
    Returns:
        Decorated async function with timeout
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Async function {func.__name__} timed out after {seconds} seconds")
                raise TimeoutError(f"Async function {func.__name__} timed out after {seconds} seconds")
        return wrapper
    return decorator 