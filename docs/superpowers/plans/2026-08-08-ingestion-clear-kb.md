# Ingestion Clear KB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--clear` / `--yes` to the ingestion CLI so operators can wipe Pinecone namespaces (or the whole index) before optional reingestion when changing embedding models.

**Architecture:** Shared `--framework` parser (`all` or comma-separated known namespaces). New `ingestion/clear.py` deletes via the Pinecone client. CLI confirms (unless `-y`), clears, then optionally calls existing `run_ingestion`. Pipeline stays ingest-only aside from multi-namespace chub filter.

**Tech Stack:** Python 3, argparse, Pinecone SDK, pytest (mocked; no live Pinecone)

## Global Constraints

- `--clear` requires `--framework`
- `--framework` is a single string: `all` OR comma-separated ⊆ `VALID_NAMESPACES`
- `--clear` without `--source` on argv → clear only
- `--clear` + explicit `--source` → clear then ingest
- Interactive confirm unless `-y` / `--yes`; typed `yes` required
- Fail closed: no ingest after failed/declined clear
- Use `deployment_env/Scripts/python.exe` for tests (not `.venv`)
- Run shell via Git Bash (`"C:\Program Files\Git\bin\bash.exe"`)

## File structure

| File | Responsibility |
|------|----------------|
| `ingestion/framework_arg.py` | Parse/validate `--framework` string |
| `ingestion/clear.py` | Pinecone namespace / full-index delete |
| `ingestion/cli.py` | Flags, confirm, sequence clear → optional ingest |
| `ingestion/pipeline.py` | Allow chub filter for multiple namespaces |
| `docs/ingestion.md` | Document clear / clear+reingest |
| `tests/test_ingestion_framework_arg.py` | Parser unit tests |
| `tests/test_ingestion_clear.py` | Clear helper unit tests (mocked) |
| `tests/test_ingestion_cli_clear.py` | CLI wiring unit tests (mocked) |

Note: do **not** put tests under `tests/ingestion/` — that package name shadows the real `ingestion` package on pytest's path.

---

### Task 1: Framework arg parser

**Files:**
- Create: `ingestion/framework_arg.py`
- Create: `tests/ingestion/test_framework_arg.py`
- Create: `tests/ingestion/__init__.py` (empty)

**Interfaces:**
- Produces: `parse_framework_arg(value: str) -> tuple[bool, list[str]]`  
  - `(True, [])` means `all`  
  - `(False, ["langgraph", ...])` means explicit namespaces  
  - Raises `ValueError` with a clear message on invalid input

- [ ] **Step 1: Write failing tests**

```python
# tests/ingestion/test_framework_arg.py
import pytest
from ingestion.framework_arg import parse_framework_arg


def test_all():
    assert parse_framework_arg("all") == (True, [])


def test_comma_list_trims():
    assert parse_framework_arg("langgraph, llamaindex") == (
        False,
        ["langgraph", "llamaindex"],
    )


def test_single_namespace():
    assert parse_framework_arg("chub") == (False, ["chub"])


@pytest.mark.parametrize(
    "bad",
    ["", "  ", "foo", "langgraph,foo", "langgraph,", ",langgraph", "all,langgraph"],
)
def test_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_framework_arg(bad)
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/test_framework_arg.py -v
```

Expected: import/collection error or `parse_framework_arg` missing

- [ ] **Step 3: Implement parser**

```python
# ingestion/framework_arg.py
from __future__ import annotations
from ingestion.namespace_map import VALID_NAMESPACES


def parse_framework_arg(value: str) -> tuple[bool, list[str]]:
    if value is None:
        raise ValueError("--framework is required")
    raw = value.strip()
    if not raw:
        raise ValueError("--framework must be 'all' or a comma-separated list of known namespaces")
    if raw == "all":
        return True, []
    parts = [p.strip() for p in raw.split(",")]
    if any(not p for p in parts):
        raise ValueError("Invalid --framework: empty token in comma-separated list")
    unknown = [p for p in parts if p not in VALID_NAMESPACES]
    if unknown:
        raise ValueError(
            f"Unknown namespace(s): {', '.join(unknown)}. "
            f"Valid: all, {', '.join(sorted(VALID_NAMESPACES))}"
        )
    # preserve order, dedupe
    seen: set[str] = set()
    ordered: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return False, ordered
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/test_framework_arg.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ingestion/framework_arg.py tests/ingestion/__init__.py tests/ingestion/test_framework_arg.py
git commit -m "Add --framework parser for all and comma-separated namespaces."
```

