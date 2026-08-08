"""Thin wrapper around the local `chub` CLI (from @nrl-ai/chub)."""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mirrors @nrl-ai/chub bin/chub.js platform → optionalDependency map.
_PLATFORM_PACKAGES = {
    "linux-x64": "@nrl-ai/chub-linux-x64",
    "linux-arm64": "@nrl-ai/chub-linux-arm64",
    "darwin-x64": "@nrl-ai/chub-darwin-x64",
    "darwin-arm64": "@nrl-ai/chub-darwin-arm64",
    "win32-x64": "@nrl-ai/chub-win32-x64",
}

_CHUB_BIN_CACHE: Optional[str] = None


class ChubError(RuntimeError):
    """Raised when a chub CLI invocation fails."""


def _clear_chub_binary_cache() -> None:
    """Reset cached binary path (tests / rare reconfigure)."""
    global _CHUB_BIN_CACHE
    _CHUB_BIN_CACHE = None


def _node_platform_key() -> Optional[str]:
    """Return Node-style platform-arch key (e.g. win32-x64, linux-x64)."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        return None

    if sys.platform.startswith("linux"):
        return f"linux-{arch}"
    if sys.platform == "darwin":
        return f"darwin-{arch}"
    if sys.platform == "win32":
        return f"win32-{arch}"
    return None


def _platform_native_binary(root: Path) -> Optional[Path]:
    """Path to the platform optionalDependency native binary, if present."""
    key = _node_platform_key()
    if not key:
        return None
    pkg = _PLATFORM_PACKAGES.get(key)
    if not pkg:
        return None
    name = "chub.exe" if key.startswith("win32") else "chub"
    path = root / "node_modules" / pkg / name
    return path if path.exists() else None


def _find_chub_binary() -> str:
    """Resolve the chub executable (env, platform package, shims, PATH).

    Result is cached after the first successful resolve.
    """
    global _CHUB_BIN_CACHE
    if _CHUB_BIN_CACHE:
        return _CHUB_BIN_CACHE

    env_path = os.getenv("CHUB_BIN")
    if env_path and Path(env_path).exists():
        _CHUB_BIN_CACHE = env_path
        return _CHUB_BIN_CACHE

    native = _platform_native_binary(PROJECT_ROOT)
    if native is not None:
        _CHUB_BIN_CACHE = str(native)
        return _CHUB_BIN_CACHE

    # npm shims (Windows .cmd first; Git Bash / Unix use `chub`)
    for path in (
        PROJECT_ROOT / "node_modules" / ".bin" / "chub.cmd",
        PROJECT_ROOT / "node_modules" / ".bin" / "chub",
    ):
        if path.exists():
            _CHUB_BIN_CACHE = str(path)
            return _CHUB_BIN_CACHE

    which = shutil.which("chub")
    if which:
        _CHUB_BIN_CACHE = which
        return _CHUB_BIN_CACHE

    raise ChubError(
        "chub binary not found. Install with `npm install` "
        "(dependency @nrl-ai/chub) or set CHUB_BIN."
    )


def run_chub(
    *args: str,
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run `chub <args>` and return the completed process."""
    binary = _find_chub_binary()
    cmd = [binary, *args]
    workdir = str(cwd or PROJECT_ROOT)
    logger.debug("Running: %s (cwd=%s)", " ".join(cmd), workdir)
    result = subprocess.run(
        cmd,
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise ChubError(
            f"chub {' '.join(args)} failed (exit {result.returncode}): "
            f"{stderr or stdout or 'no output'}"
        )
    return result


def run_chub_json(*args: str, cwd: Optional[Path] = None) -> Any:
    """Run chub with --json and parse stdout."""
    result = run_chub(*args, "--json", cwd=cwd, check=True)
    text = (result.stdout or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChubError(f"Failed to parse chub JSON output: {exc}\n{text[:500]}") from exc


def update(full: bool = False) -> Any:
    args = ["update"]
    if full:
        args.append("--full")
    return run_chub_json(*args)


def search(
    query: str = "",
    *,
    lang: Optional[str] = None,
    tags: Optional[str] = None,
    type_: Optional[str] = None,
    limit: int = 20,
) -> Any:
    args = ["search"]
    if query:
        args.append(query)
    if lang:
        args.extend(["--lang", lang])
    if tags:
        args.extend(["--tags", tags])
    if type_:
        args.extend(["--type", type_])
    args.extend(["--limit", str(limit)])
    return run_chub_json(*args)


def list_docs(
    *,
    lang: Optional[str] = None,
    type_: Optional[str] = None,
    limit: int = 100,
) -> Any:
    args = ["list"]
    if lang:
        args.extend(["--lang", lang])
    if type_:
        args.extend(["--type", type_])
    args.extend(["--limit", str(limit)])
    return run_chub_json(*args)


def get_doc(
    doc_id: str,
    *,
    lang: Optional[str] = None,
    version: Optional[str] = None,
    match_env: bool = False,
) -> str:
    """
    Fetch a single doc's markdown content.

    On --match-env failure, retries without match-env (latest/default variant).
    """
    args = ["get", doc_id]
    if lang:
        args.extend(["--lang", lang])
    if version:
        args.extend(["--version", version])

    if match_env:
        try:
            data = run_chub_json(*args, "--match-env")
            return _content_from_get(data)
        except ChubError as exc:
            logger.warning(
                "chub get %s --match-env failed (%s); retrying without --match-env",
                doc_id,
                exc,
            )

    data = run_chub_json(*args)
    return _content_from_get(data)


def get_pinned() -> list[dict[str, Any]]:
    """Return pinned docs as a list of {id, content, ...} entries when possible."""
    data = run_chub_json("get", "--pinned")
    if isinstance(data, dict) and "content" in data:
        # Single aggregate blob — fall back to pin list + individual get
        return [{"content": data["content"]}]
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return [data] if data else []


def list_pins() -> list[dict[str, Any]]:
    data = run_chub_json("pin", "list")
    if isinstance(data, dict):
        return data.get("pins", [])
    if isinstance(data, list):
        return data
    return []


def read_pins_yaml(path: Optional[Path] = None) -> list[dict[str, Any]]:
    pins_path = path or (PROJECT_ROOT / ".chub" / "pins.yaml")
    if not pins_path.exists():
        return []
    with pins_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("pins", []) or []


def parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from markdown body."""
    if not markdown.startswith("---"):
        return {}, markdown
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return {}, markdown
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = parts[2].lstrip("\n")
    return meta, body


def _content_from_get(data: Any) -> str:
    if isinstance(data, dict):
        if "content" in data and isinstance(data["content"], str):
            return data["content"]
        # Some versions may nest under results
        if "results" in data and data["results"]:
            first = data["results"][0]
            if isinstance(first, dict) and "content" in first:
                return first["content"]
    if isinstance(data, str):
        return data
    raise ChubError(f"Unexpected chub get payload type: {type(data)}")
