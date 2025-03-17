#!/bin/bash
# Script to use Together AI as the model provider

# Check if API key is provided
if [ -z "$1" ]; then
  echo "Error: Together AI API key is required"
  echo "Usage: $0 <together_ai_api_key>"
  exit 1
fi

# Export environment variables
export USE_INFERENCE_CLIENT=true
export INFERENCE_PROVIDER=together
export INFERENCE_API_KEY=$1

# Optional: Override default models
# export INFERENCE_GRADER_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
# export INFERENCE_ROUTER_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
# export INFERENCE_GENERATOR_MODEL=meta-llama/Llama-3-70b-chat

echo "Together AI configuration set successfully!"
echo "Provider: together"
echo "API Key: ${INFERENCE_API_KEY:0:5}...${INFERENCE_API_KEY: -5}"
echo ""
echo "You can now run your application with Together AI models."
echo "Example: python -m agent.graph.app" 