---

### Task 2: Pinecone clear helper

**Files:**
- Create: `ingestion/clear.py`
- Create: `tests/ingestion/test_clear.py`

**Interfaces:**
- Consumes: `parse_framework_arg` result shape `(is_all, namespaces)`
- Produces: `clear_namespaces(*, is_all: bool, namespaces: list[str]) -> list[str]`  
  Returns list of namespaces actually cleared. Raises `RuntimeError` / `ValueError` on missing creds or delete failure.

- [ ] **Step 1: Write failing tests**

```python
# tests/ingestion/test_clear.py
from unittest.mock import MagicMock, patch
import pytest
from ingestion.clear import clear_namespaces


@patch("ingestion.clear._get_index")
def test_clear_listed_namespaces(mock_get_index):
    index = MagicMock()
    mock_get_index.return_value = index
    cleared = clear_namespaces(is_all=False, namespaces=["langgraph", "chub"])
    assert cleared == ["langgraph", "chub"]
    assert index.delete.call_count == 2
    index.delete.assert_any_call(delete_all=True, namespace="langgraph")
    index.delete.assert_any_call(delete_all=True, namespace="chub")


@patch("ingestion.clear._get_index")
def test_clear_all_lists_namespaces(mock_get_index):
    index = MagicMock()
    index.describe_index_stats.return_value = {
        "namespaces": {"langgraph": {"vector_count": 1}, "chub": {"vector_count": 2}}
    }
    mock_get_index.return_value = index
    cleared = clear_namespaces(is_all=True, namespaces=[])
    assert set(cleared) == {"langgraph", "chub"}
    assert index.delete.call_count == 2


@patch.dict("os.environ", {}, clear=True)
def test_missing_creds():
    with pytest.raises(ValueError, match="PINECONE"):
        clear_namespaces(is_all=False, namespaces=["langgraph"])
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/test_clear.py -v
```

- [ ] **Step 3: Implement clear helper**

```python
# ingestion/clear.py
from __future__ import annotations
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_index() -> Any:
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not api_key or not index_name:
        raise ValueError(
            "Pinecone credentials are required. "
            "Set PINECONE_API_KEY and PINECONE_INDEX_NAME."
        )
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name), index_name


def clear_namespaces(*, is_all: bool, namespaces: list[str]) -> list[str]:
    index, index_name = _get_index()
    if is_all:
        stats = index.describe_index_stats()
        ns_map = getattr(stats, "namespaces", None) or stats.get("namespaces") or {}
        targets = sorted(ns_map.keys())
        logger.info("Clearing ALL namespaces on index %s: %s", index_name, targets or "(none)")
    else:
        targets = list(namespaces)
        logger.info("Clearing namespaces on index %s: %s", index_name, targets)

    cleared: list[str] = []
    for ns in targets:
        try:
            index.delete(delete_all=True, namespace=ns)
            cleared.append(ns)
            logger.info("Cleared namespace %s", ns)
        except Exception as exc:
            logger.error("Failed clearing namespace %s after %s: %s", ns, cleared, exc)
            raise RuntimeError(
                f"Failed clearing namespace {ns!r} on index {index_name!r}: {exc}"
            ) from exc
    return cleared
```

Note: if `_get_index` returns a tuple, adjust tests to patch `_get_index` returning `(index, "documentation-helper-agent")`. Keep that contract in the implementation.

- [ ] **Step 4: Run tests — expect PASS**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/test_clear.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ingestion/clear.py tests/ingestion/test_clear.py
git commit -m "Add Pinecone namespace clear helper for ingestion rebuilds."
```

---

### Task 3: CLI clear + confirm + sequencing

**Files:**
- Modify: `ingestion/cli.py`
- Modify: `ingestion/pipeline.py` (chub multi-namespace filter only)
- Create: `tests/ingestion/test_cli_clear.py`

**Interfaces:**
- Consumes: `parse_framework_arg`, `clear_namespaces`, `run_ingestion`
- CLI: `--source` default `None`; `--clear`; `-y/--yes`; `--framework` single string → `dest="framework"`

Pipeline tweak for chub when multiple frameworks:

```python
# in run_ingestion chub branch — filter with membership
ns_filter = None
if frameworks:
    ns_filter = frameworks  # list; load_chub_documents accepts collection
