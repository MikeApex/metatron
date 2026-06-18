# Phase 6 Testing Plan — Dedicated Hardware + Full Encryption

*Intent-driven. Tests whether the phase achieved its purpose, not just whether the code runs.*

---

## Phase Intent

The tool moves off the developer's laptop onto always-on dedicated hardware. All sensitive data is encrypted at rest. The system survives a machine restart without losing state or requiring manual reconfiguration. The user's data is protected even if the hardware is physically compromised.

---

## Prerequisites Check

| Prerequisite | Check |
|---|---|
| All Phase 5 modules working | Phase 5 sign-off complete |
| Alpha data accumulating | `quality_events.json` and daily logs live since Alpha ship; cold-start baselines (roadmap A3) stand in for long-history state-anchored baselines — the old "6+ months real data" prerequisite is retired (amended 2026-06-10) |
| Dedicated machine provisioned | Hardware selected and running |
| `age` installed | `age --version` on target machine |
| Syncthing installed | `syncthing --version` on both devices |
| `age` keypair generated | Key file exists at documented location |

---

## Intent Checks

### 1. System survives a cold restart
- Power off the dedicated machine; power it back on
- **Pass:** Scheduler, server, and all services restart automatically; no manual intervention required; no data loss
- **Fail:** Any service requires manual restart; or session state is lost

### 2. All sensitive data is encrypted at rest
- With machine powered off, examine the raw files on disk
- **Pass:** `data/logs/`, `data/journal/`, `data/wisdom/`, and goal config files are `age`-encrypted; unreadable without the key
- **Fail:** Any sensitive file is stored in plaintext

### 3. Encrypted data is fully functional when key is present
- Decrypt and run a full session with all tools
- **Pass:** All tools read/write correctly; no functionality lost due to encryption
- **Fail:** Any tool fails due to encryption layer

### 4. Syncthing sync is encrypted in transit and functional
- Modify a file on laptop; confirm it syncs to dedicated machine
- **Pass:** File appears on target within sync interval; Syncthing reports TLS-encrypted connection
- **Fail:** Sync fails, or transfers in plaintext

### 5. Local LLM stack is fully operational
- Run Diarist and Pattern Miner sessions
- **Pass:** Both route to local LLM; `routing_fallbacks.json` shows zero cloud fallbacks for sensitive agents
- **Fail:** Any sensitive agent falls back to cloud

### 6. Key management is documented and recoverable
- Follow the documented key recovery procedure from scratch
- **Pass:** A new operator can decrypt data using only the documented procedure and the passphrase
- **Fail:** Recovery requires undocumented steps or fails entirely

---

## Sign-off

Phase 6 is complete when: cold restart works (Check 1), all sensitive data is encrypted (Check 2), full functionality is preserved (Check 3), sync works (Check 4), and local LLM handles all sensitive routing (Check 5).
