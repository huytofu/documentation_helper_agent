"""RunPod client configuration for serverless vLLM inference."""

import os
import aiohttp
from typing import Dict, Any, Optional
import logging
from asyncio import sleep as async_sleep

logger = logging.getLogger(__name__)

class RunPodClient:
    """Client for interacting with RunPod serverless vLLM endpoints."""
    
    def __init__(
        self,
        api_key: str,
        endpoint_id: str,
        model_id: str = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        max_tokens: int = 2048,
        temperature: float = 0.2,
        top_p: float = 0.9,
        top_k: int = 40,
        presence_penalty: float = 0.1,
        frequency_penalty: float = 0.1,
        use_vllm: bool = True,
        trust_remote_code: bool = True
    ):
        """Initialize RunPod client.
        
        Args:
            api_key: RunPod API key
            endpoint_id: RunPod endpoint ID
            model_id: Model ID to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            presence_penalty: Presence penalty
            frequency_penalty: Frequency penalty
            use_vllm: Whether to use vLLM for faster inference
            trust_remote_code: Whether to trust remote code (needed for models like DeepSeek)
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.use_vllm = use_vllm
        self.trust_remote_code = trust_remote_code
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using RunPod serverless vLLM endpoint.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters to override defaults
            
        Returns:
            Generated text and metadata
        """
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request payload with vLLM optimizations
        payload = {
            "input": {
                "messages": messages,
                "model": self.model_id,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "top_k": kwargs.get("top_k", self.top_k),
                "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
                "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
                "use_vllm": self.use_vllm,
                "serverless": True,
                "trust_remote_code": self.trust_remote_code,
                "vllm_params": {
                    "max_num_batched_tokens": 4096,
                    "max_num_seqs": 256,
                    "max_paddings": 256,
                    "disable_log_stats": True,
                    "gpu_memory_utilization": 0.9,
                    "max_model_len": 2048,
                    "quantization": "awq",  # Use AWQ quantization for better performance
                    "dtype": "float16",     # Use float16 for better memory efficiency
                    "seed": 42,
                    "worker_use_ray": False,
                    "disable_log_requests": True,
                    "trust_remote_code": self.trust_remote_code
                }
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Start generation
                async with session.post(
                    f"{self.base_url}/run",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"RunPod API error: {error_text}")
                        raise Exception(f"RunPod API error: {error_text}")
                    
                    result = await response.json()
                    job_id = result["id"]
                
                # Poll for completion with exponential backoff
                backoff = 1
                max_backoff = 10
                while True:
                    async with session.get(
                        f"{self.base_url}/status/{job_id}",
                        headers=self.headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"RunPod status error: {error_text}")
                            raise Exception(f"RunPod status error: {error_text}")
                        
                        status = await response.json()
                        if status["status"] == "COMPLETED":
                            return status["output"]
                        elif status["status"] == "FAILED":
                            raise Exception(f"RunPod job failed: {status.get('error', 'Unknown error')}")
                        
                        # Exponential backoff
                        await async_sleep(backoff)
                        backoff = min(backoff * 2, max_backoff)
        
        except Exception as e:
            logger.error(f"Error in RunPod generation: {str(e)}")
            raise
    
    @classmethod
    def from_env(cls) -> "RunPodClient":
        """Create RunPod client from environment variables."""
        return cls(
            api_key=os.getenv("RUNPOD_API_KEY"),
            endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID"),
            model_id=os.getenv("RUNPOD_MODEL_ID", "deepseek-ai/deepseek-coder-v2-instruct"),
            max_tokens=int(os.getenv("RUNPOD_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("RUNPOD_TEMPERATURE", "0.2")),
            top_p=float(os.getenv("RUNPOD_TOP_P", "0.9")),
            top_k=int(os.getenv("RUNPOD_TOP_K", "40")),
            presence_penalty=float(os.getenv("RUNPOD_PRESENCE_PENALTY", "0.1")),
            frequency_penalty=float(os.getenv("RUNPOD_FREQUENCY_PENALTY", "0.1")),
            use_vllm=os.getenv("RUNPOD_USE_VLLM", "true").lower() == "true",
            trust_remote_code=os.getenv("RUNPOD_TRUST_REMOTE_CODE", "true").lower() == "true"
        ) 