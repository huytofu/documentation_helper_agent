# Retrieve: direct topic dump vs embedding match

**Date:** 2026-08-11  
**Status:** Approved for planning  
**Scope:** Mode detection inside `RETRIEVE`, chub `doc_id` chunk dump, post-retrieve routing (skip grade / browse refuse leaf). Router (`route_and_framework`) unchanged.

## Problem

After `KB_META` lists indexed topics (frameworks + chub packages like `stripe/package`), a follow-up such as “I want to read contents of stripe/package” still goes through normal similarity search on the query embedding.

That path:

1. Does not systematically return **all** chunks for an exact indexed topic.
2. Has no first-class distinction between **browse/dump a known topic** and **match relevant chunks to a question**.
3. Cannot safely “dump” large framework namespaces (`langgraph`, `llamaindex`, `smolagents`, `copilotkit`) — those contain many documents.

## Goals

- Add a retrieval mode chosen **inside** `RETRIEVE` (router stays `vectorstore` + `framework` as today):
  - `embedding_match` — current behavior (similarity search in the selected namespace).
  - `direct_<topic_id>` — dump all indexed chunks for one chub catalog `doc_id`.
- Detect mode with a **small LLM** (gpt-oss-20b class) and structured output `{mode, topic_id}`, catalog in prompt.
- For `direct_*` when `framework != "chub"`: soft refuse via a new leaf (large corpus; ask a specific question).
- For successful chub `direct_*`: **skip** `GRADE_DOCUMENTS` and go to `GENERATE`.
- No chunk cap (one chub source document → bounded chunk set).

## Non-goals

- Changing `RouteAndFramework` schema or datasource set.
- Dumping entire framework namespaces.
- Live Pinecone stats / TOC listing for large namespaces (v1 refuse + guide only).
- Heuristic-only mode detection (v1 is LLM-only).
- Chunk caps / truncation flags.
- Changing ingestion metadata shape beyond using existing `doc_id` / `source`.

## Decision summary

| Choice | Decision |
|--------|----------|
| Architecture | Single `RETRIEVE` node + `after_retrieve` routing |
| Mode detection | Small LLM structured output; catalog in prompt |
| Mode encoding | `retrieval_mode = "embedding_match"` or `"direct_<topic_id>"` |
| Large namespaces | `direct_*` + non-`chub` → `BROWSE_REFUSE` → END |
| Chub dump | All chunks for `doc_id`, ordered; no cap; skip grading |
| Router | Unchanged |

## Architecture

```
ROUTE_AND_FRAMEWORK (unchanged: vectorstore + framework)
        │
        ▼
     RETRIEVE
        │  1) Load chub catalog (state kb_catalog or store)
        │  2) Small LLM → {mode: embedding_match|direct, topic_id}
        │  3) If direct + topic_id → retrieval_mode = "direct_<topic_id>"
        │     else → retrieval_mode = "embedding_match"
        │  4) Fetch branch:
        │       • direct_* + framework != chub → documents=[], keep mode
        │       • direct_* + framework == chub → metadata-filter dump all chunks
        │       • else → get_retriever(framework).invoke(query)
        ▼
  after_retrieve
        ├── browse refuse (direct_* && framework != chub) → BROWSE_REFUSE → END
        ├── direct_* (chub dump path) → GENERATE
        └── embedding_match → GRADE_DOCUMENTS → … (unchanged)
```

## State

Add on `GraphState` / `OutputGraphState`:

```python
retrieval_mode: str = "embedding_match"
```

- Default / normal path: `"embedding_match"`.
- Browse path: `"direct_<topic_id>"` where `topic_id` is a catalog doc id (e.g. `direct_stripe/package`).

Optional reuse: if `kb_catalog` is already on state from a prior `kb_meta` turn it may be used; otherwise `RETRIEVE` loads catalog via the same store helpers as the router (`CHUB_PACKAGES_NS` + `format_chub_packages_for_prompt`).

## Classifier

### Files

- `agent/graph/chains/retrieval_mode.py` — prompt + pydantic parser
- `agent/graph/models/` — model wiring aligned with other gpt-oss-20b routers (new slot or reuse router model config)
- `agent/graph/models/config.py` — register model key if needed

### Contract

```text
mode: Literal["embedding_match", "direct"]
topic_id: str  # catalog doc_id when mode=direct; else ""
```

After a successful `direct` classification with non-empty `topic_id`, the node sets:

```text
retrieval_mode = "direct_" + topic_id
```

### Prompt rules

