# Handoff — CRM merge guard (worktree `metatron-wt-crm-merge-guard`), 2026-08-22

**Shipped — [DB-0822-03], all three parts.** Merging two contacts now asks the user first: the
first `merge_contacts` call changes nothing and returns a confirmation naming **both** people with
the details that tell them apart (spouse, employer, how met, when last spoken to, interaction
count), and the merge runs only when the user approves it in the app — the model never holds the
token. `"ph"` and other digitless or under-5-digit stubs are now refused as phone values, on the
same `write_contact` path that already refused `example.com`; a real number and an omitted field
are both untouched. And a merge can now be reversed: `merge_contacts` writes a pre-merge snapshot
of the *kept* record, and a new `unmerge_contacts(merge_id)` restores both sides from it.

**Commit:** `fd0aed1` "Ask which contact before merging, and make a merge reversible" — one
commit, three files: `tools/crm.py`, `tests/test_crm_merge_guard.py` (new, 25
tests), `tests/test_crm_dedup_guards.py` (4 merge tests routed through the new gate, same update
that file took on 08-19 when the create gate shipped).

**Close [DB-0822-03]** with: `tests/test_crm_merge_guard.py` 25/25, `test_crm_dedup_guards.py`
18/18, `test_crm_placeholders.py` 17/17, plus `test_contact_dedup_gate.py` 14/14,
`test_contact_disambiguation.py`, `test_contacts_import.py` 21/21 and `test_action_provenance.py`
10/10 unaffected. The gate test asserts the store is byte-identical after an ungated call, and that
an approval for one Steven pair cannot be spent on the other — the two-call shape of the live
failure. The agent-prose finding (offering to delete a contact) was explicitly **not** in scope and
is still open.

**Three things `SESSION.md` must carry.**

1. **`unmerge_contacts` is written but NOT registered** — `core/orchestrator.py` is outside this
   worktree's manifest. To expose it, add `unmerge_contacts,` to the `from tools.crm import` list
   (~line 591), `UNMERGE_CONTACTS_SCHEMA` to both schema lists (~591, ~668), `"unmerge_contacts":
   unmerge_contacts,` to the handlers dict (~725), then `"unmerge_contacts"` to `ACTION_TOOLS` in
   `core/actions.py` (or `test_action_provenance.py` fails) and to `relationships`'
   `allowed_tools` in `config/modules/routing.yaml` **and** `routing_cloud.yaml`. Until then it is
   callable in Python only.
2. **The confirm executor is self-registered from `tools/crm.py`, not listed in
   `tools/confirm.py`'s `_EXECUTORS`** — same manifest reason. It works, and fails safe if it ever
   doesn't (the user is told nothing was merged), but the durable one-liner is
   `"merge_contacts": ("tools.crm", "merge_contacts"),` in `_EXECUTORS`. The `setdefault` in crm.py
   yields to it, so adding it there needs no other change.
3. **No merge made before today can be unmerged**, including the live Steven case — there is no
   snapshot of what the friend's record looked like beforehand. `unmerge_contacts` refuses and says
   so. Those two records still need repairing by hand from the archived gym records, which are
   intact.

**Needs `./deploy.sh`** (`tools/`) — not deployed from here.

**Verbatim transcript not captured from this worktree:** `archive_chats.py` resolves the project
root to the worktree, and no JSONL exists under that slug — this subagent's messages live in the
parent session's JSONL under `-Users-md-homefolder-Desktop-multi-model-mcp`. The coordinator's own
`/archive` run captures them. `SESSION.md` and `ROADMAP.md` were not read by this worker (the
context-gate hook warned); the coordinator held that context.
