#!/bin/bash
# Script to use Perplexity AI as the model provider

# Check if API key is provided
if [ -z "$1" ]; then
  echo "Error: Perplexity AI API key is required"
  echo "Usage: $0 <perplexity_ai_api_key>"
  exit 1
fi

# Export environment variables
export USE_INFERENCE_CLIENT=true
export INFERENCE_PROVIDER=perplexity
export INFERENCE_API_KEY=$1

# Optional: Override default models
# export INFERENCE_GRADER_MODEL=pplx/llama-3-8b-instruct
# export INFERENCE_ROUTER_MODEL=pplx/llama-3-8b-instruct
# export INFERENCE_GENERATOR_MODEL=pplx/codellama-34b-instruct

echo "Perplexity AI configuration set successfully!"
echo "Provider: perplexity"
echo "API Key: ${INFERENCE_API_KEY:0:5}...${INFERENCE_API_KEY: -5}"
echo ""
echo "You can now run your application with Perplexity AI models."
echo "Example: python -m agent.graph.app" 