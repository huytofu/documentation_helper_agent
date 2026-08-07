from langchain_ollama import ChatOllama

from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientChatModel

config = get_model_config_for_component("chub_expert")

if config["provider"] == "inference_client":
    llm = InferenceClientChatModel(
        provider=config.get("provider_org", "together"),
        direct_provider=config.get("direct_provider_org", "together"),
        api_key=config["api_key"],
        direct_api_key=config["direct_api_key"],
        model=config["model"],
        temperature=0,
        max_tokens=config["max_tokens"],
    )
else:
    llm = ChatOllama(model=config["model"], temperature=0)
