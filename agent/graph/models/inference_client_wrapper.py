"""
Wrapper for Hugging Face InferenceClient to integrate with LangChain.

This module provides custom LangChain-compatible classes for using
Hugging Face's InferenceClient with third-party providers.
"""

import logging
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

# Configure logging
logger = logging.getLogger(__name__)

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
        self.provider = provider
        logger.info(f"Initialized InferenceClientChatModel with provider: {provider}, model: {model}")
    
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
        """Generate a chat response using the InferenceClient.
        
        Args:
            messages: List of messages to generate a response for
            stop: Optional list of stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            ChatResult containing the generated response
            
        Raises:
            RuntimeError: If the API call fails
        """
        chat_messages = self._convert_messages_to_chat_format(messages)
        
        # Prepare parameters - optimized for Together AI compatibility
        params = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }
        
        # Add provider-specific parameters
        if self.provider.lower() == "together":
            # Together AI specific parameters
            params.update({
                "top_p": kwargs.get("top_p", 0.9),
                "repetition_penalty": kwargs.get("repetition_penalty", 1.1),
                "stop_sequences": stop if stop else None,
            })
        else:
            # Generic parameters for other providers
            if stop:
                params["stop"] = stop
        
        # Add any additional parameters from kwargs
        for k, v in kwargs.items():
            if k not in params:
                params[k] = v
        
        try:
            # Log request for debugging
            logger.debug(f"Sending request to {self.provider} with model {self.model}")
            
            # Call the InferenceClient
            completion: ChatCompletionOutput = self.client.chat.completions.create(**params)
            
            # Verify we have choices before accessing
            if not completion.choices:
                raise ValueError(f"No choices returned from {self.provider} API")
                
            # Extract the response
            response_message = completion.choices[0].message.content
            finish_reason = getattr(completion.choices[0], "finish_reason", "unknown")
            
            # Log successful completion
            logger.debug(f"Received response from {self.provider} API: {finish_reason}")
            
            # Create a ChatGeneration object
            generation = ChatGeneration(
                message=AIMessage(content=response_message),
                generation_info={"finish_reason": finish_reason},
            )
            
            # Return the ChatResult
            return ChatResult(generations=[generation])
            
        except Exception as e:
            # Log the error
            logger.error(f"Error calling {self.provider} API: {str(e)}")
            
            # Pass error to callback manager if available
            if run_manager:
                run_manager.on_llm_error(e, **kwargs)
                
            # Raise a more informative exception
            raise RuntimeError(f"Failed to generate response from {self.provider} API: {str(e)}")
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return f"inference-client-{self.provider}-chat-model"


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
        self.provider = provider
        logger.info(f"Initialized InferenceClientEmbeddings with provider: {provider}, model: {model}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using the InferenceClient."""
        embeddings = []
        try:
            for text in texts:
                embedding = self.client.feature_extraction(text, model=self.model)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error(f"Error embedding documents with {self.provider} API: {str(e)}")
            raise RuntimeError(f"Failed to embed documents with {self.provider} API: {str(e)}")
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query using the InferenceClient."""
        try:
            return self.client.feature_extraction(text, model=self.model)
        except Exception as e:
            logger.error(f"Error embedding query with {self.provider} API: {str(e)}")
            raise RuntimeError(f"Failed to embed query with {self.provider} API: {str(e)}") 