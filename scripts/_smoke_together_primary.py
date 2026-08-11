"""Smoke-check Together-primary config + fallback wiring (no live API calls)."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Ensure inference_client path is selected before importing config-backed modules.
os.environ["USE_INFERENCE_CLIENT"] = "true"
os.environ["USE_OLLAMA"] = "false"
os.environ.setdefault("INFERENCE_API_KEY", "hf-test-key")
os.environ.setdefault("INFERENCE_DIRECT_API_KEY", "together-test-key")

from agent.graph.models.config import (  # noqa: E402
    MODEL_IDS,
    PROVIDER_IDS,
    TOGETHER_TIMEOUT_SECONDS,
    get_model_config_for_component,
)
from agent.graph.models.inference_client_wrapper import (  # noqa: E402
    InferenceClientChatModel,
)


def check_config() -> None:
    assert TOGETHER_TIMEOUT_SECONDS == 15.0
    assert MODEL_IDS["generator"][0] == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert MODEL_IDS["generator"][1] == "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    assert PROVIDER_IDS["generator"] == "nebius"
    assert all(p.lower() != "together" for p in PROVIDER_IDS.values())

    cfg = get_model_config_for_component("generator")
    assert cfg["direct_provider_org"] == "together"
    assert cfg["provider_org"] == "nebius"
    assert cfg["together_timeout"] == 15.0
    assert cfg["model"][0].startswith("deepseek")
    print("config OK")


def check_fallback_order() -> None:
    llm = InferenceClientChatModel(
        provider="nebius",
        direct_provider="together",
        api_key="hf",
        direct_api_key="tg",
        model=[
            "deepseek-ai/DeepSeek-V4-Flash-0731",
            "Qwen/Qwen3-Coder-480B-A35B-Instruct",
        ],
        timeout=15,
    )
    assert llm.direct_model == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert llm.model == "Qwen/Qwen3-Coder-480B-A35B-Instruct"

    together_client = MagicMock()
    together_client.chat.completions.create.side_effect = TimeoutError("boom")

    hf_msg = SimpleNamespace(content="fallback-ok", tool_calls=None)
    hf_choice = SimpleNamespace(message=hf_msg, finish_reason="stop")
    hf_completion = SimpleNamespace(choices=[hf_choice])

    with patch(
        "agent.graph.models.inference_client_wrapper.Together",
        return_value=together_client,
    ), patch.object(
        llm.client, "chat_completion", return_value=hf_completion
    ) as hf_chat:
        from langchain_core.messages import HumanMessage

        result = llm._generate([HumanMessage(content="hi")])
        assert result.generations[0].message.content == "fallback-ok"
        together_client.chat.completions.create.assert_called_once()
        hf_chat.assert_called_once()
        assert hf_chat.call_args.kwargs["model"] == "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    print("fallback order OK")


def main() -> int:
    check_config()
    check_fallback_order()
    print("all smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
