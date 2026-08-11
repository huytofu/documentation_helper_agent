# Ingestion Clear KB Design

**Date:** 2026-08-08  
**Status:** Approved  
**Approach:** CLI flag + small Pinecone helper (Approach 1)

## Problem

Changing the embedding model requires rebuilding the Pinecone knowledge base. The current ingestion CLI only **adds** documents via `vector_store.add_documents` and never deletes existing vectors. Re-running ingest after an embedding-model change therefore mixes old and new vectors (or fails on dimension mismatch) instead of replacing the KB.

## Goals

1. Support clearing Pinecone KBs from the ingestion CLI to prepare for reingestion.
2. `--clear` alone (with required `--framework`) clears without ingesting.
3. `--clear` combined with an explicit `--source` clears, then ingests.
4. Interactive confirmation unless `--yes` / `-y` is passed.
5. Fail closed on invalid framework specs, missing credentials, declined confirm, or clear failures (do not ingest after a failed clear).

## Non-Goals

- Recreating / resizing the Pinecone index when embedding dimensions change (operator still does that in Pinecone console or separately).
- Clearing Chroma or other non-Pinecone backends in this change.
- Soft-delete, per-document delete, or metadata-filtered delete.
- Changing Firecrawl/chub fetch behavior beyond framework filtering.

## CLI / UX

### New flags

| Flag | Meaning |
|------|---------|
| `--clear` | Wipe targeted KB(s) before optional ingest |
| `-y` / `--yes` | Skip interactive confirmation |

### `--framework` (single string)

Replaces the current repeatable `action="append"` form with one string:

| Value | Clear behavior | Ingest behavior |
|-------|----------------|-----------------|
| `all` | Delete **entire** index contents (every namespace on the index) | No framework filter (ingest all, same as omitting filter today) |
| `langgraph,llamaindex` (comma-separated) | Delete only those namespaces | Limit ingest to those namespaces |
| anything else | Error | Error |

Validation rules:

- Required when `--clear` is set.
- Accept `all`, or a comma-separated list where each token (after trim) is in `VALID_NAMESPACES` (`langgraph`, `llamaindex`, `smolagents`, `copilotkit`, `chub`).
- Reject unknown names, empty tokens, empty string, or mixed invalid forms.
- Do not accept spaces as separators (only commas); trimming around each token is allowed (`langgraph, llamaindex`).

### Invocation matrix

| Invocation | Behavior |
|------------|----------|
| `--clear --framework …` (no `--source` on argv) | Clear only |
| `--clear --source … --framework …` | Clear, then ingest that source |
| no `--clear` | Ingest as today; `--source` defaults to `all` |
| `--clear` without `--framework` | Error (non-zero exit) |

`--source` argparse default becomes `None` so “not passed” is distinguishable from `--source all`. When `--clear` is absent and `--source` is `None`, treat source as `all` for ingest.

### Confirmation

Unless `-y` / `--yes`:

1. Print Pinecone index name and delete target (`all namespaces` or the explicit list).
2. Prompt for typed `yes`.
3. Any other answer aborts with no deletes.

## Architecture

```
python -m ingestion [flags]
        │
        ▼
cli.py  — parse, validate framework, confirm if needed
        │
        ├─ if --clear → clear_namespaces(...)  (abort on failure)
        │
        └─ if ingest requested → pipeline.run_ingestion(...)
              (ingest-only, or after successful clear)
```

### Components

| Piece | Role |
|-------|------|
| `ingestion/cli.py` | Flags, validation orchestration, confirm prompt, exit codes |
| `ingestion/framework_arg.py` | Shared parser/validator for `--framework` string |
| `ingestion/clear.py` | Pinecone delete helper using `PINECONE_API_KEY` / `PINECONE_INDEX_NAME` |
| `ingestion/pipeline.py` | Unchanged ingest orchestration; no delete logic |
| `docs/ingestion.md` | Document clear / clear+reingest examples |

CLI owns sequencing: on `--clear`, call `clear_namespaces` first; only if that succeeds and `--source` was explicitly passed, call `run_ingestion`.

### Clear mechanics

Use the Pinecone client (same credentials as `agent.graph.vector_stores`):

- **Listed namespaces:** for each namespace, delete all vectors in that namespace (`index.delete(delete_all=True, namespace=ns)` or SDK-equivalent `delete_namespace`).
- **`all`:** list namespaces on the index, then delete each (entire KB for that index).
- Missing env vars → clear error before any delete.
- Partial failure mid-list → log which namespaces succeeded/failed; abort; do not proceed to ingest.

## Error handling

| Condition | Result |
|-----------|--------|
| `--clear` without `--framework` | Error, exit ≠ 0 |
| Invalid `--framework` string | Error, exit ≠ 0 |
| Missing Pinecone credentials on clear | Error, exit ≠ 0 |
| User declines confirm | Abort, no deletes, exit ≠ 0 |
| Pinecone delete failure | Log, abort before ingest, exit ≠ 0 |

## Testing

Unit tests with mocked Pinecone (no live network):

1. `framework_arg` accept/reject cases (`all`, valid list, unknowns, empties).
2. CLI wiring: clear-only vs clear+`--source`; missing `--framework`; decline confirm; `-y` skips prompt.
3. `clear.py`: per-namespace deletes vs `all` listing namespaces.

## Example commands

```bash
# Clear entire index (prompt)
python -m ingestion --clear --framework all

# Clear two namespaces without prompt
python -m ingestion --clear --framework langgraph,llamaindex -y

# Clear then reingest after embedding-model change
python -m ingestion --clear --framework all --source all -y
```

## Implementation notes

- Clear logic lives only in `clear.py`; CLI sequences clear then optional ingest.
- Never call `add_documents` if clear was requested and failed.
- Preserve existing ingest logging/summary output after a successful clear+ingest.
- Update `--framework` help text to describe `all` and comma-separated lists (breaking change vs repeatable `--framework`).
