"""
tests/test_crm_merge_guard.py — [DB-0822-03] the merge confirmation gate, the
junk-phone guard, and unmerge.

The incident these cover, live 2026-08-19: "Steven from the gym and Stephen from the
gym are the same person. Merge them, keeping Steven." There were THREE Stevens. The
agent picked the keep_id of the user's actual friend and folded both gym records into
him, across two merge_contacts calls, without asking which Steven was meant. His
record now says he was met at the gym and carries a phone of "ph".

Three separate failures, one per section below:

  1. merge_contacts asked nobody. `_ambiguous_match` guards NAME lookups; merge takes
     ids, so nothing checked that the CHOICE of id was unambiguous. Now gated through
     tools/confirm.py, with a description naming both people and their distinguishing
     details — the same two-step shape as the near-match create gate (`6d6d46c`), and
     the same principle: the model is not in the consent path.
  2. `_is_placeholder_phone` did not catch "ph". It covered fictional RANGES, and
     asked "is this a reserved number?" without ever asking "is this a number?".
  3. There was no unmerge, and no way to build one after the fact — the loser was
     archived whole, but the survivor was edited in place. merge_contacts now writes
     a pre-merge snapshot of the survivor, and unmerge_contacts restores both sides
     from it. Merges made before that have no snapshot and must refuse honestly; the
     Steven merges themselves are in that category, permanently.

Standalone runner (no pytest dependency), matching tests/test_crm_dedup_guards.py.

Usage:
    python3 tests/test_crm_merge_guard.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.confirm as CF  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.profile as PR  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test function, record pass/fail rather than aborting."""
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _temp_persona_dir:
    """Point tools.crm, tools.profile and tools.confirm at an empty temp directory —
    same fixture and same reasoning as tests/test_crm_dedup_guards.py: each module
    binds its persona_*_dir by name at import, so each needs its own patch."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig_crm_data = CRM.persona_data_dir
        self._orig_pr_config = PR.persona_config_dir
        self._orig_cf_data = CF.persona_data_dir
        CRM.persona_data_dir = lambda persona=None: self.path / "data"
        PR.persona_config_dir = lambda persona=None: self.path / "config"
        CF.persona_data_dir = lambda persona=None: self.path / "data"
        return self.path

    def __exit__(self, *exc):
        CRM.persona_data_dir = self._orig_crm_data
        PR.persona_config_dir = self._orig_pr_config
        CF.persona_data_dir = self._orig_cf_data
        self._tmp.cleanup()


def _create(name: str, **kw) -> str:
    """Create a contact and return its id, approving the near-match create gate if it
    fires. Names in these fixtures are deliberately the three Stevens, which DO trip
    that gate — that is the 08-19 gate working, not a fixture problem."""
    result = CRM.write_contact(name=name, **kw)
    if "PENDING_CONFIRMATION" not in result:
        return result.splitlines()[0]
    token = json.loads(result)["confirm_token"]
    CF.approve(token)
    outcome = CF.execute(token)
    assert outcome.get("status") == "executed", outcome
    return CRM._load_contacts()[-1]["id"]


def _merge_approved(keep_id: str, merge_id: str) -> str:
    """Walk the two steps a user does: the tool raises a pending request, the server
    approves it out of band and executes it. The model is never handed the token."""
    pending = CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)
    assert "PENDING_CONFIRMATION" in pending, pending
    token = json.loads(pending)["confirm_token"]
    assert CF.approve(token) is True
    outcome = CF.execute(token)
    assert outcome.get("status") == "executed", outcome
    return outcome["result"]


def _three_stevens() -> tuple[str, str, str]:
    """The recorded cast. `friend` is the one that must not be silently chosen."""
    friend = _create(
        "Steven Okafor", relationship_type="friend", spouse_name="Yana",
        employer="Northbank Legal", how_met="university", last_contact="2026-06-21",
    )
    gym_a = _create("Steven", relationship_type="acquaintance", how_met="at the gym")
    gym_b = _create("Stephen", relationship_type="acquaintance", how_met="at the gym")
    return friend, gym_a, gym_b


# ---------------------------------------------------------------------------
# 1. The merge confirmation gate
# ---------------------------------------------------------------------------

@check("merge_contacts without a token merges NOTHING and returns a pending request")
def _():
    with _temp_persona_dir():
        friend, gym_a, gym_b = _three_stevens()
        before = json.loads(json.dumps(CRM._load_contacts()))

        result = CRM.merge_contacts(keep_id=friend, merge_id=gym_a)
        payload = json.loads(result)
        assert payload["status"] == "PENDING_CONFIRMATION", payload
        assert payload["confirm_token"], payload

        # The whole point: the store is byte-identical afterwards. The 08-19 failure
        # was that this call had already happened by the time anyone could object.
        assert CRM._load_contacts() == before, "merge_contacts mutated data before approval"
        assert CRM._crm_archive_dir().exists() is False or not list(
            CRM._crm_archive_dir().glob("*.json")
        ), "an ungated merge wrote to the archive"


@check("the pending description names BOTH people with the details that tell them apart")
def _():
    with _temp_persona_dir():
        friend, gym_a, _gym_b = _three_stevens()
        payload = json.loads(CRM.merge_contacts(keep_id=friend, merge_id=gym_a))
        desc = payload["description"]

        # It must be readable standing alone, without the conversation around it.
        assert "Steven Okafor" in desc, desc
        assert friend in desc and gym_a in desc, desc
        # The four details that would have caught the wrong Steven.
        assert "Yana" in desc, desc                  # spouse
        assert "Northbank Legal" in desc, desc       # employer
        assert "2026-06-21" in desc, desc           # last spoken to
        assert "at the gym" in desc, desc            # how met, on the OTHER record
        # And it must be unambiguous which way round the merge runs.
        assert "KEEPING" in desc and "FOLDING IN" in desc, desc


@check("an approved merge executes and keeps the previous merge semantics exactly")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond", relationship_type="family", tags=["family"])
        merge_id = _create("Eva", occupation="Retired teacher", tags=["needs_follow_up"])

        result = _merge_approved(keep_id, merge_id)
        assert "Merged" in result, result

        kept = json.loads(CRM.read_contact(contact_id=keep_id))
        assert kept["occupation"] == "Retired teacher", kept   # empty field filled in
        assert kept["relationship_type"] == "family", kept     # set field left alone
        assert set(kept["tags"]) == {"family", "needs_follow_up"}, kept

        assert all(c["id"] != merge_id for c in CRM._load_contacts())

        archived_files = list(CRM._crm_archive_dir().glob(f"{merge_id}_*.json"))
        assert len(archived_files) == 1, archived_files
        archived = json.loads(archived_files[0].read_text())
        assert archived["merged_into"] == keep_id, archived
        assert archived["name"] == "Eva", archived

        # The old id still resolves to the survivor — the archive-on-merge contract.
        assert json.loads(CRM.read_contact(contact_id=merge_id))["id"] == keep_id


@check("an approval for one pair of Stevens cannot be spent on a different pair")
def _():
    with _temp_persona_dir():
        friend, gym_a, gym_b = _three_stevens()
        payload = json.loads(CRM.merge_contacts(keep_id=friend, merge_id=gym_a))
        token = payload["confirm_token"]
        CF.approve(token)

        # The 08-19 incident was TWO merges. The fingerprint in tools/confirm.py is
        # what stops one tap authorising the second one.
        result = CRM.merge_contacts(keep_id=friend, merge_id=gym_b, confirm_token=token)
        assert result.startswith("Error: not merged."), result
        live_ids = {c["id"] for c in CRM._load_contacts()}
        assert {friend, gym_a, gym_b} <= live_ids, live_ids


@check("an approval is single-use — the same token cannot merge twice")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond")
        merge_id = _create("Eva")
        pending = CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id)
        token = json.loads(pending)["confirm_token"]
        CF.approve(token)
        assert CF.execute(token).get("status") == "executed"

        again = CRM.merge_contacts(keep_id=keep_id, merge_id=merge_id,
                                   confirm_token=token)
        assert again.startswith("Error: not merged."), again


@check("merge_contacts still refuses bad ids, and refuses them BEFORE raising a gate")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond")
        assert CRM.merge_contacts(keep_id=keep_id, merge_id="not-a-real-id").startswith("Error:")
        assert CRM.merge_contacts(keep_id=keep_id, merge_id=keep_id).startswith("Error:")
        assert CRM.merge_contacts(keep_id="", merge_id=keep_id).startswith("Error:")
        # No confirmation should have been raised for any of them — a pending request
        # the user cannot act on usefully is noise in the approval queue.
        assert CF.pending() == [], CF.pending()


@check("merge_contacts is wired into the confirm executor registry")
def _():
    # Without this, the user taps Approve and the server has nothing to call — the
    # exact [DB-0815-03] failure ("waiting for your approval in the app", forever).
    from tools.confirm import _EXECUTORS
    assert _EXECUTORS.get("merge_contacts") == ("tools.crm", "merge_contacts"), _EXECUTORS


# ---------------------------------------------------------------------------
# 2. The junk-phone guard
# ---------------------------------------------------------------------------

@check("'ph' is flagged as junk — the literal value that reached the friend's record")
def _():
    reason = CRM._is_placeholder_phone("ph")
    assert reason, "'ph' was not flagged"
    assert "no digits" in reason, reason


@check("other digitless stubs are flagged the same way")
def _():
    for value in ("n/a", "N/A", "tbc", "unknown", "--", "phone"):
        assert CRM._is_placeholder_phone(value), f"{value!r} was not flagged"


@check("a value with fewer than 5 digits is flagged as too short")
def _():
    for value in ("2481", "12", "0", "+44 7"):
        reason = CRM._is_placeholder_phone(value)
        assert reason, f"{value!r} was not flagged"
        assert "too short" in reason or "no digits" in reason, reason


@check("a real UK mobile outside the drama range is NOT flagged")
def _():
    assert CRM._is_placeholder_phone("07700 800123") is None
    assert CRM._is_placeholder_phone("+44 7700 800123") is None
    assert CRM._is_placeholder_phone("(020) 7946 1234") is None
    assert CRM._is_placeholder_phone("+1 415 555 2671") is None


@check("an empty or absent phone is NOT flagged — omitting a field is correct")
def _():
    assert CRM._is_placeholder_phone("") is None
    assert CRM._is_placeholder_phone("   ") is None
    assert CRM._is_placeholder_phone(None) is None


@check("the known fictional ranges are still caught (no regression)")
def _():
    assert CRM._is_placeholder_phone("+44 (0)7700 900123")
    assert CRM._is_placeholder_phone("555-0100")
    assert CRM._is_placeholder_phone("1234567890")


@check("write_contact refuses a contact whose phone is 'ph', and saves nothing")
def _():
    with _temp_persona_dir():
        result = CRM.write_contact(name="Steven Okafor", contact_info={"phone": "ph"})
        assert result.startswith("Error: not saved."), result
        assert "placeholder" in result or "phone" in result, result
        assert CRM._load_contacts() == [], CRM._load_contacts()


@check("write_contact still accepts a real number on the same path")
def _():
    with _temp_persona_dir():
        cid = _create("Steven Okafor", contact_info={"phone": "07700 800123"})
        saved = json.loads(CRM.read_contact(contact_id=cid))
        assert saved["contact_info"]["phone"] == "07700 800123", saved


# ---------------------------------------------------------------------------
# 3. unmerge
# ---------------------------------------------------------------------------

_MERGE_TOUCHED_FIELDS = [
    "name", "first_name", "last_name", "nickname", "primary_contact_type",
    "relationship_type", "relationship_quality", "contact_frequency_preference",
    "spouse_name", "education", "occupation", "employer", "how_met",
    "timezone", "tone_shape", "notes", "referred_to_as", "kids_names", "tags",
    "important_dates", "contact_info", "interaction_log", "last_contact",
]


@check("merge_contacts writes a pre-merge snapshot of the KEPT record")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)

        snaps = list(CRM._crm_archive_dir().glob(f"premerge_{gym_a}_*.json"))
        assert len(snaps) == 1, snaps
        snap = json.loads(snaps[0].read_text())
        assert snap["id"] == friend, snap
        assert snap["record_type"] == "pre_merge_snapshot", snap
        assert snap["snapshot_of_merge"] == {"keep_id": friend, "merge_id": gym_a}, snap
        # Pre-merge state: the friend had NOT been met at the gym.
        assert snap["how_met"] == "university", snap
        # And it must carry no merged_into, or the archive scans would follow it.
        assert "merged_into" not in snap, snap


@check("unmerge round-trips: both records come back identical on every merged field")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        keep_before = json.loads(CRM.read_contact(contact_id=friend))
        merge_before = json.loads(CRM.read_contact(contact_id=gym_a))

        _merge_approved(friend, gym_a)
        # Sanity: the merge really did corrupt the friend's record the 08-19 way.
        during = json.loads(CRM.read_contact(contact_id=friend))
        assert during["how_met"] == "university", during
        assert all(c["id"] != gym_a for c in CRM._load_contacts())

        result = CRM.unmerge_contacts(merge_id=gym_a)
        assert result.startswith("Unmerged:"), result

        keep_after = json.loads(CRM.read_contact(contact_id=friend))
        merge_after = json.loads(CRM.read_contact(contact_id=gym_a))

        for field in _MERGE_TOUCHED_FIELDS:
            assert keep_after.get(field) == keep_before.get(field), (
                f"kept record field '{field}' not restored: "
                f"{keep_before.get(field)!r} -> {keep_after.get(field)!r}"
            )
            assert merge_after.get(field) == merge_before.get(field), (
                f"restored record field '{field}' differs: "
                f"{merge_before.get(field)!r} -> {merge_after.get(field)!r}"
            )
        assert merge_after["id"] == gym_a, merge_after
        # It is a live contact again, not an archive redirect.
        assert "_merged_note" not in merge_after, merge_after


@check("unmerge restores a record whose fields the merge actually changed")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond", relationship_type="family", tags=["family"])
        merge_id = _create("Eva", occupation="Retired teacher", tags=["needs_follow_up"],
                           notes="Taught at Fairfield until 2011.")
        _merge_approved(keep_id, merge_id)

        during = json.loads(CRM.read_contact(contact_id=keep_id))
        assert during["occupation"] == "Retired teacher", during
        assert set(during["tags"]) == {"family", "needs_follow_up"}, during

        CRM.unmerge_contacts(merge_id=merge_id)
        after = json.loads(CRM.read_contact(contact_id=keep_id))
        assert not after.get("occupation"), after
        assert after["tags"] == ["family"], after
        assert not after.get("notes"), after

        back = json.loads(CRM.read_contact(contact_id=merge_id))
        assert back["occupation"] == "Retired teacher", back
        assert back["notes"] == "Taught at Fairfield until 2011.", back


@check("unmerge refuses honestly when there is no snapshot (every pre-2026-08-22 merge)")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond")
        merge_id = _create("Eva")
        _merge_approved(keep_id, merge_id)

        # Simulate a merge made before snapshots existed: delete the snapshot only.
        for p in CRM._crm_archive_dir().glob(f"premerge_{merge_id}_*.json"):
            p.unlink()
        before = json.loads(json.dumps(CRM._load_contacts()))

        result = CRM.unmerge_contacts(merge_id=merge_id)
        assert result.startswith("Error:"), result
        assert "cannot be reversed" in result, result
        # Honest, not vague: it says why, and says the archived loser is still intact.
        assert "2026-08-22" in result, result
        assert "by hand" in result, result
        # And it must be a true no-op.
        assert CRM._load_contacts() == before, "a refused unmerge changed data"


@check("unmerge refuses an id that was never merged, and one already live")
def _():
    with _temp_persona_dir():
        keep_id = _create("Iva Diamond")
        assert CRM.unmerge_contacts(merge_id=keep_id).startswith("Error:")
        assert "already a live contact" in CRM.unmerge_contacts(merge_id=keep_id)
        assert CRM.unmerge_contacts(merge_id="not-a-real-id").startswith("Error:")
        assert CRM.unmerge_contacts(merge_id="").startswith("Error:")


@check("unmerge deletes nothing — the discarded merged state is archived too")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)
        CRM.unmerge_contacts(merge_id=gym_a)

        discarded = list(CRM._crm_archive_dir().glob(f"unmerged_{friend}_*.json"))
        assert len(discarded) == 1, discarded
        rec = json.loads(discarded[0].read_text())
        assert rec["id"] == friend, rec
        assert rec["record_type"] == "post_merge_discarded", rec
        assert rec["unmerged_away_from"] == gym_a, rec

        # The original archive files are retired, not removed.
        retired = list(CRM._crm_archive_dir().glob("reverted_*.json"))
        assert len(retired) == 2, [p.name for p in retired]


@check("a second unmerge of the same pair finds nothing to redo")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)
        assert CRM.unmerge_contacts(merge_id=gym_a).startswith("Unmerged:")
        assert CRM.unmerge_contacts(merge_id=gym_a).startswith("Error:")


@check("merge, unmerge, merge again — the second merge gets its own fresh snapshot")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)
        CRM.unmerge_contacts(merge_id=gym_a)
        _merge_approved(friend, gym_a)

        snaps = list(CRM._crm_archive_dir().glob(f"premerge_{gym_a}_*.json"))
        assert len(snaps) == 1, [p.name for p in snaps]
        assert CRM.unmerge_contacts(merge_id=gym_a).startswith("Unmerged:")


@check("a pre-merge snapshot is never followed as a merged_into redirect")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)

        # Searching for the survivor's own name must return him once, not twice —
        # the snapshot in the archive carries his name and his id.
        results = json.loads(CRM.search_contacts("Steven Okafor"))
        assert len(results) == 1, results
        assert results[0]["id"] == friend, results

        # And the survivor's id must still resolve to the live record, not a snapshot.
        assert json.loads(CRM.read_contact(contact_id=friend))["id"] == friend


@check("read_contact on the old id still resolves after a merge, and stops after unmerge")
def _():
    with _temp_persona_dir():
        friend, gym_a, _ = _three_stevens()
        _merge_approved(friend, gym_a)
        assert json.loads(CRM.read_contact(contact_id=gym_a))["id"] == friend

        CRM.unmerge_contacts(merge_id=gym_a)
        # Now it is its own record again — resolving to the other person would be a lie.
        assert json.loads(CRM.read_contact(contact_id=gym_a))["id"] == gym_a


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed

    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")

    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
