"""
Wrapper for Hugging Face InferenceClient to integrate with LangChain.

This module provides custom LangChain-compatible classes for using
Hugging Face's InferenceClient with third-party providers.

Tool-calling follows the OpenAI-compatible path used by LangChain's
ChatOpenAI (langchain_openai.chat_models.base.BaseChatOpenAI.bind_tools):
convert tools with convert_to_openai_tool, pass them on the request, and
normalize response tool_calls onto AIMessage.tool_calls via parse_tool_call.
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from huggingface_hub import InferenceClient
from huggingface_hub.inference._client import ChatCompletionOutput
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.output_parsers.openai_tools import (
    make_invalid_tool_call,
    parse_tool_call,
)
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from together import Together
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
        api_key: str,  # This is Hugging Face API key
        direct_api_key: str,  # This is direct API key for the provider like Together AI
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
            headers={"X-wait-for-model": "true"},
        )

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
            **kwargs,
        }

        # Initialize with all parameters
        super().__init__(**all_kwargs)
        logger.info(
            f"Initialized InferenceClientChatModel with provider: {provider}, "
            f"model: {model[0]} and {model[1]}"
        )

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        *,
        tool_choice: Optional[Union[dict, str, bool]] = None,
        **kwargs: Any,
    ) -> Runnable:
        """Bind tools using the OpenAI tools schema (same approach as ChatOpenAI).

        Reference: langchain_openai.chat_models.base.BaseChatOpenAI.bind_tools
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        if tool_choice:
            if isinstance(tool_choice, str):
                tool_names = [
                    t["function"]["name"]
                    for t in formatted_tools
                    if isinstance(t, dict) and "function" in t
                ]
                if tool_choice in tool_names:
                    tool_choice = {
                        "type": "function",
                        "function": {"name": tool_choice},
                    }
                elif tool_choice == "any":
                    tool_choice = "required"
            elif isinstance(tool_choice, bool):
                tool_choice = "required"
            kwargs["tool_choice"] = tool_choice
        return self.bind(tools=formatted_tools, **kwargs)

    @staticmethod
    def _tool_calls_to_openai_format(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        openai_tool_calls = []
        for tool_call in tool_calls:
            args = tool_call.get("args", {})
            if not isinstance(args, str):
                args = json.dumps(args)
            openai_tool_calls.append(
                {
                    "id": tool_call.get("id"),
                    "type": "function",
                    "function": {
                        "name": tool_call.get("name"),
                        "arguments": args,
                    },
                }
            )
        return openai_tool_calls

    def _convert_messages_to_chat_format(
        self, messages: List[BaseMessage]
    ) -> List[Dict[str, Any]]:
        """Convert LangChain messages to OpenAI-compatible chat dicts (incl. tools)."""
        chat_messages: List[Dict[str, Any]] = []
        for message in messages:
            if isinstance(message, HumanMessage):
                chat_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                entry: Dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content if message.content is not None else "",
                }
                tool_calls = message.tool_calls or []
                if not tool_calls and message.additional_kwargs.get("tool_calls"):
                    entry["tool_calls"] = message.additional_kwargs["tool_calls"]
                elif tool_calls:
                    entry["tool_calls"] = self._tool_calls_to_openai_format(tool_calls)
                    # Some providers reject empty string content with tool_calls.
                    if not entry["content"]:
                        entry["content"] = None
                chat_messages.append(entry)
            elif isinstance(message, SystemMessage):
                chat_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, ToolMessage):
                entry = {
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.tool_call_id,
                }
                if message.name:
                    entry["name"] = message.name
                chat_messages.append(entry)
            elif isinstance(message, ChatMessage):
                chat_messages.append({"role": message.role, "content": message.content})
            else:
                raise ValueError(f"Got unknown message type: {type(message)}")
        return chat_messages

    @staticmethod
    def _raw_tool_calls_from_message(message: Any) -> List[Dict[str, Any]]:
        """Normalize provider tool_calls (HF / Together / dict) to OpenAI-style dicts."""
        raw_tool_calls = getattr(message, "tool_calls", None)
        if raw_tool_calls is None and isinstance(message, dict):
            raw_tool_calls = message.get("tool_calls")
        if not raw_tool_calls:
            return []

        normalized: List[Dict[str, Any]] = []
        for raw in raw_tool_calls:
            if isinstance(raw, dict):
                normalized.append(raw)
                continue
            # Together / OpenAI SDK objects
            function = getattr(raw, "function", None)
            if function is not None:
                normalized.append(
                    {
                        "id": getattr(raw, "id", None),
                        "type": getattr(raw, "type", "function") or "function",
                        "function": {
                            "name": getattr(function, "name", None),
                            "arguments": getattr(function, "arguments", "{}") or "{}",
                        },
                    }
                )
            else:
                normalized.append(
                    {
                        "id": getattr(raw, "id", None),
                        "type": "function",
                        "function": {
                            "name": getattr(raw, "name", None),
                            "arguments": getattr(raw, "arguments", "{}") or "{}",
                        },
                    }
                )
        return normalized

    def _parse_ai_message(self, message: Any, finish_reason: str) -> AIMessage:
        """Build AIMessage with standardized tool_calls from a provider message."""
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        if content is None:
            content = ""

        raw_tool_calls = self._raw_tool_calls_from_message(message)
        tool_calls: List[Dict[str, Any]] = []
        invalid_tool_calls = []
        additional_kwargs: Dict[str, Any] = {}

        if raw_tool_calls:
            additional_kwargs["tool_calls"] = raw_tool_calls
            for raw_tool_call in raw_tool_calls:
                try:
                    tool_calls.append(parse_tool_call(raw_tool_call, return_id=True))
                except Exception as exc:  # noqa: BLE001 — mirror ChatOpenAI behavior
                    invalid_tool_calls.append(
                        make_invalid_tool_call(raw_tool_call, str(exc))
                    )

        return AIMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls,
            invalid_tool_calls=invalid_tool_calls,
            response_metadata={"finish_reason": finish_reason},
        )

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
            **kwargs: Additional parameters to pass to the API (incl. bound tools)

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

        # Bound tools / tool_choice from bind_tools(...)
        if "tools" in kwargs and kwargs["tools"] is not None:
            params["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs and kwargs["tool_choice"] is not None:
            params["tool_choice"] = kwargs["tool_choice"]

        # Add provider-specific parameters
        if self.provider.lower() == "together":
            # Together AI specific parameters
            params.update(
                {
                    "top_p": kwargs.get("top_p", 0.9),
                    "frequency_penalty": kwargs.get("frequency_penalty", 1.1),
                    "stop": stop if stop else None,
                }
            )
        else:
            # Generic parameters for other providers
            if stop:
                params["stop"] = stop

        # Add any additional parameters from kwargs (except ones we already handled)
        skip_keys = {
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "tools",
            "tool_choice",
        }
        for k, v in kwargs.items():
            if k not in params and k not in skip_keys:
                params[k] = v

        try:
            # Log request for debugging
            logger.debug(
                f"Sending request through Hugging Face InferenceClient to provider "
                f"{self.provider} with model {self.model}"
            )

            response_message_obj: Any = None
            finish_reason = "unknown"

            # Try Hugging Face's API first
            try:
                # Call the InferenceClient
                completion: ChatCompletionOutput = self.client.chat_completion(**params)

                # Verify we have choices before accessing
                if not completion.choices:
                    raise ValueError(f"No choices returned from {self.provider} API")

                response_message_obj = completion.choices[0].message
                finish_reason = getattr(completion.choices[0], "finish_reason", "unknown")

                # Log successful completion
                logger.debug(f"Received response from {self.provider} API: {finish_reason}")

            except Exception as hf_error:
                # If Hugging Face's API fails, try Together AI directly
                if self.direct_provider.lower() == "together":
                    logger.warning(
                        f"Hugging Face API failed, falling back to Together AI direct API: {str(hf_error)}"
                    )

                    # Set the API key for Together client
                    os.environ["TOGETHER_API_KEY"] = self.direct_api_key

                    # Create Together client
                    together_client = Together()

                    together_params = {
                        "model": self.direct_model,
                        "messages": chat_messages,
                        "max_tokens": params["max_tokens"],
                        "temperature": params["temperature"],
                        "top_p": params.get("top_p", 0.9),
                        "stop": params.get("stop"),
                    }
                    if params.get("tools") is not None:
                        together_params["tools"] = params["tools"]
                    if params.get("tool_choice") is not None:
                        together_params["tool_choice"] = params["tool_choice"]

                    # Call Together AI's API
                    response = together_client.chat.completions.create(**together_params)

                    response_message_obj = response.choices[0].message
                    finish_reason = getattr(
                        response.choices[0], "finish_reason", "unknown"
                    )

                    # Log successful completion
                    logger.debug(
                        f"Received response from Together AI direct API: {finish_reason}"
                    )
                else:
                    # If not Together AI, re-raise the original error
                    raise hf_error

            ai_message = self._parse_ai_message(response_message_obj, finish_reason)
            generation = ChatGeneration(
                message=ai_message,
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
            raise RuntimeError(
                f"Failed to generate response from {self.provider} API and direct "
                f"{self.direct_provider} API: {str(e)}"
            )

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
        logger.info(
            f"Initialized InferenceClientEmbeddings with provider: {provider}, model: {model[0]}"
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using the InferenceClient."""
        embeddings = []
        try:
            for text in texts:
                embedding = self.client.feature_extraction(text, model=self.model)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.warning(
                f"Hugging Face API failed, falling back to Together AI direct API: {str(e)}"
            )

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
                            model=self.direct_model, input=text
                        )
                        embeddings.append(response.data[0].embedding)
                    return embeddings
                except Exception as together_error:
                    logger.error(f"Together AI API failed: {str(together_error)}")
                    raise RuntimeError(
                        f"Both Hugging Face and Together AI APIs failed. HF error: {str(e)}, Together error: {str(together_error)}"
                    )
            else:
                # If not Together AI, re-raise the original error
                raise RuntimeError(
                    f"Failed to embed documents with direct {self.direct_provider} API: {str(e)}"
                )

    def embed_query(self, text: str) -> List[float]:
        """Embed a query using the InferenceClient."""
        try:
            return self.client.feature_extraction(text, model=self.model)
        except Exception as e:
            logger.warning(
                f"Hugging Face API failed, falling back to Together AI direct API: {str(e)}"
            )

            # If Hugging Face's API fails, try Together AI directly
            if self.direct_provider.lower() == "together":
                try:
                    # Set the API key for Together client
                    os.environ["TOGETHER_API_KEY"] = self.direct_api_key

                    # Create Together client
                    together_client = Together()

                    # Get embedding
                    response = together_client.embeddings.create(
                        model=self.direct_model, input=text
                    )
                    return response.data[0].embedding
                except Exception as together_error:
                    logger.error(f"Together AI API failed: {str(together_error)}")
                    raise RuntimeError(
                        f"Both Hugging Face and Together AI APIs failed. HF error: {str(e)}, Together error: {str(together_error)}"
                    )
            else:
                # If not Together AI, re-raise the original error
                raise RuntimeError(
                    f"Failed to embed query with direct {self.direct_provider} API: {str(e)}"
                )
