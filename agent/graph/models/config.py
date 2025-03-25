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

    USE_RUNPOD: Set to "true" to use RunPod
    RUNPOD_API_KEY: RunPod API key
    RUNPOD_ENDPOINT_ID: RunPod endpoint ID
    RUNPOD_MODEL_ID: RunPod model ID
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

# Global configuration
# Determine if Hugging Face models should be used
USE_HUGGINGFACE = os.environ.get("USE_HUGGINGFACE", "true").lower() == "true"
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# Third-party provider configuration via InferenceClient
# Determine if InferenceClient should be used
USE_INFERENCE_CLIENT = os.environ.get("USE_INFERENCE_CLIENT", "false").lower() == "true"
INFERENCE_PROVIDER = os.environ.get("INFERENCE_PROVIDER", "together")
INFERENCE_API_KEY = os.environ.get("INFERENCE_API_KEY", "")

# RunPod Configuration
USE_RUNPOD = os.environ.get("USE_RUNPOD", "true").lower() == "true"  # Default to true
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_MODEL_ID = os.getenv("RUNPOD_MODEL_ID", "deepseek-ai/deepseek-coder-v2-instruct")

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
OLLAMA_EMBEDDING_MODEL = "qllama/bge-large-en-v1.5"
OLLAMA_GRADER_MODEL = "llama3.3:70b"
OLLAMA_ROUTER_MODEL = "llama3.3:70b"
OLLAMA_GENERATOR_MODEL = "deepseek-coder:33b"

# Concurrency settings - optimized for low/medium volume
PROVISIONED_CONCURRENCY = int(os.environ.get("PROVISIONED_CONCURRENCY", "1"))
CONCURRENCY_LIMIT = int(os.environ.get("CONCURRENCY_LIMIT", "5"))  # Reduced for low/medium volume

# Create thread pool for concurrent operations
thread_pool = ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT)

# Create semaphore for limiting concurrent requests
concurrency_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# Initialize RunPod client if enabled
runpod_client: Optional[RunPodClient] = None
if USE_RUNPOD and RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID:
    runpod_client = RunPodClient.from_env()

# Model configurations
MODEL_CONFIGS = {
    "embeddings": {
        "huggingface": {
            "model": HUGGINGFACE_EMBEDDING_MODEL,
            "api_key": HUGGINGFACE_API_KEY
        }
    },
    "grader": {
        "huggingface": {
            "model": HUGGINGFACE_GRADER_MODEL,
            "api_key": HUGGINGFACE_API_KEY
        }
    },
    "router": {
        "huggingface": {
            "model": HUGGINGFACE_ROUTER_MODEL,
            "api_key": HUGGINGFACE_API_KEY
        }
    },
    "generator": {
        "huggingface": {
            "model": HUGGINGFACE_GENERATOR_MODEL,
            "api_key": HUGGINGFACE_API_KEY
        },
        "runpod": {
            "model": RUNPOD_MODEL_ID,
            "client": runpod_client
        }
    }
}

def get_inference_client() -> Optional[InferenceClient]:
    """
    Get a configured InferenceClient for third-party providers.
    
    Returns:
        Optional[InferenceClient]: Configured client if provider and API key are set
    """
    if not USE_INFERENCE_CLIENT or not INFERENCE_API_KEY:
        return None
        
    return InferenceClient(
        model=INFERENCE_PROVIDER,
        token=INFERENCE_API_KEY,
        timeout=30,
        max_retries=3,
        retry_on_failure=True,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )

def get_model_config() -> Dict[str, Any]:
    """
    Returns the current model configuration based on environment settings.
    
    Returns:
        dict: A dictionary containing the current model configuration.
    """
    # For low/medium volume, prefer Hugging Face Inference API
    provider = "huggingface" if USE_HUGGINGFACE and HUGGINGFACE_API_KEY else "ollama"
    
    # Get the appropriate models based on the provider
    if provider == "huggingface":
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
        "models": models,
        "provisioned_concurrency": PROVISIONED_CONCURRENCY,
        "concurrency_limit": CONCURRENCY_LIMIT
    }

def get_huggingface_model(model_id: str, task: str = "text-generation") -> Any:
    """
    Get a Hugging Face model optimized for serverless deployment.
    
    Args:
        model_id: The Hugging Face model ID
        task: The task type (text-generation, text2text-generation, etc.)
        
    Returns:
        A configured Hugging Face model instance
    """
    # Configure callbacks for better monitoring
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    
    # Configure model parameters for serverless optimization
    model_kwargs = {
        "temperature": 0.2,
        "max_new_tokens": 512,
        "top_p": 0.9,
        "top_k": 40,
        "repetition_penalty": 1.1,
        "do_sample": True,
        "use_cache": True,
        "return_full_text": False,
        "timeout": 30,
        "max_retries": 3,
        "retry_on_failure": True,
        "cache_dir": "/tmp/huggingface",  # Use /tmp for serverless
        "local_files_only": False,
        "trust_remote_code": True,
        "device_map": "auto",
        "torch_dtype": "auto",
        "low_cpu_mem_usage": True,
        "offload_folder": "/tmp/offload",  # Use /tmp for serverless
        "offload_state_dict": True,
        "load_in_8bit": True,
        "load_in_4bit": True,
        "quantization_config": {
            "load_in_4bit": True,
            "bnb_4bit_compute_dtype": "float16",
            "bnb_4bit_use_double_quant": True,
            "bnb_4bit_quant_type": "nf4",
        }
    }
    
    # Create model based on task type
    if task == "text-generation":
        return ChatHuggingFace(
            repo_id=model_id,
            task=task,
            model_kwargs=model_kwargs,
            huggingfacehub_api_token=HUGGINGFACE_API_KEY,
            callback_manager=callback_manager,
            streaming=True,
            verbose=True,
            max_retries=3,
            timeout=30,
            retry_on_failure=True,
            cache_dir="/tmp/huggingface",  # Use /tmp for serverless
            local_files_only=False,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype="auto",
            low_cpu_mem_usage=True,
            offload_folder="/tmp/offload",  # Use /tmp for serverless
            offload_state_dict=True,
            load_in_8bit=True,
            load_in_4bit=True,
            quantization_config={
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            }
        )
    else:
        return HuggingFaceHub(
            repo_id=model_id,
            task=task,
            model_kwargs=model_kwargs,
            huggingfacehub_api_token=HUGGINGFACE_API_KEY,
            callback_manager=callback_manager,
            streaming=True,
            verbose=True,
            max_retries=3,
            timeout=30,
            retry_on_failure=True,
            cache_dir="/tmp/huggingface",  # Use /tmp for serverless
            local_files_only=False,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype="auto",
            low_cpu_mem_usage=True,
            offload_folder="/tmp/offload",  # Use /tmp for serverless
            offload_state_dict=True,
            load_in_8bit=True,
            load_in_4bit=True,
            quantization_config={
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            }
        )

