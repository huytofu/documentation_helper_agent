# Model Provider Scripts

This directory contains scripts to easily switch between different model providers for the documentation helper agent.

## Available Scripts

### 1. `use_ollama.sh`

Switch to using Ollama (local) models.

```bash
# Make the script executable
chmod +x use_ollama.sh

# Run the script
./use_ollama.sh
```

### 2. `use_together_ai.sh`

Switch to using Together AI as the model provider.

```bash
# Make the script executable
chmod +x use_together_ai.sh

# Run the script with your API key
./use_together_ai.sh your_together_ai_api_key
```

### 3. `use_perplexity_ai.sh`

Switch to using Perplexity AI as the model provider.

```bash
# Make the script executable
chmod +x use_perplexity_ai.sh

# Run the script with your API key
./use_perplexity_ai.sh your_perplexity_ai_api_key
```

## Customizing Models

Each script includes commented-out lines that you can uncomment to override the default models. For example, in `use_together_ai.sh`:

```bash
# Optional: Override default models
# export INFERENCE_GRADER_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
# export INFERENCE_ROUTER_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
# export INFERENCE_GENERATOR_MODEL=meta-llama/Llama-3-70b-chat
```

## Adding New Providers

To add support for a new provider, create a new script following the pattern of the existing scripts. Make sure to:

1. Set `USE_INFERENCE_CLIENT=true`
2. Set `INFERENCE_PROVIDER` to the appropriate provider name
3. Set `INFERENCE_API_KEY` to the provided API key
4. Optionally, override the default models

## Running the Application

After running one of these scripts, you can start the application with:

```bash
python -m agent.graph.app
```

The application will use the model provider specified by the script. 