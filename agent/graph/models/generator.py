# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from .config import get_model_config_for_component
from .inference_client_wrapper import InferenceClientChatModel
from langchain.chat_models.base import BaseChatModel
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ChatResult,
    ChatGeneration,
)
from typing import Any, List, Mapping, Optional, Iterator, Dict, Union, cast

class RunPodChatModel(BaseChatModel):
    """Chat model that uses RunPod API through the RunPodClient."""
    
    client: Any  # RunPodClient instance
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    presence_penalty: float = 0.1
    frequency_penalty: float = 0.1
    
    def __init__(
        self,
        client: Any,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        top_k: int = 40,
        presence_penalty: float = 0.1,
        frequency_penalty: float = 0.1,
        **kwargs
    ):
        """Initialize the RunPodChatModel."""
        super().__init__(**kwargs)
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
    
    @property
    def _llm_type(self) -> str:
        """Return the type of this LLM."""
        return "runpod-chat"
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert messages to a prompt string."""
        prompt = ""
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt += f"<|system|>\n{message.content}</s>\n"
            elif isinstance(message, HumanMessage):
                prompt += f"<|user|>\n{message.content}</s>\n"
            elif isinstance(message, AIMessage):
                prompt += f"<|assistant|>\n{message.content}</s>\n"
            else:
                prompt += f"{message.content}\n"
        prompt += "<|assistant|>\n"
        return prompt
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """Generate a response from the RunPod client."""
        prompt = self._convert_messages_to_prompt(messages)
        
        # Call the RunPod client
        response = self.client.generate(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stop=stop,
            **kwargs
        )
        
        # Extract the generated text from the response
        if hasattr(response, 'generated_text'):
            text = response.generated_text
        elif isinstance(response, dict) and 'generated_text' in response:
            text = response['generated_text']
        else:
            text = str(response)
        
        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
        
# Get model configuration
config = get_model_config_for_component("generator")

# Initialize LLM based on configuration
if config["provider"] == "inference_client":
    # Use InferenceClient with third-party provider
    llm = InferenceClientChatModel(
        provider=config.get("provider_org", "together"),
        api_key=config["api_key"],
        direct_api_key=config["direct_api_key"],
        model=config["model"],
        temperature=0,
        max_tokens=config["max_tokens"]
    )
elif config["provider"] == "runpod":
    # Initialize the RunPod chat model with the client from config
    llm = RunPodChatModel(
        client=config["client"],
        model=config["model"],
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 2048),
        top_p=config.get("top_p", 0.9),
        top_k=config.get("top_k", 40),
        presence_penalty=config.get("presence_penalty", 0.1),
        frequency_penalty=config.get("frequency_penalty", 0.1),
    )
else:
    # Default to Ollama
    llm = ChatOllama(model=config["model"], temperature=0)

