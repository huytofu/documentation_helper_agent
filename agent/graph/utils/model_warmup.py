"""Warm Together serverless models with a tiny Ping/Pong completion."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from together import Together

from agent.graph.utils.together_reasoning import together_reasoning_controls

logger = logging.getLogger(__name__)

WARMUP_MODELS: List[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "MiniMaxAI/MiniMax-M3",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
]

# Keep the prompt tiny; reasoning models still spend tokens before content.
WARMUP_PROMPT = "Reply with exactly one word: Pong"
DEFAULT_CACHE_TTL_SECONDS = float(os.environ.get("MODEL_WARMUP_CACHE_TTL_SECONDS", "300"))
DEFAULT_PER_MODEL_TIMEOUT_SECONDS = float(
    os.environ.get("MODEL_WARMUP_TIMEOUT_SECONDS", "55")
)
# gpt-oss / DeepSeek put early tokens in `reasoning`; 16 was finishing with
# finish_reason=length and empty content. Allow enough for reasoning + "Pong".
DEFAULT_MAX_TOKENS = int(os.environ.get("MODEL_WARMUP_MAX_TOKENS", "256"))

_service: Optional["ModelWarmupService"] = None


def _normalize_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
                continue
            text = getattr(block, "text", None) or getattr(block, "content", None)
            if text:
                parts.append(str(text))
        return "".join(parts)
    return str(content)


def _extract_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message is not None else None
    return _normalize_message_content(content)


def _extract_reasoning(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None:
        return ""
    for attr in ("reasoning", "reasoning_content"):
        value = getattr(message, attr, None)
        text = _normalize_message_content(value)
        if text:
            return text
    return ""


def _extract_warmup_text(response: Any) -> str:
    """Prefer assistant content; fall back to reasoning for OSS/DeepSeek models."""
    content = _extract_content(response)
    if content.strip():
        return content
    return _extract_reasoning(response)


def _message_debug_snapshot(response: Any) -> Dict[str, Any]:
    """Compact, log-safe view of the Together response for warm-up debugging."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        return {"choices": 0, "raw_type": type(response).__name__}
    choice = choices[0]
    message = getattr(choice, "message", None)
    content = getattr(message, "content", None) if message is not None else None
    snapshot: Dict[str, Any] = {
        "choices": len(choices),
        "finish_reason": repr(getattr(choice, "finish_reason", None)),
        "message_type": type(message).__name__ if message is not None else None,
        "content_type": type(content).__name__,
        "content_repr": repr(content)[:1000],
    }
    # Reasoning / alternate fields some OSS models populate instead of content.
    if message is not None:
        for attr in ("reasoning", "reasoning_content", "refusal"):
            if hasattr(message, attr):
                snapshot[attr] = repr(getattr(message, attr))[:500]
        try:
            dump = (
                message.model_dump()
                if hasattr(message, "model_dump")
                else getattr(message, "__dict__", None)
            )
            if isinstance(dump, dict):
                snapshot["message_keys"] = list(dump.keys())
        except Exception:  # noqa: BLE001 — debug-only
            pass
    return snapshot


def _contains_pong(text: str) -> bool:
    return "pong" in (text or "").lower()


class ModelWarmupService:
    """Ping configured Together models in parallel; cache successful warm-ups."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        models: Optional[List[str]] = None,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        per_model_timeout_seconds: float = DEFAULT_PER_MODEL_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFERENCE_DIRECT_API_KEY", "")
        self.models = list(models or WARMUP_MODELS)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.per_model_timeout_seconds = per_model_timeout_seconds
        self._last_success_at: Optional[float] = None
        self._lock = asyncio.Lock()

    def _is_cache_valid(self) -> bool:
        if self._last_success_at is None:
            return False
        return (time.time() - self._last_success_at) < self.cache_ttl_seconds

    def _ping_model_sync(self, model: str) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "ok": False,
                "model": model,
                "error": "INFERENCE_DIRECT_API_KEY not configured",
                "reply": "",
            }
        try:
            client = Together(
                api_key=self.api_key,
                timeout=self.per_model_timeout_seconds,
            )
            base_params: Dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": WARMUP_PROMPT}],
                "max_tokens": DEFAULT_MAX_TOKENS,
                "temperature": 0,
            }
            reasoning_controls = together_reasoning_controls(model)
            try:
                response = client.chat.completions.create(
                    **base_params,
                    **reasoning_controls,
                )
            except Exception as ctrl_exc:  # noqa: BLE001 — unsupported control → retry
                if not reasoning_controls:
                    raise
                logger.warning(
                    "Warm-up reasoning controls rejected for %s (%s); retrying without them",
                    model,
                    ctrl_exc,
                )
                response = client.chat.completions.create(**base_params)
            content = _extract_content(response)
            reasoning = _extract_reasoning(response)
            reply = _extract_warmup_text(response)
            ok = _contains_pong(reply)
            # Model answered at all ⇒ cold start finished (even if text is odd).
            # Prefer Pong when present; otherwise accept non-empty content/reasoning
            # with a completed choice so warm-up is not blocked by terse refusals.
            choices = getattr(response, "choices", None) or []
            if not ok and choices and (content.strip() or reasoning.strip()):
                ok = True
            snapshot = _message_debug_snapshot(response)
            logger.info(
                "Warm-up response model=%s ok=%s content=%r reasoning=%r "
                "extracted_reply=%r snapshot=%s",
                model,
                ok,
                content[:500],
                reasoning[:500],
                reply[:500],
                snapshot,
            )
            result: Dict[str, Any] = {
                "ok": ok,
                "model": model,
                "reply": (content or reply)[:500],
                "reasoning": reasoning[:500],
            }
            if not ok:
                result["error"] = "Empty warm-up response (no content/reasoning)"
                result["debug"] = snapshot
            return result
        except Exception as exc:  # noqa: BLE001 — surface per-model failures
            logger.warning(
                "Warm-up exception for model %s: %s",
                model,
                exc,
                exc_info=True,
            )
            return {
                "ok": False,
                "model": model,
                "error": str(exc),
                "reply": "",
            }

    async def _ping_model(self, model: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._ping_model_sync, model)

    async def warmup(self) -> Dict[str, Any]:
        async with self._lock:
            if self._is_cache_valid():
                return {
                    "ok": True,
                    "status": "already_warm",
                    "models": {
                        m: {"ok": True, "model": m, "cached": True} for m in self.models
                    },
                    "last_success_at": self._last_success_at,
                }

            results = await asyncio.gather(
                *[self._ping_model(model) for model in self.models]
            )
            models_map = {r["model"]: r for r in results}
            ok = all(r.get("ok") for r in results)
            if ok:
                self._last_success_at = time.time()
                status = "warmed_up"
            else:
                status = "failed"
            logger.info(
                "Warm-up finished status=%s ok=%s replies=%s",
                status,
                ok,
                {m: models_map[m].get("reply") for m in models_map},
            )
            return {
                "ok": ok,
                "status": status,
                "models": models_map,
                "last_success_at": self._last_success_at,
            }


def get_warmup_service() -> ModelWarmupService:
    global _service
    if _service is None:
        _service = ModelWarmupService()
    return _service


def reset_warmup_service_for_tests() -> None:
    """Reset singleton between unit tests."""
    global _service
    _service = None
