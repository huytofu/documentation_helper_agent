# Documentation ingestion

This project indexes framework and library docs into **Pinecone** so the agent can answer user questions about packages — especially **agentic development** (LangGraph, LlamaIndex, OpenAI, Pinecone, CopilotKit, …).

## Sources

| Source | What it is | Namespaces |
|--------|------------|------------|
| **Firecrawl** | Scrapes hard-coded doc site URLs ([`ingestion/urls.py`](../ingestion/urls.py)) | `langgraph`, `copilotkit` (and empty lists for `llamaindex` / `smolagents`) |
| **chub pins** | Curated baseline corpus from [`.chub/pins.yaml`](../.chub/pins.yaml) via [`@nrl-ai/chub`](https://www.npmjs.com/package/@nrl-ai/chub) | Mapped from doc id → namespace (see below) |

Pins are the **maintainer-curated expert starter set**. They are not derived from this repo’s own `requirements.txt` / `package.json`.

When a **user** asks about a package that is missing or weak in Pinecone, use chub **search/get** (MCP tools or future graph node) — not dependency detection of this agent.

### Namespace map (chub)

| Doc id pattern | Pinecone namespace |
|----------------|---------------------|
| `langgraph/*` | `langgraph` |
| `llama-index/*` | `llamaindex` |
| `copilotkit/*` | `copilotkit` |
| everything else (OpenAI, Pinecone, …) | `chub` |

## Prerequisites

1. Python deps: `pip install -r requirements.txt` (activate `.venv` first when present).
2. Node deps (for the chub CLI): `npm install` — installs `@nrl-ai/chub` and the platform native binary under `node_modules/@nrl-ai/chub-<platform>/`.
3. Env vars (see [`.env.example`](../.env.example)):
   - `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
   - `FIRECRAWL_API_KEY` (only for Firecrawl source)
   - Embedding provider settings already used by the agent
4. Project pins: [`.chub/pins.yaml`](../.chub/pins.yaml) (created via `chub init` / `chub pin add`).

Optional: set `CHUB_BIN` to the native binary path. Auto-detect order: `CHUB_BIN` → platform package → `node_modules/.bin` shims → `PATH`. Docker sets `CHUB_BIN=/app/node_modules/@nrl-ai/chub-linux-x64/chub`.

## Commands

```bash
# Refresh baseline corpus from pins → Pinecone
python -m ingestion --source chub

# Same launcher
python ingest.py --source chub --verbose

# Firecrawl URL lists (slow; rate-limits between batches)
python -m ingestion --source firecrawl --framework langgraph

# Force a fresh Firecrawl crawl (ignore on-disk cache)
python -m ingestion --source firecrawl --framework langgraph --refresh

# Both sources
python -m ingestion --source all
```

`--framework` accepts `all` or a comma-separated list of known namespaces
(`langgraph`, `llamaindex`, `smolagents`, `copilotkit`, `chub`). Example:
`--framework langgraph,llamaindex`.

### Firecrawl crawl cache

Successful Firecrawl scrapes are saved under `.cache/firecrawl/{framework}.json`
(gitignored). On the next run, ingest **auto-uses** that cache when the URL list
for the framework is unchanged (SHA-256 of the ordered list). Use `--refresh` to
force a re-crawl and overwrite the cache. Empty scrapes are not cached. Chub
ingestion does not use this cache.

### Clear / rebuild (embedding model change)

Ingest **adds** vectors and does not replace the index. After changing the
embedding model, clear first, then reingest:

```bash
# Clear entire index (interactive confirm; type yes)
python -m ingestion --clear --framework all

# Clear selected namespaces without prompt
python -m ingestion --clear --framework langgraph,llamaindex -y

# Clear then reingest everything
python -m ingestion --clear --framework all --source all -y
```

- `--clear` requires `--framework`.
- Without `--source`, `--clear` only deletes (no ingest).
- With `--source`, clear runs first; ingest runs only if clear succeeds.
- Omit `-y` / `--yes` to get an interactive confirmation prompt.

## Pin workflow (maintainer)

Extend the agentic-dev expert baseline when you want a package always available offline in Pinecone:

```bash
chub init                          # once per repo
chub pin add langgraph/package --lang python --reason "..."
chub pin list --json
python -m ingestion --source chub  # pull pins into Pinecone
```

Seed pins: `langgraph/package`, `openai/package`, `openai/chat`, `pinecone/sdk`, `pinecone-client/package`, `llama-index/package`.

## Document metadata

Every ingested chunk carries metadata such as:

- `source` — URL or chub doc id  
- `origin` — `firecrawl` | `chub`  
- `framework` — Pinecone namespace  
- chub-only: `doc_id`, `language`, `version`, `title`

## MCP tools (on-demand for user questions)

For Cursor or other MCP clients, run:

```bash
python -m mcp_servers.chub_docs
```

| Tool | Role |
|------|------|
| `search_docs` | Find chub docs for a **user**-asked package/topic |
| `get_doc` | Fetch markdown for a chosen doc id |
| `ingest_doc` | Optionally persist that doc into Pinecone for later |
| `list_pins` | Show the curated baseline pins |

See [chub-mcp-graph-integration.md](./chub-mcp-graph-integration.md) for wiring search/get into the LangGraph flow when retrieval is empty.