def get_huggingface_embeddings() -> HuggingFaceInferenceAPIEmbeddings:
    """
    Get Hugging Face embeddings optimized for serverless deployment.
    
    Returns:
        A configured HuggingFaceInferenceAPIEmbeddings instance
    """
    return HuggingFaceInferenceAPIEmbeddings(
        api_key=HUGGINGFACE_API_KEY,
        model_name=HUGGINGFACE_EMBEDDING_MODEL,
        model_kwargs={
            "device": "cpu",
            "torch_dtype": "auto",
            "low_cpu_mem_usage": True,
            "offload_folder": "/tmp/offload",  # Use /tmp for serverless
            "offload_state_dict": True,
            "load_in_8bit": True,
            "load_in_4bit": True,
            "quantization_config": {
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            }
        },
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 32,
            "max_retries": 3,
            "timeout": 30,
            "retry_on_failure": True,
        },
        cache_dir="/tmp/huggingface",  # Use /tmp for serverless
        local_files_only=False,
        trust_remote_code=True,
    )

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

def get_ollama_config():
    """Get Ollama configuration with optimized settings."""
    return {
        "model": "mistral:7b-q4_K_M",  # Use quantized model
        "num_ctx": 2048,  # Reduced context window
        "num_gpu": 1,  # Use GPU if available
        "num_thread": 8,  # Match CPU cores
        "temperature": 0.2,  # Lower temperature for faster, more focused responses
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 512,  # Limit response length
        "repeat_penalty": 1.1,
        "seed": 42,
        "timeout": 30,
        "num_keep": 5,  # Keep fewer tokens in context
        "stop": ["</s>", "Human:", "Assistant:"],  # Stop tokens for faster completion
        "tfs_z": 0.7,  # Tail free sampling
        "num_batch": 512,  # Batch size for processing
        "rope_scaling": {"type": "linear", "factor": 1.0},  # ROPE scaling for better performance
        "rope_freq_base": 10000,
        "rope_freq_scale": 1.0,
        "mirostat": 2,  # Enable mirostat for better sampling
        "mirostat_tau": 5.0,
        "mirostat_eta": 0.1,
        "penalize_newline": True,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.1,
        "typical_p": 0.9,
        "tiktoken_encoding": "cl100k_base",
        "num_parallel": 1,  # Disable parallel processing for faster single responses
        "num_beam": 1,  # Disable beam search for faster inference
    }

def get_ollama_model():
    """Get Ollama model with optimized settings."""
    config = get_ollama_config()
    return ChatOllama(
        model=config["model"],
        num_ctx=config["num_ctx"],
        num_gpu=config["num_gpu"],
        num_thread=config["num_thread"],
        temperature=config["temperature"],
        top_p=config["top_p"],
        top_k=config["top_k"],
        num_predict=config["num_predict"],
        repeat_penalty=config["repeat_penalty"],
        seed=config["seed"],
        timeout=config["timeout"],
        num_keep=config["num_keep"],
        stop=config["stop"],
        tfs_z=config["tfs_z"],
        num_batch=config["num_batch"],
        rope_scaling=config["rope_scaling"],
        rope_freq_base=config["rope_freq_base"],
        rope_freq_scale=config["rope_freq_scale"],
        mirostat=config["mirostat"],
        mirostat_tau=config["mirostat_tau"],
        mirostat_eta=config["mirostat_eta"],
        penalize_newline=config["penalize_newline"],
        presence_penalty=config["presence_penalty"],
        frequency_penalty=config["frequency_penalty"],
        typical_p=config["typical_p"],
        tiktoken_encoding=config["tiktoken_encoding"],
        num_parallel=config["num_parallel"],
        num_beam=config["num_beam"],
    )

# Get active provider for each component
def get_active_provider(component: str) -> str:
    """Get the active provider for a component based on configuration."""
    if component == "generator" and USE_RUNPOD and runpod_client:
        return "runpod"
    elif USE_HUGGINGFACE:
        return "huggingface"
    else:
        raise ValueError(f"No active provider configured for {component}")

# Get model configuration for a component
def get_model_config(component: str) -> dict:
    """Get the model configuration for a component."""
    provider = get_active_provider(component)
    return MODEL_CONFIGS[component][provider] 