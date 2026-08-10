"""
Configuration settings for language models.

This module provides a centralized place to configure model settings,
including switching between Ollama, Hugging Face models, and third-party providers.

Environment Variables:
    USE_OLLAMA: Set to "true" to use Ollama models (default: false)
    USE_INFERENCE_CLIENT: Set to "true" to use Together-primary + HF-fallback inference
    USE_RUNPOD: Set to "true" to use RunPod for generator model

    INFERENCE_API_KEY: Hugging Face API key (used for HF fallback InferenceClient)
    INFERENCE_DIRECT_API_KEY: Together API key (primary path)
    TOGETHER_TIMEOUT_SECONDS: Together primary-path timeout in seconds (default: 15)
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
# Format: [Together AI direct primary ID, HF Hub ID (routed via InferenceClient fallback)]
# Primary path is always Together direct. HF fallback uses PROVIDER_IDS (never "together").
MODEL_IDS = {
    "embeddings": ["intfloat/multilingual-e5-large-instruct", "intfloat/multilingual-e5-large-instruct"],
    "router": ["openai/gpt-oss-20b", "openai/gpt-oss-20b"],
    "sentiment_grader": ["openai/gpt-oss-20b", "openai/gpt-oss-20b"],
    "answer_grader": ["openai/gpt-oss-20b", "openai/gpt-oss-20b"],
    "retrieval_grader": ["openai/gpt-oss-20b", "openai/gpt-oss-20b"],
    # gpt-oss-120b on both paths (Together primary, HF provider fallback).
    "complex_router": ["openai/gpt-oss-120b", "openai/gpt-oss-120b"],
    "hallucinate_grader": ["openai/gpt-oss-120b", "openai/gpt-oss-120b"],
    "summarizer": ["openai/gpt-oss-120b", "openai/gpt-oss-120b"],
    "chitchat": ["openai/gpt-oss-120b", "openai/gpt-oss-120b"],
    "chub_expert": ["openai/gpt-oss-120b", "openai/gpt-oss-120b"],
    # Primary: DeepSeek V4 Flash on Together serverless — 284B/13B active, 1M context.
    # Fallback: coding-specialized Qwen MoE (235B/22B active) via HF → Nebius.
    "generator": ["deepseek-ai/DeepSeek-V4-Flash-0731", "Qwen/Qwen3-235B-A22B-Instruct-2507"],
}

# HF InferenceClient fallback providers only — never "together" (primary already failed).
# Placeholder values (fireworks-ai / novita / hf-inference) may be revised later.
PROVIDER_IDS = {
    "embeddings": "hf-inference",
    "sentiment_grader": "novita",
    "answer_grader": "novita",
    "retrieval_grader": "novita",
    "router": "novita",
    "chub_expert": "novita",
    "hallucinate_grader": "fireworks-ai",
    "summarizer": "fireworks-ai",
    "chitchat": "fireworks-ai",
    "complex_router": "fireworks-ai",
    "generator": "nebius",
}

if any((p or "").lower() == "together" for p in PROVIDER_IDS.values()):
    raise ValueError(
        "PROVIDER_IDS must not include 'together'; HF fallback cannot use the primary path"
    )

TOGETHER_TIMEOUT_SECONDS = float(os.environ.get("TOGETHER_TIMEOUT_SECONDS", "15"))
# Ollama model names
OLLAMA_MODELS = {
    "embeddings": "qllama/bge-large-en-v1.5",
    "router": "mistral:latest",
    "chub_expert": "mistral:latest",
    "sentiment_grader": "mistral:latest",
    "answer_grader": "mistral:latest",
    "retrieval_grader": "mistral:latest",
    # "hallucinate_grader": "llama3.1:latest",
    # "summarizer": "llama3.1:latest",
    "hallucinate_grader": "llama3.3:latest",
    "summarizer": "llama3.3:latest",
    "chitchat": "llama3.3:latest",
    "complex_router": "llama3.3:latest",
    # "router": "llama3.3:latest",
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
            # HF InferenceClient fallback provider (never "together")
            "provider_org": PROVIDER_IDS[component],
            # Together is always the primary direct path
            "direct_provider_org": "together",
            "model": MODEL_IDS[component],
            "api_key": os.getenv("INFERENCE_API_KEY"),
            "direct_api_key": os.getenv("INFERENCE_DIRECT_API_KEY"),
            "base_url": os.getenv("INFERENCE_BASE_URL", "https://api-inference.huggingface.co/models"),
            "max_tokens": int(os.getenv("INFERENCE_MAX_TOKENS", "2048")),
            "together_timeout": TOGETHER_TIMEOUT_SECONDS,
        }
    else:  # default to ollama
        return {
            "provider": "ollama",
            "model": OLLAMA_MODELS[component],
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        }
