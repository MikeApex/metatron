"""
tests/test_contact_dedup_gate.py — the near-match confirmation gate on write_contact.

[DB-0815-07]. Until 2026-08-19 a near-match on create was *evidence*: the record was
created either way and the agent decided what to do about it. Live that day the agent
decided two ways four minutes apart — turn 1 it surfaced the existing Steven and
offered to merge, turn 2 it announced "Stephen with a 'ph' is added as a separate
contact" and created the duplicate the item exists to prevent.

Neither of the other two actors can decide it. The SIMILARITY SCORE cannot:
Stephen/Steven scores 0.77 and is one person, Dave Bennett/Dan Bennett scores 0.87 and
is two, Anna/Hannah scores 0.80 and is two — no threshold separates them, which is
pinned below so nobody re-proposes one. The AGENT cannot, per the two turns above.
So the user is asked, out of band, with the model not in the consent path.

PRODUCTION NOTE — this gate is expected to become unnecessary. It exists because
today's model on today's tier does not reliably ask. When a model does, the right move
is to delete it and return to evidence-not-verdict, which is the lighter design. Re-run
this suite against whatever model is current before assuming the friction is still
earned. See the same note in tools/crm.py beside the gate.

Standalone runner (no pytest dependency), matching tests/test_crm_dedup_guards.py.

Usage:
    python tests/test_contact_dedup_gate.py

Exits 0 if every test passes, 1 otherwise.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


def _run() -> None:
    # An isolated persona tree, so no real CRM is touched and the suite is repeatable.
    tmp = tempfile.mkdtemp(prefix="dedup_gate_")
    os.environ["METATRON_PERSONA"] = "test_confirm"

    import core.persona as PERSONA
    real_dir = PERSONA.persona_data_dir

    def fake_dir(persona=None):
        p = Path(tmp) / "persona"
        p.mkdir(parents=True, exist_ok=True)
        return p

    PERSONA.persona_data_dir = fake_dir
    import tools.crm as CRM
    import tools.confirm as CF
    CRM.persona_data_dir = fake_dir
    CF.persona_data_dir = fake_dir

    def contacts_on_disk() -> list:
        f = fake_dir() / "crm" / "contacts.json"
        return json.load(open(f)) if f.exists() else []

    # --- the score cannot separate same-person from different-person -------------
    sim = CRM._name_similarity
    check("Stephen/Steven (same person) scores BELOW Dave/Dan Bennett (different people)",
          sim("Stephen", "Steven") < sim("Dave Bennett", "Dan Bennett"),
          f"{sim('Stephen','Steven'):.2f} vs {sim('Dave Bennett','Dan Bennett'):.2f} — "
          "no threshold can separate them, so do not propose one")
    check("Anna/Hannah (different people) outscores Stephen/Steven (same person)",
          sim("Anna", "Hannah") > sim("Stephen", "Steven"),
          f"{sim('Anna','Hannah'):.2f} vs {sim('Stephen','Steven'):.2f}")

    # --- the gate ----------------------------------------------------------------
    r1 = CRM.write_contact(name="Steven Ashworth", how_met="gym")
    check("a create with no near match is ungated", "PENDING" not in r1, r1[:80])
    check("  and it saved", len(contacts_on_disk()) == 1, str(len(contacts_on_disk())))

    r2 = CRM.write_contact(name="Stephen Ashworth", how_met="gym")
    gated = "PENDING_CONFIRMATION" in r2
    check("a create that near-matches is GATED", gated, r2[:120])
    check("  and NOTHING was saved — this is the whole point",
          len(contacts_on_disk()) == 1, f"{len(contacts_on_disk())} contacts on disk")

    if not gated:
        return
    payload = json.loads(r2)
    token = payload["confirm_token"]
    check("  the description names the existing contact, so the user can answer it",
          "Steven Ashworth" in payload["description"], payload["description"][:120])

    # --- the model is not in the consent path ------------------------------------
    r3 = CRM.write_contact(name="Stephen Ashworth", how_met="gym", confirm_token=token)
    check("replaying the token WITHOUT a user tap is refused",
          "not saved" in r3 and "not approved" in r3.lower(), r3[:100])
    check("  and still nothing was saved", len(contacts_on_disk()) == 1)

    # --- approve out of band, server executes -------------------------------------
    CF.approve(token)
    res = CF.execute(token)
    check("after the user approves, the server carries it out",
          res.get("status") == "executed", str(res)[:120])
    check("  and now it is saved", len(contacts_on_disk()) == 2,
          str([c["name"] for c in contacts_on_disk()]))

    check("the approval is single use",
          "not saved" in CRM.write_contact(name="Stephen Ashworth", how_met="gym",
                                           confirm_token=token))

    # --- the fingerprint binds the arguments ---------------------------------------
    r5 = CRM.write_contact(name="Stephanie Ashworth", how_met="gym")
    tok2 = json.loads(r5)["confirm_token"]
    CF.approve(tok2)
    r6 = CRM.write_contact(name="Stephanie Ashworth", how_met="pub", confirm_token=tok2)
    check("an approval cannot be spent on different arguments",
          "details changed" in r6.lower(), r6[:110])

    # --- enriching an existing record is not gated -----------------------------------
    first = contacts_on_disk()[0]
    r7 = CRM.write_contact(name=first["name"], contact_id=first["id"], occupation="architect")
    check("an UPDATE by contact_id is never gated, even on a near-matching name",
          "PENDING" not in r7, r7[:80])

    r7b = CRM.write_contact(name=first["name"], contact_id=first["id"],
                            employer="Foster + Partners",
                            contact_info={"phone": "07911 123456"})
    check("adding facts to a correctly identified person stays ungated",
          "PENDING" not in r7b, r7b[:80])

    # --- THE UPDATE GATE (2026-08-26) ------------------------------------------------
    # Live on 2026-08-22, asked to "add Stephen Ashworth", the model decided Stephen was
    # the existing Steven, called write_contact with HIS id, and renamed a real friend's
    # record — twice, with no prompt, because only creation was gated. What is checked
    # here is that changing WHO a record is now asks, while enriching it does not.
    target = contacts_on_disk()[0]
    before_name = target["name"]
    r8 = CRM.write_contact(name="Stephen Ashworth", contact_id=target["id"],
                           last_name="Ashworth")
    check("renaming an existing contact returns PENDING_CONFIRMATION",
          "PENDING" in r8, r8[:110])
    # Read from the decoded description, not the JSON envelope: json.dumps escapes the
    # arrow to \u2192, so a substring check against the raw payload silently fails.
    _desc8 = json.loads(r8)["description"]
    check("the description names the person and shows current → proposed",
          before_name in _desc8 and "Stephen Ashworth" in _desc8 and "→" in _desc8,
          _desc8[:160])
    check("nothing is written to the record while the rename is pending",
          contacts_on_disk()[0]["name"] == before_name,
          contacts_on_disk()[0]["name"])

    # The fingerprint binds the id, so consent for one person's rename is not consent
    # for another's — the whole failure was the model choosing the wrong record.
    tok3 = json.loads(r8)["confirm_token"]
    CF.approve(tok3)
    other = contacts_on_disk()[1]
    r9 = CRM.write_contact(name="Stephen Ashworth", contact_id=other["id"],
                           last_name="Ashworth", confirm_token=tok3)
    check("an approved rename cannot be spent on a different contact",
          "details changed" in r9.lower(), r9[:110])

    r10 = CRM.write_contact(name="Stephen Ashworth", contact_id=target["id"],
                            last_name="Ashworth", confirm_token=tok3)
    check("the approved rename completes on the record it was granted for",
          "PENDING" not in r10 and contacts_on_disk()[0]["name"] == "Stephen Ashworth",
          r10[:110])

    # A bulk import phone-matches a record whose stored name differs; that is an
    # ordinary import outcome, not a model renaming someone, and 200 of them would be
    # 200 blocking ten-minute confirmations. tools/contacts_import.py passes _bulk on
    # both branches for exactly this reason.
    r11 = CRM.write_contact(name="Stephen J Ashworth", contact_id=target["id"],
                            _bulk=True)
    check("_bulk exempts the update gate, as it does the creation gate",
          "PENDING" not in r11, r11[:80])

    PERSONA.persona_data_dir = real_dir


def main() -> int:
    _run()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
