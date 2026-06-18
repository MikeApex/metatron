# Session: Vertex Setup, Privacy Ruling Revision, Deployment Architecture
*2026-06-18. Continuation of a context-compressed session; earlier portion summarized only (see .txt for details and JSONL for full verbatim).*

---

## What was built / changed

### Roadmap additions (archive/plans/phase5_to_future_roadmap_2026-06-10.md)
- D2 output compression bullet revised to match June 2 session specifics: per-agent token targets, action tag examples, latency estimates
- D2 latency optimizations block added (4 items from June 2: Diarist fire-and-forget, prefix caching structural change, 12B Coordinator split evaluation, Pattern Miner daily cadence)
- D2 age encryption scope expanded: per-persona core files + filesystem permission hardening
- E6 added: multimodal input support (post-Alpha, may pull forward)
- E7 added: file storage tiers — consumable/pointer/owned (design conversation + immediate buildout)
- **Section 0 Amendment 2026-06-18:** dedicated VM with ZDR acceptable for testing; north star unchanged (architectural security on private hardware / A100/H100)

### New file: archive/plans/vertex_setup_prompt_2026-06-17.md
7-step prompt for a dedicated Vertex/GCP setup chat:
1. GCP account + project setup
2. Verify Gemini 3.1 Pro model ID on Vertex
3. Service account credentials
4. Code: swap Gemini client init to Vertex mode
5. Smoke test
5b. Routing config split (routing_cloud.yaml + DEPLOYMENT_MODE env var)
6. VM setup (e2-medium)
6b. Git auto-deploy workflow (post-push hook)
7. VPC networking (production-grade)
Plus 4 open questions (SDK compatibility, current model ID, ZDR tier, grounded search on Vertex).

### Privacy ruling updated (3 files)
- Roadmap Section 0
- memory/project_privacy_never_cloud.md
- SESSION.md

---

## Key decisions made

- **Privacy ruling revised:** shared cloud API ≠ dedicated VM with ZDR. The latter is acceptable for testing. North star (architectural/private hardware) unchanged.
- **Ollama-on-VM ruled out:** e2-medium can't run qwen3:14b; larger VM + CPU inference is slower and more expensive than Vertex. Vertex ZDR is the right choice on a GCP VM.
- **"Local" is relative to orchestrator host:** if orchestrator runs on VM, localhost:11434 is the VM — no Ollama there means sensitive agents hard-fail. VM deployment is scoped to decontextualized paths (Research Agent, model conferences) unless architecture is revised.
- **One codebase, not two:** routing_cloud.yaml + DEPLOYMENT_MODE env var is the toggle. Local dev unchanged; VM is a runtime target.
- **TLS = encrypted:** public internet TLS is fully encrypted; VPC is about routing path (private fiber), not adding encryption on top.

---

## Deferred / open

- Vertex setup session not yet run — prompt is ready at archive/plans/vertex_setup_prompt_2026-06-17.md
- Open questions in the prompt (SDK compat, model IDs, ZDR tier) to be resolved in that session
- VM + VPC setup (Step 7) deferred until testing passes
- Decision on Metatron hosting (local Mac vs. cloud VM) still pending (noted in SESSION.md as HOLD 2026-06-17)
- Full pipeline on VM requires either: split deployment (Mac handles sensitive agents), CPU Ollama (slow), or formal privacy ruling extension beyond testing
