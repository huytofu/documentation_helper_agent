# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace
from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientChatModel

# Get model configuration
config = get_model_config_for_component("retrieval_grader")

# Initialize LLM based on configuration
if "client" in config:
    # Use InferenceClient with third-party provider
    llm = InferenceClientChatModel(
        provider=config.get("provider", "together"),
        api_key=config["api_key"],
        model=config["model"],
        temperature=0
    )
elif "api_key" in config:
    # Use Hugging Face
    llm = ChatHuggingFace(
        model_id=config["model"],
        huggingfacehub_api_token=config["api_key"],
        temperature=0
    )
else:
    # Default to Ollama
    llm = ChatOllama(model=config["model"], temperature=0)