- Prefer `direct` only when the user wants to **read / show / browse / dump contents** of a **specific** package/topic that appears in the indexed chub catalog.
- `topic_id` must be copied from the catalog (exact `doc_id`), not invented.
- How-to / API / “explain X” questions → `embedding_match` even if a package name appears.
- If catalog is empty / `"(none indexed yet)"` → `embedding_match`.
- On LLM/parse failure → treat as `embedding_match`.
- If `mode=direct` but `topic_id` empty or not in catalog → fall back to `embedding_match`.

## RETRIEVE behavior

1. Emit CopilotKit state / wait message as today.
2. Resolve `query`, `framework`, catalog.
3. Invoke classifier; set `retrieval_mode`.
4. Branch:

| Condition | Action |
|-----------|--------|
| `retrieval_mode` starts with `direct_` and `framework != "chub"` | Return `documents=[]`, `retrieval_mode` unchanged |
| `retrieval_mode` starts with `direct_` and `framework == "chub"` | Extract `topic_id` after prefix `direct_`; fetch all chunks with metadata filter on `doc_id` (and/or `source`); sort by available chunk id / position metadata; **no cap**; return documents |
| else | Existing `get_retriever(framework).invoke(query)` |

### Direct fetch notes

- Ingest already stores `metadata.doc_id` (and `source`) for chub docs — filter on that.
- Implementation may use Pinecone/LangChain APIs that accept a metadata filter; prefer listing/filtering by `doc_id` rather than ranking by query embedding. If the SDK requires a vector query, use a filter-constrained query with sufficiently high `k` to cover one document’s chunks, then sort deterministically — still treat this as the dump path (no grading).
- Empty result set: still `direct_*` + skip grade → `GENERATE` (model can say nothing found). Do **not** send empty chub dumps to `BROWSE_REFUSE`.

## BROWSE_REFUSE leaf

### Files

- `agent/graph/consts.py` — e.g. `BROWSE_REFUSE = "browse_refuse"`
- `agent/graph/nodes/browse_refuse.py` — async leaf
- Export + wire in `real_flow.py`

### Behavior

1. Emit `current_node: "BROWSE_REFUSE"`.
2. Append AIMessage (`display_in_chat: True`) explaining that this namespace is a large corpus and cannot be dumped wholesale; ask the user for a specific question (next turn → normal `embedding_match`).
3. `reset_flow_state()` as other leaves.
4. Edge → END.

No graders, no generate, no websearch on this path.

## Graph wiring

Replace hard edge `RETRIEVE → GRADE_DOCUMENTS` with:

```python
def after_retrieve(state: GraphState) -> str:
    mode = state.get("retrieval_mode") or "embedding_match"
    framework = state.get("framework")
    if mode.startswith("direct_") and framework != "chub":
        return BROWSE_REFUSE
    if mode.startswith("direct_"):
        return GENERATE
    return GRADE_DOCUMENTS
```

## Error handling

| Failure | Behavior |
|---------|----------|
| Classifier timeout/exception | `embedding_match`; normal retrieve |
| Catalog store read fails | Catalog `"(none indexed yet)"`; classifier almost always embedding |
| Direct + unknown topic_id | Fall back to embedding before fetch |
| Direct + chub + 0 chunks | GENERATE with empty docs |
| Direct + non-chub | BROWSE_REFUSE |
| Vector store unavailable | Same as today (empty docs) for embedding path; for direct dump, empty docs → GENERATE |

## Testing

Prefer mocked LLM / vector store; no live Pinecone required.

1. **Classifier**
   - “Read contents of stripe/package” + catalog containing that id → `direct` + `topic_id=stripe/package`.
   - “How do I create a Stripe customer?” → `embedding_match`.
2. **Retrieve node**
   - `direct_stripe/package` + `framework=chub` → filtered dump, ordered.
   - `direct_*` + `framework=langgraph` → empty documents, mode preserved.
3. **after_retrieve**
   - chub direct → `GENERATE`
   - non-chub direct → `BROWSE_REFUSE`
   - embedding → `GRADE_DOCUMENTS`
4. **BROWSE_REFUSE**
   - Message has `display_in_chat: True`.

## Future extension (out of scope)

- Namespace TOC / drill-down for large frameworks before dump.
- Optional chunk caps if multi-doc topics appear under one `doc_id`.
- Sharing classifier with router if browse intent becomes common enough to route earlier.

## Self-review checklist

- No TBDs for v1 behavior.
- Router unchanged; mode owned by `RETRIEVE`.
- Refuse only for large-namespace browse; empty chub dump goes to GENERATE.
- Skip grading only on `direct_*` success path to GENERATE.
- Catalog source matches router (LTM chub packages).
