# Together-Primary Inference Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Make Together the primary inference path with a 15s timeout, falling back to non-Together HF InferenceClient on any Together failure.

**Architecture:** Invert order inside existing `InferenceClientChatModel` / `InferenceClientEmbeddings`. Swap `MODEL_IDS` to `[Together, HF]`. Hardcode `PROVIDER_IDS` (never together).

**Tech Stack:** Together Python SDK, huggingface_hub InferenceClient, LangChain BaseChatModel

## Global Constraints

- Together timeout: 15 seconds
- Fallback on timeout OR any Together error
- HF provider never `"together"`
- `MODEL_IDS` = `[Together primary, HF fallback]`
- Keep call-site constructor shape

---

### Task 1: Config

**Files:** `agent/graph/models/config.py`

- [ ] Swap generator MODEL_IDS to `[DeepSeek-V4-Flash, Qwen3-Coder]`
- [ ] Update comments for new list semantics
- [ ] Hardcode PROVIDER_IDS (nebius / fireworks-ai / novita / hf-inference)
- [ ] Set `direct_provider_org` to `"together"`; expose `together_timeout` (default 15)
- [ ] Assert no PROVIDER_IDS value is `"together"`

### Task 2: Wrapper invert

**Files:** `agent/graph/models/inference_client_wrapper.py`

- [ ] Map `direct_model=model[0]`, HF `model=model[1]`
- [ ] Together-first in `_generate` with `Together(..., timeout=15)`
- [ ] On any Together failure → HF chat_completion
- [ ] Same for embeddings
- [ ] Pass timeout via kwargs/config if available

### Task 3: Call-site defaults

**Files:** all model modules using InferenceClient*

- [ ] Remove `"together"` default for HF `provider=` (use config only / non-together default)

### Task 4: Smoke verify

- [ ] Import wrapper + config under venv; sanity-check MODEL_IDS order and PROVIDER_IDS
