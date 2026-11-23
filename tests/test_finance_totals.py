#!/usr/bin/env python3
"""
tests/test_finance_totals.py — #13: Finance figures computed in code, and transactions merged
by code-assigned id (Stage 3 plan § 1.2 tests 1–12, Revision 2 S2, build-time amendments 3 and
5; archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).

Temporary persona tree; no model. Log files for past dates are written directly (write_log
refuses a date more than seven days out); today's merges go through the real write_log.

Run:  python tests/test_finance_totals.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from support.stage3_fixtures import (PERSONA, Script, coordinator_package, patched,  # noqa: E402
                                     pipeline, sandbox)

from core import orchestrator as ORC  # noqa: E402
from tools import finance_totals as FT  # noqa: E402
from tools.agent_config import write_agent_config  # noqa: E402
from tools.logger import read_log, write_log  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
TODAY = date.today()


def check(name):
    def deco(fn):
        try:
            with sandbox() as sb:
                fn(sb)
            RESULTS.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            import traceback
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-700:]}"))
        return fn
    return deco


def tx(desc, amount, cat, typ="expense", **kw):
    return {"description": desc, "amount": amount, "financial_category": cat, "type": typ, **kw}


def put_day(sb, d: date, txs: list[dict]) -> None:
    logs = sb["data"] / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{d.isoformat()}.json").write_text(json.dumps({"date": d.isoformat(),
                                                           "finance": {"transactions": txs}}))


def put_budget(sb, budget) -> None:
    cfg = sb["data"] / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "finance.json").write_text(json.dumps({"budget_structure": json.dumps(budget)
                                                  if not isinstance(budget, str) else budget}))


def today_txs() -> list[dict]:
    return (read_log().get("finance") or {}).get("transactions") or []


FOOD = {"period": "month", "groups": {"food": {"limit": 600, "categories": ["groceries", "dining"]}}}


# --- 1–9: the sums -----------------------------------------------------------------------

@check("1. exact cents: 0.1 + 0.2 style amounts, and 340 + 180 = 520")
def _(sb):
    put_day(sb, TODAY, [tx("a", 0.1, "other"), tx("b", 0.2, "other"), tx("g", 340, "groceries"),
                        tx("d", "180.00", "dining")])
    f = FT.period_figures(PERSONA, TODAY)
    assert f["ok"] and f["by_category"]["other"] == 30, f
    assert f["by_category"]["groceries"] + f["by_category"]["dining"] == 52000
    assert FT.money(f["total"]) == "520.30"


@check("2. groups: limit, spend and remaining from the member categories")
def _(sb):
    put_budget(sb, FOOD)
    put_day(sb, TODAY, [tx("g", 340, "groceries"), tx("d", 180, "dining")])
    text = FT.finance_figures_block(PERSONA)
    assert "food (groceries, dining): limit 600.00, spent 520.00, 80.00 remaining" in text, text


@check("3. period boundaries: the previous month's last day is out, the 1st is in; a week starts "
       "Monday")
def _(sb):
    wed = date(2026, 11, 18)                      # a Wednesday; Monday is the 16th
    put_day(sb, date(2026, 10, 31), [tx("old", 99, "dining")])
    put_day(sb, date(2026, 11, 1), [tx("new", 10, "dining")])
    put_day(sb, date(2026, 11, 15), [tx("sun", 7, "transport")])
    put_day(sb, date(2026, 11, 16), [tx("mon", 3, "transport")])
    f = FT.period_figures(PERSONA, wed)
    assert (f["start"], f["end"]) == ("2026-11-01", "2026-11-30"), f
    assert f["by_category"] == {"dining": 1000, "transport": 1000}, f
    put_budget(sb, {"period": "week", "categories": {"transport": 50}})
    f = FT.period_figures(PERSONA, wed)
    assert (f["period"], f["start"], f["end"]) == ("week", "2026-11-16", "2026-11-22"), f
    assert f["by_category"] == {"transport": 300} and f["days_gone"] == 3, f


@check("4. refunds subtract; income and a missing type are excluded and counted; removed "
       "entries are excluded")
def _(sb):
    put_day(sb, TODAY, [tx("shoes", 80, "clothing"), tx("shoes back", 30, "clothing", "refund"),
                        tx("salary", 2000, "other", "income"),
                        {"description": "?", "amount": 5, "financial_category": "other"},
                        tx("gone", 999, "clothing", removed=True)])
    f = FT.period_figures(PERSONA, TODAY)
    assert f["by_category"] == {"clothing": 5000}, f
    assert f["excluded"] == {"income": 1, "no type": 1}, f
    assert "Not counted in spending: 1 income, 1 no type." in FT.finance_figures_block(PERSONA)


@check("5. an unreadable log gives ok False, never 0")
def _(sb):
    logs = sb["data"] / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{TODAY.isoformat()}.json").write_text("{not json")
    f = FT.period_figures(PERSONA, TODAY)
    assert f["ok"] is False and "could not be read" in f["reason"], f
    text = FT.finance_figures_block(PERSONA)
    assert "UNKNOWN" in text and "0.00" not in text, text


@check("6. a non-conforming budget gives totals only and says so")
def _(sb):
    put_budget(sb, {"food_total_monthly_limit": 600, "categories_included": ["groceries",
                                                                             "dining_out"]})
    put_day(sb, TODAY, [tx("g", 340, "groceries")])
    text = FT.finance_figures_block(PERSONA)
    assert "not in the readable shape" in text and "Total spent 340.00" in text and \
        "Budget:" not in text, text


@check("7. a limit category with no spend, and an unbudgeted category, are both listed (names "
       "never reconciled)")
def _(sb):
    put_budget(sb, {"period": "month", "categories": {"dining_out": 200}})
    put_day(sb, TODAY, [tx("dinner", 45, "dining")])
    text = FT.finance_figures_block(PERSONA)
    assert "nothing logged under `dining_out` this period" in text, text
    assert "Logged under no budget: dining 45.00." in text, text


@check("8. first_seen thresholds: 10 days and twice is listed; first seen 30 days ago is not; "
       "once is not")
def _(sb):
    put_day(sb, TODAY - timedelta(days=10), [tx("Oat latte", 4, "dining")])
    put_day(sb, TODAY - timedelta(days=3), [tx("oat  LATTE", 4, "dining"), tx("Vinyl", 30, "entertainment")])
    put_day(sb, TODAY - timedelta(days=30), [tx("Bagel", 3, "groceries")])
    put_day(sb, TODAY - timedelta(days=2), [tx("bagel", 3, "groceries"), tx("Bagel", 3, "groceries")])
    got = {(x["key"], x["value"]): x["count"] for x in FT.first_seen(PERSONA, TODAY)}
    assert got.get(("description", "oat latte")) == 2, got
    assert ("description", "bagel") not in got and ("description", "vinyl") not in got, got


@check("9. the heading says 'sums of what was logged'; no 'right' or 'authoritative', and 'exact' "
       "only in the stated phrase")
def _(sb):
    put_day(sb, TODAY, [tx("g", 1, "groceries")])
    for text in (FT.finance_figures_block(PERSONA), FT.finance_figures_note(PERSONA)):
        low = text.lower()
        assert "sums of the 1 transaction logged this period" in low, text
        assert "authoritative" not in low and " right" not in low, text
        assert low.count("exact") == 1 and "exact arithmetic over what was logged" in low


# --- 10: the merge ---------------------------------------------------------------------------

@check("10a. a later write with only the new transaction keeps the earlier ones; two coffees in "
       "separate writes = 2")
def _(sb):
    write_log({"finance": {"transactions": [tx("groceries", 340, "groceries")]}})
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining")]}})
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining")]}})
    txs = today_txs()
    assert [t["description"] for t in txs] == ["groceries", "coffee", "coffee"], txs
    assert [t["id"] for t in txs] == [f"tx-{TODAY}-{n}" for n in (1, 2, 3)], txs
    assert all(t.get("logged_at") for t in txs)


@check("10b. a restatement carrying both stored ids = 2; with both ids plus an id-less coffee = 3")
def _(sb):
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining"), tx("bagel", 2, "dining")]}})
    stored = today_txs()
    write_log({"finance": {"transactions": stored}})
    assert len(today_txs()) == 2, today_txs()
    write_log({"finance": {"transactions": today_txs() + [tx("coffee", 3, "dining")]}})
    assert len(today_txs()) == 3, today_txs()


@check("10c. legacy file (no ids) — amendment 3: never a restatement; one stored coffee + a write "
       "of one coffee = 2, and every entry then has an id")
def _(sb):
    put_day(sb, TODAY, [tx("coffee", 3, "dining")])
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining")]}})
    txs = today_txs()
    assert len(txs) == 2 and all(t.get("id") for t in txs), txs
    put_day(sb, TODAY, [tx("coffee", 3, "dining"), tx("coffee", 3, "dining")])
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining"), tx("coffee", 3, "dining")]}})
    assert len(today_txs()) == 4, "legacy: id-less incoming entries are all new"


@check("10d. a write carrying only some of the day's ids is not a restatement: its id-less "
       "entries are new; two identical entries in one write give two")
def _(sb):
    write_log({"finance": {"transactions": [tx("coffee", 3, "dining"), tx("tea", 2, "dining")]}})
    first = today_txs()[0]
    write_log({"finance": {"transactions": [first, tx("tea", 2, "dining")]}})
    assert len(today_txs()) == 3, today_txs()
    write_log({"finance": {"transactions": [tx("gum", 1, "other"), tx("gum", 1, "other")]}})
    assert sum(1 for t in today_txs() if t["description"] == "gum") == 2


@check("10e. a correction by id replaces in place and the total moves by the difference; "
       "amendment 5: {id, amount} alone keeps the other fields")
def _(sb):
    write_log({"finance": {"transactions": [tx("dinner", 45, "dining"), tx("cab", 20, "transport")]}})
    before = FT.period_figures(PERSONA)["total"]
    tid = today_txs()[0]["id"]
    out = write_log({"finance": {"transactions": [{"id": tid, "amount": 52}]}})
    after = FT.period_figures(PERSONA)["total"]
    assert after - before == 700, (before, after)
    t = today_txs()[0]
    assert (t["id"], t["description"], t["financial_category"], t["type"]) == \
        (tid, "dinner", "dining", "expense") and t.get("corrected_at"), t
    assert f"Corrected: {tid}" in out and len(today_txs()) == 2


@check("10f. remove by id excludes the entry from totals and keeps it in the file; an unknown "
       "id is refused and the reply says so")
def _(sb):
    write_log({"finance": {"transactions": [tx("dinner", 45, "dining")]}})
    tid = today_txs()[0]["id"]
    out = write_log({"finance": {"transactions": [{"id": tid, "remove": True}]}})
    t = today_txs()[0]
    assert t["removed"] is True and t.get("removed_at") and f"Removed: {tid}" in out, (t, out)
    assert FT.period_figures(PERSONA)["total"] == 0
    out = write_log({"finance": {"transactions": [{"id": f"tx-{TODAY}-9", "amount": 1}]}})
    assert f"Not written: no transaction with id tx-{TODAY}-9" in out and len(today_txs()) == 1


@check("10g. an id-less same-description entry with a new amount is recorded as new and the reply "
       "names the existing id; the reply lists new ids")
def _(sb):
    out1 = write_log({"finance": {"transactions": [tx("dinner", 45, "dining")]}})
    assert f"Transactions recorded: tx-{TODAY}-1 (dinner, 45.00)." in out1, out1
    out = write_log({"finance": {"transactions": [tx("Dinner", 50, "dining")]}})
    assert len(today_txs()) == 2
    assert f"Recorded as new: 'Dinner' 50.00 (id tx-{TODAY}-2)" in out and \
        f'{{"id": "tx-{TODAY}-2", "replaces": "tx-{TODAY}-1"}}' in out, out


@check("10g'. FOLLOWING the hint gives one counted entry: a 3.50 coffee restated id-less is 7.00, "
       "the hinted write brings the day back to 3.50 (review item 1)")
def _(sb):
    write_log({"finance": {"transactions": [tx("Coffee", "3.50", "dining")]}})
    out = write_log({"finance": {"transactions": [tx("coffee", "3.50", "dining")]}})
    assert FT.period_figures(PERSONA)["total"] == 700
    import re as _re
    hinted = _re.search(r"write (\{.*?\}):", out).group(1)
    write_log({"finance": {"transactions": [json.loads(hinted)]}})
    assert FT.period_figures(PERSONA)["total"] == 350, today_txs()
    kept = [t for t in today_txs() if not t.get("removed")]
    gone = [t for t in today_txs() if t.get("removed")]
    assert len(kept) == 1 and len(gone) == 1 and gone[0]["replaced_by"] == kept[0]["id"], today_txs()


@check("10g''. a one-step correction: an id-less entry with \"replaces\" sets the old one aside "
       "(kept, not counted) and records the new; an unknown replaces target is refused")
def _(sb):
    write_log({"finance": {"transactions": [tx("Coffee", "3.50", "dining")]}})
    out = write_log({"finance": {"transactions": [
        tx("Coffee", "4.00", "dining", replaces=f"tx-{TODAY}-1")]}})
    assert FT.period_figures(PERSONA)["total"] == 400, today_txs()
    assert f"Replaced: tx-{TODAY}-1" in out and len(today_txs()) == 2, out
    out = write_log({"finance": {"transactions": [tx("tea", 2, "dining", replaces=f"tx-{TODAY}-9")]}})
    assert out.count("Not written") == 1 and len(today_txs()) == 2, out


@check("10i. an id from another day is refused with that day named, never 'write it without an id' "
       "(review item 4)")
def _(sb):
    write_log({"finance": {"transactions": [tx("dinner", 45, "dining")]}})
    other = (TODAY - timedelta(days=1)).isoformat()
    out = write_log({"finance": {"transactions": [{"id": f"tx-{other}-1", "amount": 50}]}})
    assert f"tx-{other}-1 belongs to {other}" in out and f"log_date: {other}" in out, out
    assert "without an id" not in out and len(today_txs()) == 1, out


@check("10j. figures run to the period's END (a later-dated log in the period counts) and stop at "
       "the month boundary (review item 5)")
def _(sb):
    day = date(2026, 11, 28)
    put_day(sb, date(2026, 11, 30), [tx("ahead", 12, "dining")])
    put_day(sb, date(2026, 12, 1), [tx("next month", 99, "dining")])
    f = FT.period_figures(PERSONA, day)
    assert f["by_category"] == {"dining": 1200} and f["days_gone"] == 28, f
    f = FT.period_figures(PERSONA, date(2026, 12, 1))
    assert f["by_category"] == {"dining": 9900}, f


@check("10k. a negative expense reduces spend (signed sum, review item 8)")
def _(sb):
    put_day(sb, TODAY, [tx("shoes", 80, "clothing"), tx("adjustment", -20, "clothing")])
    assert FT.period_figures(PERSONA, TODAY)["by_category"] == {"clothing": 6000}


@check("8'. first_seen is empty for a new user (no history before the window) and after a gap of "
       "more than 90 days (review item 6)")
def _(sb):
    put_day(sb, TODAY - timedelta(days=5), [tx("Oat latte", 4, "dining")])
    put_day(sb, TODAY - timedelta(days=2), [tx("Oat latte", 4, "dining")])
    assert FT.first_seen(PERSONA, TODAY) == []
    assert "First seen" not in FT.finance_figures_block(PERSONA)
    put_day(sb, TODAY - timedelta(days=120), [tx("Bagel", 3, "groceries")])
    assert FT.first_seen(PERSONA, TODAY) == [], "a >90-day gap is not history"
    put_day(sb, TODAY - timedelta(days=40), [tx("Bagel", 3, "groceries")])
    assert "oat latte" in [x["value"] for x in FT.first_seen(PERSONA, TODAY)], \
        "with history inside the lookback, the new habit is listed"


@check("10h. legacy id-less entries get ids, and a second write leaves those ids unchanged; a "
       "write with no finance.transactions key leaves the list untouched")
def _(sb):
    put_day(sb, TODAY, [tx("a", 1, "other"), tx("b", 2, "other")])
    write_log({"finance": {"transactions": [tx("c", 3, "other")]}})
    ids = [t["id"] for t in today_txs()]
    write_log({"finance": {"transactions": [tx("d", 4, "other")]}})
    assert [t["id"] for t in today_txs()][:3] == ids, today_txs()
    snap = today_txs()
    write_log({"mood": "ok", "finance": {"stress_signal": False}})
    assert today_txs() == snap


# --- 11, 12 ----------------------------------------------------------------------------------

@check("11. write_agent_config: refuses a non-conforming budget with the shape, accepts a good one, "
       "leaves other pairs untouched")
def _(sb):
    bad = write_agent_config("finance", "budget_structure",
                             json.dumps({"food_total_monthly_limit": 600}))
    assert bad.startswith("Error: budget_structure not saved") and '"period"' in bad, bad
    assert not (sb["data"] / "config" / "finance.json").exists()
    ok = write_agent_config("finance", "budget_structure", json.dumps(FOOD))
    assert ok.startswith("Saved"), ok
    assert write_agent_config("finance", "savings_target", "not json at all").startswith("Saved")
    assert write_agent_config("learning_growth", "budget_structure", "{}").startswith("Saved")


@check("12. every path: Finance gets the before-block in its user message and the note on its "
       "result — pipeline dispatch, run_subagent, run_session")
def _(sb):
    put_budget(sb, FOOD)
    put_day(sb, TODAY, [tx("g", 340, "groceries"), tx("d", 180, "dining")])
    reply = "FINANCIAL STATE: on budget"
    spec = [{"agent": "finance", "directive": "How is the food budget?"}]
    s = Script({"coordinator": coordinator_package(spec), "finance": reply}, synth_reply="ok")
    with pipeline(s):
        ORC.run_pipeline_session("how's my food budget", persona=PERSONA, provider="openai")
        assert s.last("finance").startswith("FINANCE FIGURES (from code — sums of the 2"), \
            s.last("finance")[:200]
        assert "FINANCE FIGURES (from code, after this turn's writes" in s.last("synthesizer")
        from tools.subagent import run_subagent
        out = run_subagent("finance", "food budget?")
        assert out.startswith(reply) and "after this turn's writes" in out, out
        out = ORC.run_session("finance", "monthly review", persona=PERSONA, provider="openai")
        assert out.startswith(reply) and "80.00 remaining" in out, out
        assert "80.00 remaining" in s.last("finance")


def main() -> int:
    passed = 0
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"\n     {detail}" if detail else ""))
        passed += ok
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
