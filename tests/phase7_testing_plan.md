# Phase 7 Testing Plan — Multi-User Architecture

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

The tool supports multiple users without any user's sensitive data touching another user's context, ever. Cloud dispatch provides genuine k-anonymity at scale — no individual user's identity is recoverable from the cloud request stream. Each user's experience is as private and grounded as the single-user system.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| Single-user system stable (Phase 6) | 6+ months production use, no data loss incidents |
| User research session completed | Multi-user consent model and onboarding flow validated |
| Per-user data isolation architecture designed | Each user's sensitive data is in a separate, access-controlled path |
| Identifiability threshold logic implemented | `core/router.py` or equivalent applies the threshold before cloud dispatch |
| 2+ test user accounts provisioned | Separate keys, separate data paths |

---

## Intent Checks

### 1. Zero cross-user data leakage
- Create two users with distinct prime directives and goals; run sessions for each
- **Pass:** Neither user's session context contains any data from the other user's files; verified by inspecting prompt payloads
- **Fail:** Any cross-user data appears in any prompt or response

### 2. Identifiability threshold blocks identifiable requests
- Submit a request containing identifying information (name, specific goal detail)
- **Pass:** Request is held by the private model; not dispatched to cloud until sufficiently decontextualized
- **Fail:** Identifying request dispatched to cloud provider

### 3. Cloud request stream is not individually attributable
- Examine cloud API request logs across multiple users over a session
- **Pass:** An outside observer with access to the cloud logs cannot determine which request belongs to which user
- **Fail:** User identity is recoverable from request content or metadata

### 4. Onboarding is self-service
- A new user completes goals interview, populates config, and conducts first session without developer intervention
- **Pass:** New user onboards end-to-end following documented steps only
- **Fail:** Any step requires developer involvement

### 5. Per-user encryption keys are isolated
- Compromise one user's key (simulate)
- **Pass:** Only that user's data is accessible; other users' data remains encrypted and inaccessible
- **Fail:** One key compromise exposes any other user's data

### 6. System scales without per-user code changes
- Add a third user
- **Pass:** Third user onboards by adding config and data files only; no code changes required
- **Fail:** Adding a user requires code changes

---

## Sign-off

Phase 7 is complete when: cross-user isolation is verified (Check 1), identifiability threshold works (Check 2), and self-service onboarding is confirmed (Check 4). The k-anonymity property (Check 3) requires a sufficient user base to test fully — document the minimum pool size threshold at which cloud dispatch is considered safe.
