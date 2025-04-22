"""
Wrapper for Hugging Face InferenceClient to integrate with LangChain.

This module provides custom LangChain-compatible classes for using
Hugging Face's InferenceClient with third-party providers.
"""

from typing import Any, Dict, List, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from huggingface_hub import InferenceClient
from huggingface_hub.inference._client import ChatCompletionOutput

class InferenceClientChatModel(BaseChatModel):
    """Chat model that uses Hugging Face's InferenceClient with third-party providers."""
    
    client: InferenceClient
    model: str
    temperature: float = 0.0
    max_tokens: int = 1024
    
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        """Initialize the InferenceClientChatModel.
        
        Args:
            provider: The provider to use (e.g., "together", "perplexity", "anyscale")
            api_key: The API key for the provider
            model: The model to use
            temperature: The temperature to use for generation
            max_tokens: The maximum number of tokens to generate
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.client = InferenceClient(provider=provider, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _convert_messages_to_chat_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to the format expected by InferenceClient."""
        chat_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                chat_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                chat_messages.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                chat_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, ChatMessage):
                chat_messages.append({"role": message.role, "content": message.content})
            else:
                raise ValueError(f"Got unknown message type: {type(message)}")
        return chat_messages
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat response using the InferenceClient."""
        chat_messages = self._convert_messages_to_chat_format(messages)
        
        # Prepare parameters
        params = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        # Add stop sequences if provided
        if stop:
            params["stop"] = stop
        
        # Add any additional parameters
        params.update(kwargs)
        
        # Call the InferenceClient
        completion: ChatCompletionOutput = self.client.chat.completions.create(**params)
        
        # Extract the response
        response_message = completion.choices[0].message.content
        
        # Create a ChatGeneration object
        generation = ChatGeneration(
            message=AIMessage(content=response_message),
            generation_info={"finish_reason": completion.choices[0].finish_reason},
        )
        
        # Return the ChatResult
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "inference-client-chat-model"


class InferenceClientEmbeddings:
    """Embeddings model that uses Hugging Face's InferenceClient with third-party providers."""
    
    client: InferenceClient
    model: str
    
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        **kwargs: Any,
    ):
        """Initialize the InferenceClientEmbeddings.
        
        Args:
            provider: The provider to use (e.g., "together", "perplexity", "anyscale")
            api_key: The API key for the provider
            model: The model to use
            **kwargs: Additional keyword arguments
        """
        self.client = InferenceClient(provider=provider, api_key=api_key)
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using the InferenceClient."""
        embeddings = []
        for text in texts:
            embedding = self.client.feature_extraction(text, model=self.model)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query using the InferenceClient."""
        return self.client.feature_extraction(text, model=self.model) 