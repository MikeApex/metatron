### 2026-09-24, fourth (phases B and D built in parallel — and the combined tree found what neither window could) — `7c48ade`, `a3bf3e1` + this close-out — **nothing deployed; the VM is still at `b2b1dc7`**

The first parallel run of this build. Two phase windows from the same base (`5ed1abf`), five files
each, **zero overlap** — the claim the coordinating window made when it authorised running them
together, and it held. Both patches applied to the main tree in sequence with no conflict.

**The cross-phase contract was honoured from both ends, which is the result worth recording.**
Phase B wrote its read-set allowlist naming `search_conversations` and `read_journal_range` *before
they existed* (§ 6: "once built") and asserted that an allowlisted name with no handler answers
**501 `needs_tool`**, never 403 or 500. Phase D fitted its two signatures to phase A's already-landed
`manifest._SOURCES` probe rather than editing another phase's file — `start`/`end`, not
`start_date`/`end_date`, **against its own stated preference**, on the grounds that `manifest.py`'s
docstring records what a mismatched argument costs and names `get_log_window`'s `{"days": 14}` as the
instance that made the richest source in the system read as empty for three review rounds. The
schemas matched on first contact: B's open item 2 (check the signatures by hand once both are in one
tree) closed positively without an edit.

**What only the combined tree could find: the doors suite passed 50/50 in its own worktree and
49/50 once both patches were in.** A presence-mode check used `search_conversations` as its fixture
for *an unregistered tool* — true for the hours between B and D, false afterwards. The door was
correct; it returned `state: data, count: 11` because the tool now exists and has data. **Phase B had
anticipated exactly this class and fixed the wrong half:** its handoff's judgement call 4 describes
making the research-mode twin branch on phase D's state, and it did — that check passes — while the
presence-mode sibling went on naming a live tool. One assertion, two homes, one improved. That is
the third time this shape has appeared in this build.

**A second instance of the same defect class, found by chasing the first.** `PENDING_TOOLS` was a
hardcoded frozenset naming the two tools phase D was to build. Nothing was ever wrongly refused —
the actual gate is a live `_handler(name) is None` lookup — but `scripts/vm_read.py --list` went on
advertising two working tools as unbuilt, and **§ 6 makes that surface the description of what the
Librarian may read, which phase C renders into that agent's prompt.** A stale list there would have
told the Librarian a tool it can use does not exist, which is the one direction the read doors exist
to make impossible. Replaced with `pending_tools()`, derived from the registry, and the test now
asserts the derivation tracks a moved registry rather than pinning a written list. *Fixing the class
rather than the instance was chosen deliberately: the read set will name the next unbuilt tool too.*

**Options rejected.** Emptying the `PENDING_TOOLS` constant instead of deriving it — it would be
correct today and stale again at the next tool the read set names ahead of its build, which § 6 says
is the normal case. Landing B and D as one commit — the files do not overlap, so two commits keep
each phase's diff readable and line up with the two handoffs.

**Believed true earlier, corrected by phase D:** this window labelled the sixteen `request_build`
grants **class 2** in `SESSION.md` and in `224e5d4`'s message. `check_agent_tools.py`'s own taxonomy
makes class 2 *named-but-not-granted* and **class 3** *granted-but-never-named*, which is where they
sit. The same run reported class 2 as `0`, which should have been the tell. `SESSION.md` is fixed;
the commit message stands as written. **Do not go looking for a class-2 advisory to confirm B-Red
landed — there is none and there should not be.**

**Also found by phase D and not fixed, because it is outside both phases' files:**
`tests/test_build_manifest.py` **does not exist**, while `core/build/manifest.py`'s docstring cites it
twice as the thing enforcing the content-free rule. So the rule that keeps the manifest safe to
render into a prompt has no test behind it *and the docstring asserts otherwise*, which is worse than
silence. A phase-A gap. Owed before run 1, since the Librarian is the agent the manifest is rendered
to; folding it into phase C is the coordinating window's recommendation, C being where that prompt
gets built. Separately, `register_tools()` returns **80 schemas against 81 handlers** —
`record_wisdom_response` has a handler and no schema, confirmed identical on the base tree, so
unreachable except through `dispatch_tool()`. Neither filed; neither was asked for.

**State:** thirteen suites green in the combined tree (330 checks), `qa_sweep` 12/12 including
`scheduler-functions-resolve`. Phases 0, A, B-Red, B and D are committed and none is deployed.
Remaining: C, its `/adversarial-review` in Fable, then E — which carries **everything in
`b2b1dc7..HEAD`**, not Build's commits alone. Count it at deploy time with
`git rev-list --count b2b1dc7..HEAD` rather than reading a number from here: it was 18 when the
coordinating window first measured it and 29 by this close-out, which is exactly the short-half-life
trap `CLAUDE.md` warns against recording.

