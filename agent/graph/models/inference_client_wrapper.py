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
import requests
import json
from together import Together
import os

# Configure logging
logger = logging.getLogger(__name__)

class InferenceClientChatModel(BaseChatModel):
    """Chat model that uses Hugging Face's InferenceClient with third-party providers."""
    
    client: InferenceClient
    model: str
    direct_model: str
    temperature: float = 0.0
    max_tokens: int = 1024
    provider: str = ""
    direct_provider: str = ""
    direct_api_key: str
    
    def __init__(
        self,
        provider: str,
        direct_provider: str,
        api_key: str, #This is Hugging Face API key
        direct_api_key: str, #This is direct API key for the provider like Together AI
        model: List[str],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        """Initialize the InferenceClientChatModel.
        
        Args:
            provider: The provider to use (e.g., "together", "perplexity", "anyscale")
            api_key: The API key for the provider
            model: The model to use (should be a list of two models, the first is for the InferenceClient and the second is for the Together AI direct API)
            temperature: The temperature to use for generation
            max_tokens: The maximum number of tokens to generate
            **kwargs: Additional keyword arguments
        """
        # Create client first
        client = InferenceClient(
            provider=provider, 
            api_key=api_key, 
            headers={"X-wait-for-model": "true"})
        
        # Include all parameters in kwargs for proper Pydantic validation
        all_kwargs = {
            "client": client,
            "model": model[0],
            "direct_model": model[1],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": provider,
            "direct_provider": direct_provider,
            "direct_api_key": direct_api_key,
            **kwargs
        }
        
        # Initialize with all parameters
        super().__init__(**all_kwargs)
        logger.info(f"Initialized InferenceClientChatModel with provider: {provider}, model: {model[0]} and {model[1]}")
    
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
                "frequency_penalty": kwargs.get("frequency_penalty", 1.1),
                "stop": stop if stop else None,
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
            logger.debug(f"Sending request through Hugging Face InferenceClient to provider {self.provider} with model {self.model}")
            
            # Try Hugging Face's API first
            try:
                # Call the InferenceClient
                completion: ChatCompletionOutput = self.client.chat_completion(**params)
                
                # Verify we have choices before accessing
                if not completion.choices:
                    raise ValueError(f"No choices returned from {self.provider} API")
                    
                # Extract the response
                response_message = completion.choices[0].message.content
                finish_reason = getattr(completion.choices[0], "finish_reason", "unknown")
                
                # Log successful completion
                logger.debug(f"Received response from {self.provider} API: {finish_reason}")
                
            except Exception as hf_error:
                # If Hugging Face's API fails, try Together AI directly
                if self.direct_provider.lower() == "together":
                    logger.warning(f"Hugging Face API failed, falling back to Together AI direct API: {str(hf_error)}")
                    
                    # Set the API key for Together client
                    os.environ["TOGETHER_API_KEY"] = self.direct_api_key
                    
                    # Create Together client
                    together_client = Together()
                    
                    # Call Together AI's API
                    response = together_client.chat.completions.create(
                        model=self.direct_model,
                        messages=chat_messages,
                        max_tokens=params["max_tokens"],
                        temperature=params["temperature"],
                        top_p=params.get("top_p", 0.9),
                        stop=params.get("stop")
                    )
                    
                    # Extract the response
                    response_message = response.choices[0].message.content
                    finish_reason = getattr(response.choices[0], "finish_reason", "unknown")
                    
                    # Log successful completion
                    logger.debug(f"Received response from Together AI direct API: {finish_reason}")
                else:
                    # If not Together AI, re-raise the original error
                    raise hf_error
            
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
            if self.direct_provider.lower() == "together":
                logger.error(f"Error calling direct {self.direct_provider} API: {str(e)}")
            
            # Pass error to callback manager if available
            if run_manager:
                run_manager.on_llm_error(e, **kwargs)
                
            # Raise a more informative exception
            raise RuntimeError(f"Failed to generate response from {self.provider} API and direct {self.direct_provider} API: {str(e)}")
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return f"inference-client-{self.provider}-chat-model"


class InferenceClientEmbeddings:
    """Embeddings model that uses Hugging Face's InferenceClient with third-party providers."""
    
    client: InferenceClient
    model: str
    direct_model: str
    provider: str
    direct_provider: str
    direct_api_key: str
    
    def __init__(
        self,
        provider: str,
        direct_provider: str,
        api_key: str,
        direct_api_key: str,
        model: List[str],
        **kwargs: Any,
    ):
        """Initialize the InferenceClientEmbeddings.
        
        Args:
            provider: The provider to use (e.g., "together", "perplexity", "anyscale")
            api_key: The API key for the provider
            model: The model to use (should be a list of two models, the first is for the InferenceClient and the second is for the Together AI direct API)
            **kwargs: Additional keyword arguments
        """
        self.client = InferenceClient(provider=provider, api_key=api_key)
        self.model = model[0]
        self.direct_model = model[1]
        self.provider = provider
        self.direct_provider = direct_provider
        self.direct_api_key = direct_api_key
        logger.info(f"Initialized InferenceClientEmbeddings with provider: {provider}, model: {model[0]}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using the InferenceClient."""
        embeddings = []
        try:
            for text in texts:
                embedding = self.client.feature_extraction(text, model=self.model)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.warning(f"Hugging Face API failed, falling back to Together AI direct API: {str(e)}")
            
            # If Hugging Face's API fails, try Together AI directly
            if self.direct_provider.lower() == "together":
                try:
                    # Set the API key for Together client
                    os.environ["TOGETHER_API_KEY"] = self.direct_api_key
                    
                    # Create Together client
                    together_client = Together()
                    
                    # Get embeddings for each text
                    for text in texts:
                        response = together_client.embeddings.create(
                            model=self.direct_model,
                            input=text
                        )
                        embeddings.append(response.data[0].embedding)
                    return embeddings
                except Exception as together_error:
                    logger.error(f"Together AI API failed: {str(together_error)}")
                    raise RuntimeError(f"Both Hugging Face and Together AI APIs failed. HF error: {str(e)}, Together error: {str(together_error)}")
            else:
                # If not Together AI, re-raise the original error
                raise RuntimeError(f"Failed to embed documents with direct {self.direct_provider} API: {str(e)}")
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query using the InferenceClient."""
        try:
            return self.client.feature_extraction(text, model=self.model)
        except Exception as e:
            logger.warning(f"Hugging Face API failed, falling back to Together AI direct API: {str(e)}")
            
            # If Hugging Face's API fails, try Together AI directly
            if self.direct_provider.lower() == "together":
                try:
                    # Set the API key for Together client
                    os.environ["TOGETHER_API_KEY"] = self.direct_api_key
                    
                    # Create Together client
                    together_client = Together()
                    
                    # Get embedding
                    response = together_client.embeddings.create(
                        model=self.direct_model,
                        input=text
                    )
                    return response.data[0].embedding
                except Exception as together_error:
                    logger.error(f"Together AI API failed: {str(together_error)}")
                    raise RuntimeError(f"Both Hugging Face and Together AI APIs failed. HF error: {str(e)}, Together error: {str(together_error)}")
            else:
                # If not Together AI, re-raise the original error
                raise RuntimeError(f"Failed to embed query with direct {self.direct_provider} API: {str(e)}") 