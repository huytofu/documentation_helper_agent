# Design: Firecrawl crawl cache (skip re-scrape)

**Date:** 2026-08-11  
**Status:** Approved for planning  
**Scope:** Persist Firecrawl scrape results to local disk so re-ingest can skip crawling when the URL list is unchanged. CLI `--refresh`, docs, gitignore, unit tests.

## Problem

Firecrawl ingest is scrape → chunk → embed → Pinecone with **no on-disk crawl cache**.  
If embedding fails after a long crawl (e.g. e5 512-token limit), the scraped documents exist only in memory and are lost. Re-running the CLI always re-crawls.

## Goals

- After a successful Firecrawl scrape, save documents under `.cache/firecrawl/` so a later ingest can reuse them.
- **Auto-use** cache when present and valid for that framework.
- Invalidate cache when the framework’s URL list changes (hash mismatch → crawl again).
- Force a fresh crawl with `--refresh`.
- Write cache after scrape succeeds, **before** chunk/embed, so embed failures still leave a reusable crawl.

## Non-goals

- Caching chub fetches.
- TTL / age-based expiry (only URL-list hash + `--refresh`).
- Committing or sharing cache across machines.
- Incremental per-URL cache files or SQLite.

## Decision

**Per-framework JSON on disk** at `.cache/firecrawl/{framework}.json`.

Rejected alternatives:

1. **Per-URL files + manifest** — more I/O and code; not needed for hundreds of pages.
2. **SQLite** — heavier than this CLI needs.
3. **Explicit `--from-cache` only** — user chose auto-use instead.

## Cache file format

```json
{
  "framework": "langgraph",
  "url_hash": "<sha256 hex>",
  "scraped_at": "<ISO-8601>",
  "documents": [
    {
      "content": "<markdown>",
      "url": "https://...",
      "framework": "langgraph"
    }
  ]
}
```

**`url_hash`:** SHA-256 of the framework’s URL list joined with newlines, in list order (same order as `FRAMEWORK_URLS[framework]`).

## Data flow

For each framework in Firecrawl ingest:

1. Compute `url_hash` from the current URL list.
2. Unless `refresh=True`: if cache file exists and `url_hash` matches → load Documents → skip Firecrawl.
3. Otherwise: scrape with Firecrawl.
4. If scrape produced a non-empty document list → write/overwrite cache.
5. Chunk + embed + Pinecone (unchanged).

## Components

| Piece | Change |
|--------|--------|
| `ingestion/firecrawl_cache.py` (new) | `url_hash(urls)`, `cache_path(framework)`, `load_cache`, `save_cache` |
| `ingestion/pipeline.py` | Try cache unless refresh; save after successful scrape; pass `refresh` through |
| `ingestion/cli.py` | Add `--refresh` (applies to Firecrawl path; no-op for chub-only runs) |
| `.gitignore` | Add `.cache/` |
| `docs/ingestion.md` | Document auto-cache + `--refresh` |

## Error / edge cases

| Case | Behavior |
|------|----------|
| Corrupt / unreadable cache | Log warning; crawl; overwrite |
| Hash mismatch | Log warning; crawl; overwrite |
| Empty scrape result | Do **not** write cache |
| Partial scrape (some URLs fail) | Save whatever documents succeeded; hash is based on **requested** URL list |
| Missing `.cache/firecrawl/` | Create on save |
| `--refresh` without API key | Same as today (fail clearly) |

## CLI

```bash
# Auto: use cache if valid; else crawl and save
python -m ingestion --source firecrawl --framework langgraph

# Force re-crawl and overwrite cache
python -m ingestion --source firecrawl --framework langgraph --refresh
```

## Testing

Unit tests with tempdir / mocks:

- `url_hash` stable for same ordered list; changes when list or order changes
- load hit / miss / hash mismatch / corrupt file
- pipeline loads cache when valid; crawls and saves when missing, stale, or `refresh=True` (mock `scrape_urls`)

## Out of scope for this change

- Fixing embedding chunk size (separate; already being adjusted by the user).
- Clearing Pinecone before re-ingest (existing `--clear` remains the tool for that).
