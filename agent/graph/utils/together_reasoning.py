"""Together reasoning controls shared by graph chat models and warm-up."""

from __future__ import annotations

from typing import Any, Dict


def together_reasoning_controls(model_id: str) -> Dict[str, Any]:
    """Return Together kwargs that minimize reasoning latency for ``model_id``.

    - gpt-oss: always-on reasoning → ``reasoning_effort="low"``
    - DeepSeek V4 family: hybrid → ``reasoning={"enabled": False}``
    - Other models: no extra kwargs
    """
    model_l = (model_id or "").lower()
    if "gpt-oss" in model_l:
        return {"reasoning_effort": "low"}
    if "deepseek" in model_l:
        return {"reasoning": {"enabled": False}}
    return {}
