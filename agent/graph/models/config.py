"""
Configuration settings for language models.

This module provides a centralized place to configure model settings,
including switching between Ollama, Hugging Face models, and third-party providers.

Environment Variables:
    USE_HUGGINGFACE: Set to "true" to use Hugging Face models (default: true)
    USE_OLLAMA: Set to "true" to use Ollama models (default: false)
    USE_INFERENCE_CLIENT: Set to "true" to use InferenceClient with third-party providers
    USE_RUNPOD: Set to "true" to use RunPod for generator model
    
    HUGGINGFACE_API_KEY: Your Hugging Face API key
    INFERENCE_API_KEY: API key for the specified provider
    RUNPOD_API_KEY: RunPod API key
    RUNPOD_ENDPOINT_ID: RunPod endpoint ID
"""

import os
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_community.llms import HuggingFaceHub
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.chat_models import ChatHuggingFace
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from huggingface_hub import InferenceClient
from .runpod_client import RunPodClient

# Environment flags
USE_HUGGINGFACE = os.environ.get("USE_HUGGINGFACE", "true").lower() == "true"
USE_OLLAMA = os.environ.get("USE_OLLAMA", "false").lower() == "true"
USE_INFERENCE_CLIENT = os.environ.get("USE_INFERENCE_CLIENT", "false").lower() == "true"
USE_RUNPOD = os.environ.get("USE_RUNPOD", "false").lower() == "true"

# Validate environment configuration
if USE_HUGGINGFACE and USE_OLLAMA:
    raise ValueError("USE_HUGGINGFACE and USE_OLLAMA cannot be enabled simultaneously")

# API Keys
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
INFERENCE_API_KEY = os.environ.get("INFERENCE_API_KEY", "")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")

# Model IDs
MODEL_IDS = {
    "embeddings": "BAAI/bge-large-en-v1.5",
    "router": "meta-llama/Llama-3-70b-chat-hf",
    "grader": "meta-llama/Llama-3-70b-chat-hf",
    "generator": "deepseek-ai/deepseek-coder-v2-instruct"
}

# Ollama model names
OLLAMA_MODELS = {
    "embeddings": "qllama/bge-large-en-v1.5",
    "router": "llama3.3:70b",
    "grader": "llama3.3:70b",
    "generator": "deepseek-coder:33b"
}

# Concurrency settings
PROVISIONED_CONCURRENCY = int(os.environ.get("PROVISIONED_CONCURRENCY", "1"))
CONCURRENCY_LIMIT = int(os.environ.get("CONCURRENCY_LIMIT", "5"))

# Initialize thread pool and semaphore
thread_pool = ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT)
concurrency_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# Initialize RunPod client if enabled
runpod_client: Optional[RunPodClient] = None
if USE_RUNPOD and RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID:
    runpod_client = RunPodClient.from_env()

def get_inference_client() -> Optional[InferenceClient]:
    """Get a configured InferenceClient for third-party providers."""
    if not USE_INFERENCE_CLIENT or not INFERENCE_API_KEY:
        return None
        
    return InferenceClient(
        model=os.environ.get("INFERENCE_PROVIDER", "together"),
        token=INFERENCE_API_KEY,
        timeout=30,
        max_retries=3,
        retry_on_failure=True,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )

def get_ollama_config() -> Dict[str, Any]:
    """Get Ollama configuration with optimized settings."""
    return {
        "num_ctx": 2048,
        "num_gpu": 1,
        "num_thread": 8,
        "temperature": 0.2,
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 512,
        "repeat_penalty": 1.1,
        "seed": 42,
        "timeout": 30,
        "num_keep": 5,
        "stop": ["</s>", "Human:", "Assistant:"],
        "tfs_z": 0.7,
        "num_batch": 512,
        "rope_scaling": {"type": "linear", "factor": 1.0},
        "rope_freq_base": 10000,
        "rope_freq_scale": 1.0,
        "mirostat": 2,
        "mirostat_tau": 5.0,
        "mirostat_eta": 0.1,
        "penalize_newline": True,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.1,
        "typical_p": 0.9,
        "tiktoken_encoding": "cl100k_base",
        "num_parallel": 1,
        "num_beam": 1,
    }

async def with_concurrency_limit(func, *args, **kwargs):
    """Wrapper to limit concurrent executions using a semaphore."""
    async with concurrency_semaphore:
        return await func(*args, **kwargs)

def get_active_provider(component: str) -> str:
    """Get the active provider for a component based on configuration."""
    if USE_OLLAMA:
        return "ollama"
    
    if USE_INFERENCE_CLIENT:
        return "inference"
    
    if component == "generator" and USE_RUNPOD and runpod_client:
        return "runpod"
    
    return "huggingface"

def get_model_config_for_component(component: str) -> dict:
    """Get the model configuration for a specific component."""
    provider = get_active_provider(component)
    
    if provider == "ollama":
        return {"model": OLLAMA_MODELS[component], **get_ollama_config()}
    
    if provider == "inference":
        return {
            "model": MODEL_IDS[component],
            "api_key": INFERENCE_API_KEY
        }
    
    if provider == "runpod":
        return {
            "model": MODEL_IDS[component],
            "client": runpod_client
        }
    
    return {
        "model": MODEL_IDS[component],
        "api_key": HUGGINGFACE_API_KEY
    } 