"""Parse and validate the ingestion --framework CLI argument."""

from __future__ import annotations

from ingestion.namespace_map import VALID_NAMESPACES


def parse_framework_arg(value: str | None) -> tuple[bool, list[str]]:
    """
    Parse --framework.

    Returns:
        (True, []) for ``all``
        (False, [namespaces...]) for an explicit comma-separated list

    Raises:
        ValueError: if the value is missing or invalid
    """
    if value is None:
        raise ValueError("--framework is required")
    raw = value.strip()
    if not raw:
        raise ValueError(
            "--framework must be 'all' or a comma-separated list of known namespaces"
        )
    if raw == "all":
        return True, []

    parts = [p.strip() for p in raw.split(",")]
    if any(not p for p in parts):
        raise ValueError("Invalid --framework: empty token in comma-separated list")

    unknown = [p for p in parts if p not in VALID_NAMESPACES]
    if unknown:
        valid = ", ".join(sorted(VALID_NAMESPACES))
        raise ValueError(
            f"Unknown namespace(s): {', '.join(unknown)}. Valid: all, {valid}"
        )

    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            ordered.append(part)
    return False, ordered