```

```python
# load_chub_documents / run_chub_ingestion
namespace_filter: Optional[str] | Optional[Collection[str]]
# skip when: namespace_filter and ns not in set(namespace_filter) if collection,
# or ns != namespace_filter if str (keep str for back-compat)
```

Prefer updating signature to `namespace_filter: Optional[Collection[str]] = None` and treat a single string as one-element by normalizing at call site to a list/set.

- [ ] **Step 1: Write failing CLI tests**

```python
# tests/ingestion/test_cli_clear.py
from unittest.mock import patch
import pytest
from ingestion.cli import main


def test_clear_requires_framework():
    assert main(["--clear"]) != 0


def test_clear_only_no_source(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    with patch("ingestion.clear.clear_namespaces", return_value=["langgraph"]) as clear, \
         patch("ingestion.pipeline.run_ingestion") as ingest:
        code = main(["--clear", "--framework", "langgraph"])
        assert code == 0
        clear.assert_called_once()
        ingest.assert_not_called()


def test_clear_then_ingest_when_source_passed(monkeypatch):
    with patch("ingestion.clear.clear_namespaces", return_value=["langgraph"]) as clear, \
         patch("ingestion.pipeline.run_ingestion", return_value={"firecrawl": {}}) as ingest:
        code = main(["--clear", "--framework", "langgraph", "--source", "firecrawl", "-y"])
        assert code == 0
        clear.assert_called_once()
        ingest.assert_called_once()


def test_decline_confirm_aborts(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with patch("ingestion.clear.clear_namespaces") as clear, \
         patch("ingestion.pipeline.run_ingestion") as ingest:
        code = main(["--clear", "--framework", "all"])
        assert code != 0
        clear.assert_not_called()
        ingest.assert_not_called()


def test_ingest_default_source_without_clear():
    with patch("ingestion.pipeline.run_ingestion", return_value={"firecrawl": {}, "chub": {}}) as ingest:
        code = main([])
        assert code == 0
        assert ingest.call_args.kwargs["source"] == "all"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/test_cli_clear.py -v
```

- [ ] **Step 3: Implement CLI + chub filter**

Update `build_parser`:
- `--source` default `None`
- `--framework` single string (no append)
- `--clear`, `-y/--yes`

Update `main`:
1. If `--clear` and not `--framework` → error
2. If `--framework` set → `parse_framework_arg`
3. If `--clear`: confirm unless `--yes`; then `clear_namespaces`
4. Ingest if: not `--clear`, OR `--source` was explicitly provided  
   - source = `args.source or "all"` when ingesting without clear; when clear-only, skip ingest
5. Map `is_all` → `frameworks=None` for ingest; else pass namespace list
6. On clear failure / decline → return non-zero, never ingest

- [ ] **Step 4: Run all ingestion tests — expect PASS**

```bash
deployment_env/Scripts/python.exe -m pytest tests/ingestion/ -v
```

- [ ] **Step 5: Commit**

```bash
git add ingestion/cli.py ingestion/pipeline.py ingestion/chub_source.py tests/ingestion/test_cli_clear.py
git commit -m "Wire --clear/--yes into ingestion CLI with confirm and sequencing."
```

---

### Task 4: Docs

**Files:**
- Modify: `docs/ingestion.md`

- [ ] **Step 1: Add Clear / rebuild section** with examples from the spec:

```bash
python -m ingestion --clear --framework all
python -m ingestion --clear --framework langgraph,llamaindex -y
python -m ingestion --clear --framework all --source all -y
```

Note: `--framework` is now `all` or comma-separated (not repeatable flags). Mention confirm / `-y`.

- [ ] **Step 2: Commit**

```bash
git add docs/ingestion.md
git commit -m "Document ingestion --clear for embedding-model rebuilds."
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `--clear` + required `--framework` | 3 |
| `all` vs comma list validation | 1 |
| Clear-only vs clear+source | 3 |
| Confirm / `-y` | 3 |
| Pinecone delete listed / all | 2 |
| No ingest after failed clear | 3 |
| Unit tests mocked | 1–3 |
| `docs/ingestion.md` | 4 |
