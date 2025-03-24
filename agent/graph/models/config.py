"""
Configuration settings for language models.

This module provides a centralized place to configure model settings,
including switching between Ollama, Hugging Face models, and third-party providers.

Environment Variables:
    USE_HUGGINGFACE: Set to "true" to use Hugging Face models instead of Ollama
    HUGGINGFACE_API_KEY: Your Hugging Face API key
    HUGGINGFACE_EMBEDDING_MODEL: Model ID for embeddings
    HUGGINGFACE_GRADER_MODEL: Model ID for grader
    HUGGINGFACE_ROUTER_MODEL: Model ID for router
    HUGGINGFACE_GENERATOR_MODEL: Model ID for generator
    
    USE_INFERENCE_CLIENT: Set to "true" to use Hugging Face InferenceClient with third-party providers
    INFERENCE_PROVIDER: Provider name (e.g., "together", "perplexity", "anyscale", etc.)
    INFERENCE_API_KEY: API key for the specified provider
    INFERENCE_EMBEDDING_MODEL: Model ID for embeddings via InferenceClient
    INFERENCE_GRADER_MODEL: Model ID for grader via InferenceClient
    INFERENCE_ROUTER_MODEL: Model ID for router via InferenceClient
    INFERENCE_GENERATOR_MODEL: Model ID for generator via InferenceClient
    
    PROVISIONED_CONCURRENCY: Number of concurrent instances to keep warm (default: 1)
    CONCURRENCY_LIMIT: Maximum number of concurrent requests per instance (default: 10)
"""

import os
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Global configuration
# Determine if Hugging Face models should be used
USE_HUGGINGFACE = os.environ.get("USE_HUGGINGFACE", "false").lower() == "true"
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# Third-party provider configuration via InferenceClient
# Determine if InferenceClient should be used
USE_INFERENCE_CLIENT = os.environ.get("USE_INFERENCE_CLIENT", "true").lower() == "true"
INFERENCE_PROVIDER = os.environ.get("INFERENCE_PROVIDER", "together")
INFERENCE_API_KEY = os.environ.get("INFERENCE_API_KEY", "")

# Model-specific configurations for Hugging Face
HUGGINGFACE_EMBEDDING_MODEL = os.environ.get("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
HUGGINGFACE_GRADER_MODEL = os.environ.get("HUGGINGFACE_GRADER_MODEL", "meta-llama/Llama-3-70b-chat-hf")
HUGGINGFACE_ROUTER_MODEL = os.environ.get("HUGGINGFACE_ROUTER_MODEL", "meta-llama/Llama-3-70b-chat-hf")
HUGGINGFACE_GENERATOR_MODEL = os.environ.get("HUGGINGFACE_GENERATOR_MODEL", "deepseek-ai/deepseek-coder-v2-instruct")

# Model-specific configurations for InferenceClient
INFERENCE_EMBEDDING_MODEL = os.environ.get("INFERENCE_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
INFERENCE_GRADER_MODEL = os.environ.get("INFERENCE_GRADER_MODEL", "meta-llama/Llama-3-70b-chat-hf")
INFERENCE_ROUTER_MODEL = os.environ.get("INFERENCE_ROUTER_MODEL", "meta-llama/Llama-3-70b-chat-hf")
INFERENCE_GENERATOR_MODEL = os.environ.get("INFERENCE_GENERATOR_MODEL", "deepseek-ai/deepseek-coder-v2-instruct")

# Ollama model configurations
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_GRADER_MODEL = "llama3.3:70b"
OLLAMA_ROUTER_MODEL = "llama3.3:70b"
OLLAMA_GENERATOR_MODEL = "deepseek-coder:33b"

# Concurrency settings
PROVISIONED_CONCURRENCY = int(os.environ.get("PROVISIONED_CONCURRENCY", "1"))
CONCURRENCY_LIMIT = int(os.environ.get("CONCURRENCY_LIMIT", "10"))

# Create thread pool for concurrent operations
thread_pool = ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT)

# Create semaphore for limiting concurrent requests
concurrency_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

def get_model_config() -> Dict[str, Any]:
    """
    Returns the current model configuration based on environment settings.
    
    Returns:
        dict: A dictionary containing the current model configuration.
    """
    # Determine which provider to use
    provider = "ollama"
    if USE_INFERENCE_CLIENT and INFERENCE_API_KEY:
        provider = "inference_client"
    elif USE_HUGGINGFACE and HUGGINGFACE_API_KEY:
        provider = "huggingface"
    
    # Get the appropriate models based on the provider
    if provider == "inference_client":
        models = {
            "embedding": INFERENCE_EMBEDDING_MODEL,
            "grader": INFERENCE_GRADER_MODEL,
            "router": INFERENCE_ROUTER_MODEL,
            "generator": INFERENCE_GENERATOR_MODEL,
        }
    elif provider == "huggingface":
        models = {
            "embedding": HUGGINGFACE_EMBEDDING_MODEL,
            "grader": HUGGINGFACE_GRADER_MODEL,
            "router": HUGGINGFACE_ROUTER_MODEL,
            "generator": HUGGINGFACE_GENERATOR_MODEL,
        }
    else:  # ollama
        models = {
            "embedding": OLLAMA_EMBEDDING_MODEL,
            "grader": OLLAMA_GRADER_MODEL,
            "router": OLLAMA_ROUTER_MODEL,
            "generator": OLLAMA_GENERATOR_MODEL,
        }
    
    return {
        "provider": provider,
        "use_huggingface": USE_HUGGINGFACE,
        "huggingface_api_key": HUGGINGFACE_API_KEY,
        "use_inference_client": USE_INFERENCE_CLIENT,
        "inference_provider": INFERENCE_PROVIDER,
        "inference_api_key": INFERENCE_API_KEY,
        "models": models,
        "provisioned_concurrency": PROVISIONED_CONCURRENCY,
        "concurrency_limit": CONCURRENCY_LIMIT
    }

async def with_concurrency_limit(func, *args, **kwargs):
    """
    Wrapper to limit concurrent executions using a semaphore.
    
    Args:
        func: The async function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function execution
    """
    async with concurrency_semaphore:
        return await func(*args, **kwargs) 