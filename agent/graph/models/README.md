# Model Configuration

This directory contains the language model configurations for the documentation helper agent. The agent supports Ollama, Hugging Face models, and third-party providers via Hugging Face's InferenceClient.

## Available Models

The agent uses different models for different tasks:

1. **Embeddings** (`embeddings.py`): Used for vector embeddings of text
2. **Grader** (`grader.py`): Used for evaluating and grading responses
3. **Router** (`router.py`): Used for routing queries to the appropriate handler
4. **Generator** (`generator.py`): Used for generating code and documentation

## Switching Between Model Providers

You can choose between three different model providers:

### 1. Ollama (Default, Local)

No configuration needed. The agent will use Ollama models by default.

### 2. Hugging Face Models

```bash
# Use Hugging Face models
export USE_HUGGINGFACE=true
export HUGGINGFACE_API_KEY=your_api_key_here

# Optional: Customize model selections
export HUGGINGFACE_EMBEDDING_MODEL="BAAI/bge-large-en-v1.5"
export HUGGINGFACE_GRADER_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
export HUGGINGFACE_ROUTER_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
export HUGGINGFACE_GENERATOR_MODEL="codellama/CodeLlama-34b-Instruct-hf"
```

### 3. Third-Party Providers via InferenceClient

```bash
# Use InferenceClient with third-party providers
export USE_INFERENCE_CLIENT=true
export INFERENCE_API_KEY=your_api_key_here
export INFERENCE_PROVIDER=together  # or "perplexity", "anyscale", etc.

# Optional: Customize model selections
export INFERENCE_EMBEDDING_MODEL="BAAI/bge-large-en-v1.5"
export INFERENCE_GRADER_MODEL="deepseek-ai/DeepSeek-R1"
export INFERENCE_ROUTER_MODEL="deepseek-ai/DeepSeek-R1"
export INFERENCE_GENERATOR_MODEL="deepseek-ai/DeepSeek-Coder-V2"
```

## Priority Order

The agent will choose a provider in the following order:
1. InferenceClient (if `USE_INFERENCE_CLIENT=true` and `INFERENCE_API_KEY` is provided)
2. Hugging Face (if `USE_HUGGINGFACE=true` and `HUGGINGFACE_API_KEY` is provided)
3. Ollama (default)

## Default Models

### Ollama Models
- Embeddings: `deepseek-coder:33b`
- Grader: `llama3.3:70b`
- Router: `llama3.3:70b`
- Generator: `deepseek-coder:33b`

### Hugging Face Models
- Embeddings: `BAAI/bge-large-en-v1.5`
- Grader: `mistralai/Mistral-7B-Instruct-v0.2`
- Router: `mistralai/Mistral-7B-Instruct-v0.2`
- Generator: `codellama/CodeLlama-34b-Instruct-hf`

### InferenceClient Models (Third-Party Providers)
- Embeddings: `BAAI/bge-large-en-v1.5`
- Grader: `deepseek-ai/DeepSeek-R1`
- Router: `deepseek-ai/DeepSeek-R1`
- Generator: `deepseek-ai/DeepSeek-Coder-V2`

## Configuration

All model configuration is centralized in `config.py`. If you need to change default models or add new configuration options, modify this file.

## Custom Wrappers

The `inference_client_wrapper.py` file contains custom LangChain-compatible wrappers for the Hugging Face InferenceClient, allowing seamless integration with third-party providers like Together AI, Perplexity, Anyscale, and others. 