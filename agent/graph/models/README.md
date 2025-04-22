# Model Configuration

This directory contains the language model configurations for the documentation helper agent. The agent supports multiple model providers including Ollama, Hugging Face models, third-party providers via Hugging Face's InferenceClient, and RunPod for serverless inference.

## Available Models

The agent uses different models for different tasks:

1. **Embeddings** (`embeddings.py`): Used for vector embeddings of text
2. **Grader** (`grader.py`): Used for evaluating and grading responses
3. **Router** (`router.py`): Used for routing queries to the appropriate handler
4. **Generator** (`generator.py`): Used for generating code and documentation

## Model Provider Configuration

The agent uses a centralized configuration system that determines the appropriate model provider based on environment variables. The configuration is handled by `get_model_config_for_component()` in `config.py`.

### Priority Order

The agent will choose a provider in the following order:
1. Ollama (if `USE_OLLAMA=true`)
2. InferenceClient (if `USE_INFERENCE_CLIENT=true` and `INFERENCE_API_KEY` is provided)
3. RunPod (if `USE_RUNPOD=true` and `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are provided, only for generator)
4. Hugging Face (default)

### Environment Variables

```bash
# Core Provider Flags
export USE_OLLAMA=false
export USE_HUGGINGFACE=true
export USE_INFERENCE_CLIENT=false
export USE_RUNPOD=false

# API Keys
export HUGGINGFACE_API_KEY=your_api_key_here
export INFERENCE_API_KEY=your_api_key_here
export RUNPOD_API_KEY=your_api_key_here
export RUNPOD_ENDPOINT_ID=your_endpoint_id_here

# Optional: Customize model selections
export INFERENCE_PROVIDER=together  # or "perplexity", "anyscale", etc.
```

## Default Models

### Ollama Models
- Embeddings: `qllama/bge-large-en-v1.5`
- Router: `llama3.3:70b`
- Grader: `llama3.3:70b`
- Generator: `deepseek-coder:33b`

### Hugging Face Models
- Embeddings: `BAAI/bge-large-en-v1.5`
- Router: `meta-llama/Llama-3-70b-chat-hf`
- Grader: `meta-llama/Llama-3-70b-chat-hf`
- Generator: `deepseek-ai/deepseek-coder-v2-instruct`

### InferenceClient Models (Third-Party Providers)
- Embeddings: `BAAI/bge-large-en-v1.5`
- Router: `meta-llama/Llama-3-70b-chat-hf`
- Grader: `meta-llama/Llama-3-70b-chat-hf`
- Generator: `deepseek-ai/deepseek-coder-v2-instruct`

### RunPod Models
- Generator: `deepseek-ai/deepseek-coder-v2-instruct` (default)

## Model Configuration

All model configuration is centralized in `config.py`. The `get_model_config_for_component()` function handles:
1. Provider selection based on environment variables
2. Model selection for each component
3. API key and client configuration
4. Ollama-specific settings

## Custom Wrappers

The `inference_client_wrapper.py` file contains custom LangChain-compatible wrappers for:
- Hugging Face's InferenceClient
- Third-party providers (Together AI, Perplexity, Anyscale, etc.)
- RunPod serverless endpoints

## Usage Example

```python
from .config import get_model_config_for_component

# Get configuration for a specific component
config = get_model_config_for_component("generator")

# Initialize model based on configuration
if "client" in config:
    # Use InferenceClient or RunPod
    model = InferenceClientChatModel(**config)
elif "api_key" in config:
    # Use Hugging Face
    model = ChatHuggingFace(**config)
else:
    # Use Ollama
    model = ChatOllama(**config)
```

## Notes

1. `USE_HUGGINGFACE` and `USE_OLLAMA` cannot be enabled simultaneously
2. RunPod is only available for the generator component
3. All models use temperature=0 for consistent outputs
4. Ollama models include optimized settings for better performance 