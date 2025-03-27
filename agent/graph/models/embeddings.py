# from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientEmbeddings

# Get model configuration
config = get_model_config_for_component("embeddings")

# Initialize embeddings based on configuration
if "client" in config:
    # Use InferenceClient with third-party provider
    embeddings = InferenceClientEmbeddings(
        provider=config.get("provider", "together"),
        api_key=config["api_key"],
        model=config["model"]
    )
elif "api_key" in config:
    # Use Hugging Face
    embeddings = HuggingFaceEmbeddings(
        api_key=config["api_key"],
        model_name=config["model"]
    )
else:
    # Default to Ollama
    embeddings = OllamaEmbeddings(model=config["model"])