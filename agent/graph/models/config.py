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
"""

import os

# Global configuration
USE_HUGGINGFACE = os.environ.get("USE_HUGGINGFACE", "false").lower() == "true"
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# Third-party provider configuration via InferenceClient
USE_INFERENCE_CLIENT = os.environ.get("USE_INFERENCE_CLIENT", "false").lower() == "true"
INFERENCE_PROVIDER = os.environ.get("INFERENCE_PROVIDER", "together")
INFERENCE_API_KEY = os.environ.get("INFERENCE_API_KEY", "")

# Model-specific configurations for Hugging Face
HUGGINGFACE_EMBEDDING_MODEL = os.environ.get("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
HUGGINGFACE_GRADER_MODEL = os.environ.get("HUGGINGFACE_GRADER_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
HUGGINGFACE_ROUTER_MODEL = os.environ.get("HUGGINGFACE_ROUTER_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
HUGGINGFACE_GENERATOR_MODEL = os.environ.get("HUGGINGFACE_GENERATOR_MODEL", "codellama/CodeLlama-34b-Instruct-hf")

# Model-specific configurations for InferenceClient
INFERENCE_EMBEDDING_MODEL = os.environ.get("INFERENCE_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
INFERENCE_GRADER_MODEL = os.environ.get("INFERENCE_GRADER_MODEL", "deepseek-ai/DeepSeek-R1")
INFERENCE_ROUTER_MODEL = os.environ.get("INFERENCE_ROUTER_MODEL", "deepseek-ai/DeepSeek-R1")
INFERENCE_GENERATOR_MODEL = os.environ.get("INFERENCE_GENERATOR_MODEL", "deepseek-ai/DeepSeek-Coder-V2")

# Ollama model configurations
OLLAMA_EMBEDDING_MODEL = "deepseek-coder:33b"
OLLAMA_GRADER_MODEL = "llama3.3:70b"
OLLAMA_ROUTER_MODEL = "llama3.3:70b"
OLLAMA_GENERATOR_MODEL = "deepseek-coder:33b"

def get_model_config():
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
        "models": models
    } 