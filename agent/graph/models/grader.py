# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceInference
from .config import (
    USE_HUGGINGFACE, HUGGINGFACE_API_KEY, HUGGINGFACE_GRADER_MODEL, OLLAMA_GRADER_MODEL,
    USE_INFERENCE_CLIENT, INFERENCE_API_KEY, INFERENCE_PROVIDER, INFERENCE_GRADER_MODEL
)
from .inference_client_wrapper import InferenceClientChatModel

# Choose LLM based on configuration
if USE_INFERENCE_CLIENT and INFERENCE_API_KEY:
    # Use InferenceClient with third-party provider
    llm = InferenceClientChatModel(
        provider=INFERENCE_PROVIDER,
        api_key=INFERENCE_API_KEY,
        model=INFERENCE_GRADER_MODEL,
        temperature=0
    )
elif USE_HUGGINGFACE and HUGGINGFACE_API_KEY:
    # Use Hugging Face
    llm = ChatHuggingFace(
        model_id=HUGGINGFACE_GRADER_MODEL,
        huggingfacehub_api_token=HUGGINGFACE_API_KEY,
        temperature=0
    )
else:
    # Default to Ollama
    llm = ChatOllama(model=OLLAMA_GRADER_MODEL, temperature=0)

