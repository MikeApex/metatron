# Session: Vertex VM Migration Decision and Metatron Hold
*2026-06-18*

---

## What happened

Short session. No code written. Two decisions made and recorded.

---

## Decisions

### 1. Metatron infrastructure work on hold
All three next items from the Metatron Android session (always-on Mac, Tailscale dual-network, login/profile selection) are paused until the Vertex VM is provisioned and the codebase is deployed there. Building Mac-specific infrastructure (launchd daemons, pmset sleep settings, Tailscale IP hardcoding) would be throwaway work if the backend moves.

### 2. Full migration to Vertex VM confirmed
All project files move to a Google Vertex VM. This is a full migration, not a sidecar or hybrid.

Privacy ruling status: **covered.** The 2026-06-18 amendment to the binding privacy ruling (in `archive/plans/phase5_to_future_roadmap_2026-06-10.md`, lines 28–36) explicitly permits sensitive agents on a dedicated VM with verified Zero Data Retention (Vertex AI ZDR) during the testing phase. No open question — the ruling was already updated before this session.

---

## Files changed

- `SESSION.md` — hold notice added to Metatron section
- `memory/project_vertex_vm_decision.md` — new; documents migration decision, ZDR coverage, deferred tasks
- `memory/MEMORY.md` — index entry added for Vertex VM decision

---

## Next session

Resume when Vertex VM is provisioned and codebase is deployed. First task: configure Metatron app to point at VM endpoint, then work through the three deferred items (always-on equivalent on VM, network connectivity, login/profile selection).
