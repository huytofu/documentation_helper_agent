# README + DEPLOYMENT.md Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deploy-heavy `README.md` with an end-user landing page and move operator content into `DEPLOYMENT.md`.

**Architecture:** Docs-only change. `DEPLOYMENT.md` receives the current README’s model/env/install/deploy sections (reorganized). `README.md` becomes overview → try it → what it does → high-level mermaid → notes + link to deploy docs. Keep `VERCEL_DEPLOYMENT.md` and link it from `DEPLOYMENT.md`.

**Tech Stack:** Markdown; Mermaid diagram in README.

## Global Constraints

- Audience: end users / demos for README
- Graph depth: high-level only (approved mermaid from spec)
- Do not delete or rewrite `VERCEL_DEPLOYMENT.md`
- Do not change application code
- Hosted URL: `https://documentation-helper-agent-aur6f7jff-huy-tos-projects.vercel.app/`
- Limit: 20 messages per user per day
- Spec: `docs/superpowers/specs/2026-08-11-readme-deployment-docs-design.md`

---

### Task 1: Create DEPLOYMENT.md

**Files:**
- Create: `DEPLOYMENT.md`
- Source content: current `README.md` (model config through performance)
- Link: `VERCEL_DEPLOYMENT.md`

**Interfaces:**
- Consumes: Existing README operator sections
- Produces: Root `DEPLOYMENT.md` with sections Architecture → Model options → Env vars (+ Firebase) → Install & local run → Ingestion pointer → Cloud Run → Frontend link → RunPod → Performance

- [ ] **Step 1: Write DEPLOYMENT.md** with reorganized content from current README; frontend section must link to `VERCEL_DEPLOYMENT.md` (not duplicate it).

- [ ] **Step 2: Spot-check** that Cloud Run steps, env var block, install, ingestion, RunPod, Firebase, and performance notes are present.

- [ ] **Step 3: Commit** (optional if batching with Task 2)

```bash
git add DEPLOYMENT.md
git commit -m "docs: add DEPLOYMENT.md with operator guidance from README"
```

---

### Task 2: Rewrite README.md

**Files:**
- Modify: `README.md` (full rewrite)
- Link: `DEPLOYMENT.md`

**Interfaces:**
- Consumes: Approved structure + mermaid from design spec
- Produces: End-user README with Try it URL and 20 msg/day limit

- [ ] **Step 1: Replace README.md** with Overview, Try it, What it does, How it works (mermaid + caption), Notes, Further reading → DEPLOYMENT.md.

- [ ] **Step 2: Verify** no env/install/Cloud Run content remains in README; URL and limit are present; mermaid matches spec.

- [ ] **Step 3: Commit**

```bash
git add README.md DEPLOYMENT.md
git commit -m "docs: make README demo-focused; move deploy docs to DEPLOYMENT.md"
```

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| End-user README sections | Task 2 |
| Approved mermaid | Task 2 |
| Move deploy/env to DEPLOYMENT.md | Task 1 |
| Link VERCEL_DEPLOYMENT.md | Task 1 |
| No app code changes | Global |
