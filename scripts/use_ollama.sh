#!/bin/bash
# Script to use Ollama as the model provider (default)

# Unset any environment variables that might be set for other providers
unset USE_INFERENCE_CLIENT
unset INFERENCE_PROVIDER
unset INFERENCE_API_KEY

# Optional: Override default models
# export OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# export OLLAMA_GRADER_MODEL=llama3:8b
# export OLLAMA_ROUTER_MODEL=llama3:8b
# export OLLAMA_GENERATOR_MODEL=codellama:7b

echo "Ollama configuration set successfully!"
echo "Provider: ollama (local)"
echo ""
echo "You can now run your application with Ollama models."
echo "Example: python -m agent.graph.app"
echo ""
echo "Make sure Ollama is running locally with the required models."
echo "You can check available models with: ollama list" 