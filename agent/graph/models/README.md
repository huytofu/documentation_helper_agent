# Model Configuration

This directory contains the language model configurations for the documentation helper agent. The agent supports multiple model providers including Ollama (local deployment), third-party providers via the Inference API, and RunPod for serverless inference.

## Available Models

The agent uses different models for different tasks:

1. **Embeddings** (`embeddings.py`): Used for vector embeddings of text
2. **Router** (`router.py`): Used for routing queries to the appropriate handler
3. **Graders** (`grader.py`): Several specialized graders for different evaluation types
4. **Summarizer** (`summarizer.py`): Used for summarizing content
5. **Generator** (`generator.py`): Used for generating code and documentation

## Model Provider Configuration

The agent uses a centralized configuration system that determines the appropriate model provider based on environment variables. The configuration is handled by `get_model_config_for_component()` in `config.py`.

### Provider Options

The agent offers two main provider configurations:

1. **Local Deployment (Ollama)**
   - Set `USE_OLLAMA=true` and `USE_INFERENCE_CLIENT=false`
   - All components use Ollama models running locally

2. **Cloud Deployment (Inference API)**
   - Set `USE_OLLAMA=false` and `USE_INFERENCE_CLIENT=true`
   - All components use cloud-based models via Inference API
   - Optional: Set `USE_RUNPOD=true` to use RunPod for the generator model

Note: Only one of `USE_OLLAMA` or `USE_INFERENCE_CLIENT` can be true at a time.

### Environment Variables

```bash
# Provider Selection (choose one option)
# Option 1: Local deployment
export USE_OLLAMA=true
export USE_INFERENCE_CLIENT=false
export USE_RUNPOD=false

# Option 2: Cloud deployment
export USE_OLLAMA=false
export USE_INFERENCE_CLIENT=true
export USE_RUNPOD=false  # Can be true to use RunPod for generator

# API Keys (for cloud deployment)
export INFERENCE_API_KEY=your_api_key_here
export INFERENCE_PROVIDER=together  # or "perplexity", "anyscale", etc.

# Optional: RunPod Configuration (if USE_RUNPOD=true)
export RUNPOD_API_KEY=your_api_key_here
export RUNPOD_ENDPOINT_ID=your_endpoint_id_here
```

## Default Models

### Ollama Models (Local Deployment)
- Embeddings: `qllama/bge-large-en-v1.5`
- Router: `llama3.1:latest`
- Sentiment Grader: `mistral:latest`
- Answer Grader: `mistral:latest` 
- Retrieval Grader: `llama3.1:latest`
- Hallucination Grader: `qwen2.5:14b`
- Summarizer: `qwen2.5:14b`
- Generator: `deepseek-coder:33b`

### Inference API Models (Cloud Deployment)
- Embeddings: `BAAI/bge-large-en-v1.5`
- Router: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Sentiment Grader: `mistralai/Mistral-7B-Instruct-v0.3`
- Answer Grader: `mistralai/Mistral-7B-Instruct-v0.3`
- Retrieval Grader: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Hallucination Grader: `Qwen/Qwen2.5-14B-Instruct`
- Summarizer: `Qwen/Qwen2.5-14B-Instruct`
- Generator: `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

### RunPod Models (Optional for Generator)
- Generator: `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

## Custom Wrappers

The `inference_client_wrapper.py` file contains custom LangChain-compatible wrappers for:
- Third-party providers via the Inference API (Together AI, Perplexity, Anyscale, etc.)
- The `runpod_client.py` file provides a wrapper for the RunPod serverless API

## Usage Example

```python
from .config import get_model_config_for_component

# Get configuration for a specific component
config = get_model_config_for_component("generator")

# Initialize model based on configuration
if config["provider"] == "inference_client":
    # Use Inference API
    model = InferenceClientChatModel(**config)
elif config["provider"] == "runpod":
    # Use RunPod client
    model = RunPodChatModel(client=config["client"], **config)
else:
    # Use Ollama
    model = ChatOllama(**config)
```

## Notes

1. `USE_INFERENCE_CLIENT` and `USE_OLLAMA` cannot be enabled simultaneously
2. RunPod is only available for the generator component
3. All models use temperature=0 by default for consistent outputs
4. Ollama models include optimized settings for better performance 