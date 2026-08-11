# Together-Primary Inference Fallback Design

**Date:** 2026-08-08  
**Status:** Approved  
**Approach:** Invert path inside existing `InferenceClientChatModel` / `InferenceClientEmbeddings` (keep call-site API)

## Problem

Hugging Face `InferenceClient` is used as the primary path and frequently times out or is very slow. Together direct inference is faster and should be tried first. Falling back to Together when HF fails (current behavior) does not help when the primary path is already Together via HF routing.

## Goals

1. Call Together direct API as the **primary** inference path.
2. On **timeout or any Together failure**, fall back to Hugging Face `InferenceClient`.
3. HF fallback provider must **never** be `"together"` (do not fall back to the path that just failed).
4. Keep existing call sites (`answer_grader.py`, `generator.py`, etc.) largely unchanged.

## Non-Goals

- Renaming `InferenceClientChatModel`
- Changing RunPod / Ollama paths
- Streaming
- Changing model selection beyond list-order swap and current `gpt-oss-20b` / `gpt-oss-120b` IDs

## Architecture

```
Caller (grader / generator / embeddings)
        │
        ▼
InferenceClientChatModel._generate()  (or Embeddings methods)
        │
        ├─ 1) Together direct (primary)
        │     model = MODEL_IDS[component][0]
        │     timeout = 15s
        │     on success → return result
        │
        └─ 2) on timeout OR any Together error
              → HF InferenceClient (fallback)
                provider = PROVIDER_IDS[component]  # never "together"
                model = MODEL_IDS[component][1]
                on success → return result
                on failure → raise RuntimeError (both failed)
```

### Generator example

| Role | Path | Model |
|------|------|-------|
| Primary | Together direct | `deepseek-ai/DeepSeek-V4-Flash-0731` |
| Fallback | HF `InferenceClient` provider `nebius` | `Qwen/Qwen3-Coder-480B-A35B-Instruct` |

## Config (`config.py`)

### `MODEL_IDS` semantics

**New format:** `[Together primary, HF fallback]`

| Component | Together (primary) | HF (fallback) |
|-----------|-------------------|---------------|
| generator | `deepseek-ai/DeepSeek-V4-Flash-0731` | `Qwen/Qwen3-Coder-480B-A35B-Instruct` |
| router, chub_expert, sentiment/answer/retrieval graders | `openai/gpt-oss-20b` | `openai/gpt-oss-20b` |
| complex_router, hallucinate_grader, summarizer, chitchat | `openai/gpt-oss-120b` | `openai/gpt-oss-120b` |
| embeddings | `BAAI/bge-large-en-v1.5` | `BAAI/bge-large-en-v1.5` |

### `PROVIDER_IDS`

Hardcoded HF fallback providers only. No env default for HF provider. Never `"together"`.

| Component | HF provider |
|-----------|-------------|
| generator | `nebius` |
| complex_router, hallucinate_grader, summarizer, chitchat | `fireworks-ai` *(placeholder — revise later)* |
| router, chub_expert, sentiment/answer/retrieval graders | `novita` *(placeholder — revise later)* |
| embeddings | `hf-inference` *(placeholder — revise later)* |

### Other config

- `direct_provider_org` is always `"together"` (primary path).
- Stop using `INFERENCE_PROVIDER` as the HF provider source.
- Together timeout: **15 seconds** (`TOGETHER_TIMEOUT_SECONDS` env optional, default `15`).

### Wrapper field mapping

| Field | Meaning after change |
|-------|----------------------|
| `direct_model` | `model[0]` — Together primary |
| `model` | `model[1]` — HF fallback |
| `direct_provider` | `"together"` |
| `provider` | HF org from `PROVIDER_IDS` |

## Wrapper behavior (`inference_client_wrapper.py`)

### Chat (`_generate`)

1. Build OpenAI-format messages (existing helpers unchanged).
2. Call Together `chat.completions.create` with `Together(api_key=..., timeout=15)`, including tools/tool_choice when bound.
3. On timeout or any exception: log warning, then call HF `InferenceClient(provider=..., api_key=...).chat_completion(...)` with HF model.
4. If HF fails: raise `RuntimeError` describing both failures.
5. Parse response via existing `_parse_ai_message` (tool calls preserved).

### Embeddings

Same order: Together embeddings primary (15s timeout) → HF `feature_extraction` fallback.

### Call sites

Minimal cleanup: do not default `provider=` to `"together"`. Use `config["provider_org"]` (HF fallback). `direct_provider` remains together from config.

## Error handling

| Event | Behavior |
|-------|----------|
| Together success | Return immediately |
| Together timeout (15s) | Fall back to HF |
| Any other Together error (rate limit, 5xx, network, etc.) | Fall back to HF |
| HF success after fallback | Return; log that fallback was used |
| HF failure after Together failure | Raise `RuntimeError` with both errors |

## Testing

- Together success path returns normally without calling HF.
- Together timeout/error triggers HF fallback (log + successful response).
- Both fail → raised `RuntimeError`.
- Tool-calling (`bind_tools`) still works on both backends.

## Files to change

1. `agent/graph/models/config.py` — MODEL_IDS order/comments, PROVIDER_IDS hardcoding, timeout config key
2. `agent/graph/models/inference_client_wrapper.py` — invert primary/fallback for chat + embeddings
3. Model modules that default `provider` to `"together"` — use config HF provider (no functional change if config is wired correctly)

## Out of scope

- RunPod / Ollama
- Class rename
- Streaming
- Final production values for placeholder HF providers (`fireworks-ai`, `novita`, `hf-inference`)
