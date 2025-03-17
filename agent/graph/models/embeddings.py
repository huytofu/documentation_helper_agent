# from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface import HuggingFaceInferenceAPIEmbeddings
from .config import (
    USE_HUGGINGFACE, HUGGINGFACE_API_KEY, HUGGINGFACE_EMBEDDING_MODEL, OLLAMA_EMBEDDING_MODEL,
    USE_INFERENCE_CLIENT, INFERENCE_API_KEY, INFERENCE_PROVIDER, INFERENCE_EMBEDDING_MODEL
)
from .inference_client_wrapper import InferenceClientEmbeddings

# Choose embeddings model based on configuration
if USE_INFERENCE_CLIENT and INFERENCE_API_KEY:
    # Use InferenceClient with third-party provider
    embeddings = InferenceClientEmbeddings(
        provider=INFERENCE_PROVIDER,
        api_key=INFERENCE_API_KEY,
        model=INFERENCE_EMBEDDING_MODEL
    )
elif USE_HUGGINGFACE and HUGGINGFACE_API_KEY:
    # Use Hugging Face
    embeddings = HuggingFaceInferenceAPIEmbeddings(
        api_key=HUGGINGFACE_API_KEY,
        model_name=HUGGINGFACE_EMBEDDING_MODEL
    )
else:
    # Default to Ollama
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL)