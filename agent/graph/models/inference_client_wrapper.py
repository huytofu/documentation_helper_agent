"""
Together-primary chat/embeddings wrappers with Hugging Face InferenceClient fallback.

Primary path: Together direct API (timeout-bounded).
Fallback path: Hugging Face InferenceClient with a non-Together provider.

Tool-calling follows the OpenAI-compatible path used by LangChain's
ChatOpenAI (langchain_openai.chat_models.base.BaseChatOpenAI.bind_tools):
convert tools with convert_to_openai_tool, pass them on the request, and
normalize response tool_calls onto AIMessage.tool_calls via parse_tool_call.
"""

import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Sequence, Union

from huggingface_hub import InferenceClient
from huggingface_hub.inference._client import ChatCompletionOutput
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.output_parsers.openai_tools import (
    make_invalid_tool_call,
    parse_tool_call,
)
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from together import Together

logger = logging.getLogger(__name__)

DEFAULT_TOGETHER_TIMEOUT_SECONDS = 15.0


class InferenceClientChatModel(BaseChatModel):
    """Chat model: Together direct primary, HF InferenceClient fallback."""

    client: InferenceClient
    model: str
    direct_model: str
    temperature: float = 0.0
    max_tokens: int = 1024
    provider: str = ""
    direct_provider: str = ""
    direct_api_key: str
    timeout: float = DEFAULT_TOGETHER_TIMEOUT_SECONDS

    def __init__(
        self,
        provider: str,
        direct_provider: str,
        api_key: str,  # Hugging Face API key (fallback path)
        direct_api_key: str,  # Together API key (primary path)
        model: List[str],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = DEFAULT_TOGETHER_TIMEOUT_SECONDS,
        **kwargs: Any,
    ):
        """Initialize the InferenceClientChatModel.

        Args:
            provider: HF InferenceClient fallback provider (must not be "together")
            direct_provider: Primary direct provider (expected: "together")
            api_key: Hugging Face API key for the fallback path
            direct_api_key: Together API key for the primary path
            model: [Together primary model ID, HF fallback model ID]
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            timeout: Together primary-path timeout in seconds
            **kwargs: Additional keyword arguments
        """
        if not provider or provider.lower() == "together":
            raise ValueError(
                "HF fallback provider must be set and must not be 'together' "
                f"(got {provider!r})"
            )
        if (direct_provider or "").lower() != "together":
            raise ValueError(
                f"Primary direct_provider must be 'together' (got {direct_provider!r})"
            )
        if not isinstance(model, list) or len(model) < 2:
            raise ValueError(
                "model must be a list of [Together primary, HF fallback] model IDs"
            )

        # HF fallback client (used only if Together fails / times out)
        client = InferenceClient(
            provider=provider,
            api_key=api_key,
            headers={"X-wait-for-model": "true"},
            timeout=timeout,
        )

        all_kwargs = {
            "client": client,
            "direct_model": model[0],  # Together primary
            "model": model[1],  # HF fallback
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": provider,
            "direct_provider": direct_provider,
            "direct_api_key": direct_api_key,
            "timeout": timeout,
            **kwargs,
        }

        super().__init__(**all_kwargs)
        logger.info(
            "Initialized InferenceClientChatModel: Together primary=%s, "
            "HF fallback provider=%s model=%s, timeout=%ss",
            model[0],
            provider,
            model[1],
            timeout,
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
        """Generate via Together primary, then HF InferenceClient on failure/timeout."""
        chat_messages = self._convert_messages_to_chat_format(messages)

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)
        top_p = kwargs.get("top_p", 0.9)
        tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")

        together_params: Dict[str, Any] = {
            "model": self.direct_model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop if stop else None,
        }
        if tools is not None:
            together_params["tools"] = tools
        if tool_choice is not None:
            together_params["tool_choice"] = tool_choice

        hf_params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools is not None:
            hf_params["tools"] = tools
        if tool_choice is not None:
            hf_params["tool_choice"] = tool_choice
        if stop:
            hf_params["stop"] = stop

        skip_keys = {
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "tools",
            "tool_choice",
        }
        for k, v in kwargs.items():
            if k not in hf_params and k not in skip_keys:
                hf_params[k] = v

        response_message_obj: Any = None
        finish_reason = "unknown"
        together_error: Optional[Exception] = None

        try:
            # 1) Together direct (primary)
            try:
                logger.debug(
                    "Sending request to Together direct API with model %s (timeout=%ss)",
                    self.direct_model,
                    self.timeout,
                )
                together_client = Together(
                    api_key=self.direct_api_key,
                    timeout=self.timeout,
                )
                response = together_client.chat.completions.create(**together_params)
                if not response.choices:
                    raise ValueError("No choices returned from Together API")
                response_message_obj = response.choices[0].message
                finish_reason = getattr(
                    response.choices[0], "finish_reason", "unknown"
                )
                logger.debug(
                    "Received response from Together AI direct API: %s", finish_reason
                )
            except Exception as err:  # noqa: BLE001 — any Together failure → HF fallback
                together_error = err
                logger.warning(
                    "Together AI primary path failed; falling back to HF provider %s "
                    "model %s: %s",
                    self.provider,
                    self.model,
                    err,
                )

                # 2) HF InferenceClient (fallback, non-Together provider)
                completion: ChatCompletionOutput = self.client.chat_completion(
                    **hf_params
                )
                if not completion.choices:
                    raise ValueError(
                        f"No choices returned from HF provider {self.provider} API"
                    )
                response_message_obj = completion.choices[0].message
                finish_reason = getattr(
                    completion.choices[0], "finish_reason", "unknown"
                )
                logger.debug(
                    "Received response from HF provider %s API: %s",
                    self.provider,
                    finish_reason,
                )

            ai_message = self._parse_ai_message(response_message_obj, finish_reason)
            generation = ChatGeneration(
                message=ai_message,
                generation_info={"finish_reason": finish_reason},
            )
            return ChatResult(generations=[generation])

        except Exception as e:
            logger.error(
                "Together primary and HF fallback both failed. Together error: %s; "
                "HF (%s) error: %s",
                together_error,
                self.provider,
                e,
            )
            if run_manager:
                run_manager.on_llm_error(e, **kwargs)
            raise RuntimeError(
                f"Failed to generate response from Together primary "
                f"({self.direct_model}) and HF fallback provider {self.provider} "
                f"({self.model}). Together error: {together_error}; HF error: {e}"
            ) from e

    def _build_request_params(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build Together and HF request param dicts from messages/kwargs."""
        chat_messages = self._convert_messages_to_chat_format(messages)

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)
        top_p = kwargs.get("top_p", 0.9)
        tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")

        together_params: Dict[str, Any] = {
            "model": self.direct_model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": stop if stop else None,
        }
        if tools is not None:
            together_params["tools"] = tools
        if tool_choice is not None:
            together_params["tool_choice"] = tool_choice

        hf_params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools is not None:
            hf_params["tools"] = tools
        if tool_choice is not None:
            hf_params["tool_choice"] = tool_choice
        if stop:
            hf_params["stop"] = stop

        skip_keys = {
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "tools",
            "tool_choice",
        }
        for k, v in kwargs.items():
            if k not in hf_params and k not in skip_keys:
                hf_params[k] = v

        return together_params, hf_params

    def _yield_text_chunk(
        self,
        text: str,
        *,
        finish_reason: Optional[str] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> ChatGenerationChunk:
        chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=text),
            generation_info={"finish_reason": finish_reason} if finish_reason else None,
        )
        if run_manager and text:
            run_manager.on_llm_new_token(text, chunk=chunk)
        return chunk

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream via Together primary; HF one-shot fallback on Together failure."""
        together_params, hf_params = self._build_request_params(
            messages, stop=stop, **kwargs
        )
        together_params = {**together_params, "stream": True}
        together_error: Optional[Exception] = None

        try:
            together_client = Together(
                api_key=self.direct_api_key,
                timeout=self.timeout,
            )
            stream = together_client.chat.completions.create(**together_params)
            yielded = False
            for raw_chunk in stream:
                choices = getattr(raw_chunk, "choices", None) or []
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                finish_reason = getattr(choice, "finish_reason", None)
                if content:
                    yielded = True
                    yield self._yield_text_chunk(
                        content, finish_reason=finish_reason, run_manager=run_manager
                    )
                elif finish_reason and not yielded:
                    # No content tokens; still surface finish for empty generations.
                    continue
            return
        except Exception as err:  # noqa: BLE001 — any Together failure → HF fallback
            together_error = err
            logger.warning(
                "Together AI stream primary path failed; falling back to HF provider %s "
                "model %s: %s",
                self.provider,
                self.model,
                err,
            )

        try:
            completion: ChatCompletionOutput = self.client.chat_completion(**hf_params)
            if not completion.choices:
                raise ValueError(
                    f"No choices returned from HF provider {self.provider} API"
                )
            response_message_obj = completion.choices[0].message
            finish_reason = getattr(completion.choices[0], "finish_reason", "unknown")
            ai_message = self._parse_ai_message(response_message_obj, finish_reason)
            text = ai_message.content if isinstance(ai_message.content, str) else str(
                ai_message.content or ""
            )
            yield self._yield_text_chunk(
                text, finish_reason=finish_reason, run_manager=run_manager
            )
        except Exception as e:
            logger.error(
                "Together stream and HF fallback both failed. Together error: %s; "
                "HF (%s) error: %s",
                together_error,
                self.provider,
                e,
            )
            if run_manager:
                run_manager.on_llm_error(e, **kwargs)
            raise RuntimeError(
                f"Failed to stream response from Together primary "
                f"({self.direct_model}) and HF fallback provider {self.provider} "
                f"({self.model}). Together error: {together_error}; HF error: {e}"
            ) from e

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Async wrapper around sync `_stream` for LangGraph / AG-UI astream paths."""
        sync_manager = run_manager.get_sync() if run_manager else None
        for chunk in self._stream(
            messages, stop=stop, run_manager=sync_manager, **kwargs
        ):
            yield chunk

    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return f"inference-client-{self.provider}-chat-model"


class InferenceClientEmbeddings:
    """Embeddings: Together direct primary, HF InferenceClient fallback."""

    client: InferenceClient
    model: str
    direct_model: str
    provider: str
    direct_provider: str
    direct_api_key: str
    timeout: float

    def __init__(
        self,
        provider: str,
        direct_provider: str,
        api_key: str,
        direct_api_key: str,
        model: List[str],
        timeout: float = DEFAULT_TOGETHER_TIMEOUT_SECONDS,
        **kwargs: Any,
    ):
        """Initialize the InferenceClientEmbeddings.

        Args:
            provider: HF InferenceClient fallback provider (must not be "together")
            direct_provider: Primary direct provider (expected: "together")
            api_key: Hugging Face API key for the fallback path
            direct_api_key: Together API key for the primary path
            model: [Together primary model ID, HF fallback model ID]
            timeout: Together primary-path timeout in seconds
            **kwargs: Additional keyword arguments (ignored extras like max_tokens)
        """
        if not provider or provider.lower() == "together":
            raise ValueError(
                "HF fallback provider must be set and must not be 'together' "
                f"(got {provider!r})"
            )
        if (direct_provider or "").lower() != "together":
            raise ValueError(
                f"Primary direct_provider must be 'together' (got {direct_provider!r})"
            )
        if not isinstance(model, list) or len(model) < 2:
            raise ValueError(
                "model must be a list of [Together primary, HF fallback] model IDs"
            )

        self.client = InferenceClient(
            provider=provider, api_key=api_key, timeout=timeout
        )
        self.direct_model = model[0]
        self.model = model[1]
        self.provider = provider
        self.direct_provider = direct_provider
        self.direct_api_key = direct_api_key
        self.timeout = timeout
        logger.info(
            "Initialized InferenceClientEmbeddings: Together primary=%s, "
            "HF fallback provider=%s model=%s, timeout=%ss",
            model[0],
            provider,
            model[1],
            timeout,
        )

    def _together_client(self) -> Together:
        return Together(api_key=self.direct_api_key, timeout=self.timeout)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents via Together primary, HF fallback on failure/timeout."""
        together_error: Optional[Exception] = None
        try:
            together_client = self._together_client()
            embeddings: List[List[float]] = []
            for text in texts:
                response = together_client.embeddings.create(
                    model=self.direct_model, input=text
                )
                embeddings.append(response.data[0].embedding)
            return embeddings
        except Exception as err:  # noqa: BLE001
            together_error = err
            logger.warning(
                "Together embeddings primary path failed; falling back to HF "
                "provider %s model %s: %s",
                self.provider,
                self.model,
                err,
            )

        try:
            return [
                self.client.feature_extraction(text, model=self.model) for text in texts
            ]
        except Exception as hf_error:
            logger.error(
                "Together and HF embeddings both failed. Together error: %s; HF error: %s",
                together_error,
                hf_error,
            )
            raise RuntimeError(
                f"Both Together and HF embeddings failed. Together error: {together_error}, "
                f"HF error: {hf_error}"
            ) from hf_error

    def embed_query(self, text: str) -> List[float]:
        """Embed a query via Together primary, HF fallback on failure/timeout."""
        together_error: Optional[Exception] = None
        try:
            response = self._together_client().embeddings.create(
                model=self.direct_model, input=text
            )
            return response.data[0].embedding
        except Exception as err:  # noqa: BLE001
            together_error = err
            logger.warning(
                "Together embeddings primary path failed; falling back to HF "
                "provider %s model %s: %s",
                self.provider,
                self.model,
                err,
            )

        try:
            return self.client.feature_extraction(text, model=self.model)
        except Exception as hf_error:
            logger.error(
                "Together and HF embeddings both failed. Together error: %s; HF error: %s",
                together_error,
                hf_error,
            )
            raise RuntimeError(
                f"Both Together and HF embeddings failed. Together error: {together_error}, "
                f"HF error: {hf_error}"
            ) from hf_error
