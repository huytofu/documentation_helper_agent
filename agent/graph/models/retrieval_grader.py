# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientChatModel

# Get model configuration
config = get_model_config_for_component("retrieval_grader")

# Initialize LLM based on configuration
if config["provider"] == "inference_client":
    # Use InferenceClient with third-party provider
    llm = InferenceClientChatModel(
        provider=config.get("provider_org", "together"),
        api_key=config["api_key"],
        model=config["model"],
        temperature=0,
        max_tokens=config["max_tokens"]
    )
else:
    # Default to Ollama
    llm = ChatOllama(model=config["model"], temperature=0)

