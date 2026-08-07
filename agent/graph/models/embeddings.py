from langchain_ollama import OllamaEmbeddings
from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientEmbeddings

# Get model configuration
config = get_model_config_for_component("embeddings")

# Initialize embeddings based on configuration
if config["provider"] == "inference_client":
    # Use InferenceClient with third-party provider
    embeddings = InferenceClientEmbeddings(
        provider=config.get("provider_org", "together"),
        direct_provider=config.get("direct_provider_org", "together"),
        api_key=config["api_key"],
        direct_api_key=config["direct_api_key"],
        model=config["model"],
        max_tokens=config["max_tokens"]
    )
else:
    # Default to Ollama
    embeddings = OllamaEmbeddings(model=config["model"])