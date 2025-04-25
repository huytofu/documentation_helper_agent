"""
Configuration settings for language models.

This module provides a centralized place to configure model settings,
including switching between Ollama, Hugging Face models, and third-party providers.

Environment Variables:
    USE_OLLAMA: Set to "true" to use Ollama models (default: false)
    USE_INFERENCE_CLIENT: Set to "true" to use InferenceClient with third-party providers
    USE_RUNPOD: Set to "true" to use RunPod for generator model
    
    INFERENCE_API_KEY: API key for the specified provider
    RUNPOD_API_KEY: RunPod API key
    RUNPOD_ENDPOINT_ID: RunPod endpoint ID
"""

import os
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .runpod_client import RunPodClient
import logging

logger = logging.getLogger(__name__)

# Environment flags
USE_OLLAMA = os.environ.get("USE_OLLAMA", "false").lower() == "true"
USE_INFERENCE_CLIENT = os.environ.get("USE_INFERENCE_CLIENT", "false").lower() == "true"
USE_RUNPOD = os.environ.get("USE_RUNPOD", "false").lower() == "true"
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")

# Validate environment configuration
if USE_OLLAMA and USE_INFERENCE_CLIENT:
    raise ValueError("USE_OLLAMA and USE_INFERENCE_CLIENT cannot be enabled simultaneously")

# Model IDs
MODEL_IDS = {
    "embeddings": "BAAI/bge-large-en-v1.5",
    # "router": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "router": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "sentiment_grader": "mistralai/Mistral-7B-Instruct-v0.3",
    "answer_grader": "mistralai/Mistral-7B-Instruct-v0.3",
    "retrieval_grader": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    # "hallucinate_grader": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    # "summarizer": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "hallucinate_grader": "Qwen/Qwen2.5-14B-Instruct",
    "summarizer": "Qwen/Qwen2.5-14B-Instruct",
    "generator": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
}

# Ollama model names
OLLAMA_MODELS = {
    "embeddings": "qllama/bge-large-en-v1.5",
    # "router": "mixtral:8x7b",
    "router": "llama3.1:latest",
    "sentiment_grader": "mistral:latest",
    "answer_grader": "mistral:latest",
    "retrieval_grader": "llama3.1:latest",
    # "hallucinate_grader": "llama3.1:latest",
    # "summarizer": "llama3.1:latest",
    "hallucinate_grader": "qwen2.5:14b",
    "summarizer": "qwen2.5:14b",
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
    """Get the active model provider for a component.
    
    Args:
        component: Component name (embeddings, router, grader, generator)
        
    Returns:
        Active provider name (ollama, runpod, or inference_client)
    """
    if component == "generator":
        if USE_OLLAMA:
            return "ollama"
        elif USE_INFERENCE_CLIENT:
            if USE_RUNPOD:
                return "runpod"
            else:
                return "inference_client"
        else:
            raise ValueError("No model provider enabled. Please set one of USE_OLLAMA, USE_INFERENCE_CLIENT to true.")
    else:
        if USE_OLLAMA:
            return "ollama"
        elif USE_INFERENCE_CLIENT:
            return "inference_client"
        else:
            raise ValueError("No model provider enabled. Please set one of USE_OLLAMA, USE_INFERENCE_CLIENT to true.")

def get_model_config_for_component(component: str) -> Dict[str, Any]:
    """Get model configuration for a specific component.
    
    Args:
        component: Component name (embeddings, router, grader, generator)
        
    Returns:
        Model configuration dictionary
    """
    provider = get_active_provider(component)
    
    if provider == "ollama":
        return {
            "provider": provider,
            "model": OLLAMA_MODELS[component],
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        }
    elif provider == "runpod":
        return {
            "provider": provider,
            "client": runpod_client,
            "model": os.getenv("RUNPOD_MODEL_ID", MODEL_IDS[component]),
            "api_key": os.getenv("RUNPOD_API_KEY"),
            "endpoint_id": os.getenv("RUNPOD_ENDPOINT_ID"),
            "max_tokens": int(os.getenv("RUNPOD_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("RUNPOD_TEMPERATURE", "0.2")),
            "top_p": float(os.getenv("RUNPOD_TOP_P", "0.9")),
            "top_k": int(os.getenv("RUNPOD_TOP_K", "40")),
            "presence_penalty": float(os.getenv("RUNPOD_PRESENCE_PENALTY", "0.1")),
            "frequency_penalty": float(os.getenv("RUNPOD_FREQUENCY_PENALTY", "0.1")),
            "use_vllm": os.getenv("RUNPOD_USE_VLLM", "true").lower() == "true",
            "vllm_params": {
                "max_num_batched_tokens": int(os.getenv("RUNPOD_VLLM_MAX_BATCHED_TOKENS", "4096")),
                "max_num_seqs": int(os.getenv("RUNPOD_VLLM_MAX_NUM_SEQS", "256")),
                "max_paddings": int(os.getenv("RUNPOD_VLLM_MAX_PADDINGS", "256")),
                "gpu_memory_utilization": float(os.getenv("RUNPOD_VLLM_GPU_MEMORY_UTILIZATION", "0.9")),
                "max_model_len": int(os.getenv("RUNPOD_VLLM_MAX_MODEL_LEN", "2048")),
                "quantization": os.getenv("RUNPOD_VLLM_QUANTIZATION", "awq"),
                "dtype": os.getenv("RUNPOD_VLLM_DTYPE", "float16")
            }
        }
    elif provider == "inference_client":
        return {
            "provider": provider,
            "model": os.getenv("INFERENCE_MODEL_ID", MODEL_IDS[component]),
            "api_key": os.getenv("INFERENCE_API_KEY"),
            "base_url": os.getenv("INFERENCE_BASE_URL", "https://api-inference.huggingface.co/models"),
            "max_tokens": int(os.getenv("INFERENCE_MAX_TOKENS", "2048"))
        }
    else:  # default to ollama
        return {
            "provider": "ollama",
            "model": OLLAMA_MODELS[component],
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        }
