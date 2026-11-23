"""
tools/finance_totals.py — Finance's figures, summed by code from what is logged (#13).

Stage 3 plan § 1.2 (archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).
"On budget" and "overspent" used to rest on the Finance model re-adding the transactions it read
back with `read_log` — arithmetic a model does less reliably than code, and the hard-fail
criterion for this domain. Code now sums `finance.transactions` over the budget period in
integer cents and hands Finance the sums, before it runs (`finance_figures_block`, at the head
of its user message) and after its writes (`finance_figures_note`, appended to its result), on
every path that runs Finance (core/orchestrator._run_single_agent).

THE FIGURES ARE SUMS OF WHAT WAS LOGGED, and say so. A purchase never logged is not in them; a
transaction logged twice is counted twice. They are labelled "exact arithmetic over what was
logged", never "right" or "authoritative".

Read-only over the bound persona's daily logs (tools/logger._logs_dir) and Finance's agent
config. An unreadable log is UNKNOWN (`ok: False`), never a total of zero. No function here
raises into the turn.

`budget_structure` has one readable shape (ruling D = (a)), checked when it is written
(tools/agent_config.write_agent_config, via `budget_shape_error`):

    {"period": "month" | "week",
     "categories": {"<financial_category>": <limit>},
     "groups": {"<name>": {"limit": <n>, "categories": ["<financial_category>", ...]}}}

Category names are compared exactly (casefolded, spaces collapsed) and never reconciled: a
budget under `dining_out` and spending under `dining` are reported as a limit with nothing
logged and an unbudgeted category, which is the point.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

logger = logging.getLogger(__name__)

BUDGET_KEY = "budget_structure"
BUDGET_SHAPE = ('{"period": "month"|"week", "categories": {"<financial category>": <limit>}, '
                '"groups": {"<name>": {"limit": <n>, "categories": [...]}}}')
FIRST_SEEN_LOOKBACK_DAYS = 90
FIRST_SEEN_WINDOW_DAYS = 14
FIRST_SEEN_MIN_COUNT = 2


# ---------------------------------------------------------------------------
# Small exact helpers
# ---------------------------------------------------------------------------

def amount_cents(value) -> int | None:
    """An amount as integer cents (half-up), or None when it is not a number. Accepts numbers
    and strings like "45", "45.00", "$1,234.50"; a float goes through its shortest repr, so
    0.1 + 0.2 style artefacts never reach the sum."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        text = str(value).strip().replace(",", "")
        text = re.sub(r"^[^\d\-+.]+", "", text)
        d = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite():
        return None
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    c = abs(int(cents))
    return f"{sign}{c // 100}.{c % 100:02d}"


def norm(text) -> str:
    return " ".join(str(text or "").split()).casefold()


# ---------------------------------------------------------------------------
# The budget shape
# ---------------------------------------------------------------------------

def _parse_budget(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise ValueError("not a JSON object")


def budget_shape_error(value) -> str | None:
    """None when `value` is a readable budget_structure, else what is wrong with it."""
    try:
        data = _parse_budget(value)
    except (ValueError, TypeError):
        return "it is not valid JSON"
    if not isinstance(data, dict):
        return "it is not a JSON object"
    extra = sorted(set(data) - {"period", "categories", "groups"})
    if extra:
        return f"unknown key(s) {', '.join(extra)}"
    if data.get("period") not in ("month", "week"):
        return '"period" must be "month" or "week"'
    cats, groups = data.get("categories", {}), data.get("groups", {})
    if not cats and not groups:
        return 'it sets no limit: give "categories", "groups" or both'
    if not isinstance(cats, dict):
        return '"categories" must map a financial category to a limit'
    for name, limit in cats.items():
        if not str(name).strip() or amount_cents(limit) is None or amount_cents(limit) < 0:
            return f'the limit for category "{name}" is not a non-negative number'
    if not isinstance(groups, dict):
        return '"groups" must map a group name to {"limit": n, "categories": [...]}'
    for name, g in groups.items():
        if not isinstance(g, dict) or set(g) - {"limit", "categories"}:
            return f'group "{name}" must be {{"limit": n, "categories": [...]}}'
        if amount_cents(g.get("limit")) is None or amount_cents(g.get("limit")) < 0:
            return f'group "{name}" has no non-negative "limit"'
        members = g.get("categories")
        if not isinstance(members, list) or not members or not all(
                isinstance(m, str) and m.strip() for m in members):
            return f'group "{name}" needs a non-empty "categories" list of names'
    return None


def _read_budget():
    """(budget dict | None, state): state is "none", "readable" or "unreadable"."""
    from core.persona import persona_data_dir
    path = persona_data_dir() / "config" / "finance.json"
    if not path.exists():
        return None, "none"
    try:
        stored = json.loads(path.read_text())
    except (OSError, ValueError):
        return None, "unreadable"
    value = stored.get(BUDGET_KEY) if isinstance(stored, dict) else None
    if value in (None, ""):
        return None, "none"
    if budget_shape_error(value) is not None:
        return None, "unreadable"
    return _parse_budget(value), "readable"


# ---------------------------------------------------------------------------
# Reading the period
# ---------------------------------------------------------------------------

def _period_bounds(day: date, kind: str) -> tuple[date, date]:
    if kind == "week":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    start = day.replace(day=1)
    nxt = (start.replace(year=start.year + 1, month=1) if start.month == 12
           else start.replace(month=start.month + 1))
    return start, nxt - timedelta(days=1)


class _Unreadable(Exception):
    pass


def _day_transactions(d: date) -> list[dict] | None:
    """The day's finance.transactions (None when the day has no log or no finance block).
    Raises _Unreadable for a file that exists and cannot be read."""
    from tools.logger import _logs_dir
    path = _logs_dir() / f"{d.isoformat()}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise _Unreadable(f"the log for {d.isoformat()} could not be read") from exc
    if not isinstance(data, dict):
        raise _Unreadable(f"the log for {d.isoformat()} is not a log")
    fin = data.get("finance")
    if not isinstance(fin, dict) or "transactions" not in fin:
        return None
    txs = fin.get("transactions")
    if not isinstance(txs, list):
        raise _Unreadable(f"the transactions for {d.isoformat()} are not a list")
    return [t for t in txs if isinstance(t, dict)]


def period_figures(persona: str | None = None, day: date | None = None) -> dict:
    """The budget period's sums, from the persona's logs. See the module docstring."""
    from core.persona import persona_scope, resolve_persona
    out: dict = {"ok": False}
    try:
        with persona_scope(resolve_persona(persona)):
            day = day or date.today()
            budget, budget_state = _read_budget()
            kind = (budget or {}).get("period") or "month"
            start, end = _period_bounds(day, kind)
            by_cat: dict[str, int] = {}
            excluded: dict[str, int] = {}
            n_tx, days_logged, unreadable_amounts = 0, 0, 0
            # To the period's END, not today: a write dated later in the period (a log_date a
            # few days ahead) belongs to it, and the after-write figures must include it.
            d = start
            while d <= end:
                txs = _day_transactions(d)
                if txs is not None:
                    days_logged += 1
                for t in txs or []:
                    if t.get("removed"):
                        continue
                    typ = norm(t.get("type"))
                    if typ not in ("expense", "refund"):
                        key = typ or "no type"
                        excluded[key] = excluded.get(key, 0) + 1
                        continue
                    cents = amount_cents(t.get("amount"))
                    if cents is None:
                        unreadable_amounts += 1
                        continue
                    cat = norm(t.get("financial_category")) or "uncategorised"
                    # Signed as written: an expense of -20 reduces spend. A refund subtracts its
                    # size whichever sign it was logged with.
                    by_cat[cat] = by_cat.get(cat, 0) + (cents if typ == "expense"
                                                        else -abs(cents))
                    n_tx += 1
                d += timedelta(days=1)
            out.update(ok=True, period=kind, start=start.isoformat(), end=end.isoformat(),
                       day=day.isoformat(), days_gone=(day - start).days + 1,
                       days_total=(end - start).days + 1, transactions=n_tx,
                       days_logged=days_logged, excluded=excluded,
                       unreadable_amounts=unreadable_amounts, by_category=by_cat,
                       total=sum(by_cat.values()), budget_state=budget_state,
                       budget=_budget_lines(budget, by_cat) if budget else None)
            return out
    except _Unreadable as exc:
        out["reason"] = str(exc)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("[finance] figures unavailable: %s", exc)
        out["reason"] = "the finance logs could not be read"
        return out


def _budget_lines(budget: dict, by_cat: dict[str, int]) -> dict:
    limits: list[dict] = []
    named: set[str] = set()
    for cat, limit in (budget.get("categories") or {}).items():
        key = norm(cat)
        named.add(key)
        limits.append({"name": key, "categories": [key], "limit": amount_cents(limit),
                       "spent": by_cat.get(key, 0), "logged": key in by_cat})
    for name, g in (budget.get("groups") or {}).items():
        members = [norm(m) for m in g.get("categories") or []]
        named.update(members)
        limits.append({"name": str(name), "categories": members,
                       "limit": amount_cents(g.get("limit")),
                       "spent": sum(by_cat.get(m, 0) for m in members),
                       "logged": any(m in by_cat for m in members)})
    unbudgeted = {c: v for c, v in by_cat.items() if c not in named}
    return {"limits": limits, "unbudgeted": unbudgeted}


def first_seen(persona: str | None = None, day: date | None = None) -> list[dict]:
    """NEW_HABIT_EXPENSE evidence: over a 90-day lookback, the expense keys — description
    (casefolded, spaces collapsed) and, separately, financial_category — first seen within the
    last 14 days and seen at least twice in them. [] on any failure."""
    from core.persona import persona_scope, resolve_persona
    try:
        with persona_scope(resolve_persona(persona)):
            day = day or date.today()
            window_start = day - timedelta(days=FIRST_SEEN_WINDOW_DAYS - 1)
            seen: dict[tuple[str, str], dict] = {}
            history_before_window = False
            for back in range(FIRST_SEEN_LOOKBACK_DAYS - 1, -1, -1):
                d = day - timedelta(days=back)
                try:
                    txs = _day_transactions(d) or []
                except _Unreadable:
                    continue
                if txs and d < window_start:
                    history_before_window = True
                for t in txs:
                    if t.get("removed") or norm(t.get("type")) != "expense":
                        continue
                    for kind, value in (("description", norm(t.get("description"))),
                                        ("category", norm(t.get("financial_category")))):
                        if not value:
                            continue
                        rec = seen.setdefault((kind, value), {"first": d, "recent": 0})
                        if d >= window_start:
                            rec["recent"] += 1
            # "First seen" needs something to have been unseen against: with no finance logged
            # in the lookback before the window (a new user, or a gap of more than 90 days)
            # everything is "new", so nothing is reported (review item 6).
            if not history_before_window:
                return []
            return [{"key": kind, "value": value, "first_seen": rec["first"].isoformat(),
                     "count": rec["recent"]}
                    for (kind, value), rec in sorted(seen.items(), key=lambda kv: kv[1]["first"])
                    if rec["first"] >= window_start and rec["recent"] >= FIRST_SEEN_MIN_COUNT]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[finance] first_seen unavailable: %s", exc)
        return []


# ---------------------------------------------------------------------------
# The text Finance is handed
# ---------------------------------------------------------------------------

def _figures_text(persona: str | None, when: str) -> str:
    fig = period_figures(persona)
    if not fig.get("ok"):
        return (f"FINANCE FIGURES (from code{when}): {fig.get('reason') or 'the logs could not be read'}"
                " — this period's sums are UNKNOWN. Do not state any total as zero or as on "
                "budget; say the record could not be read.")
    if not fig["days_logged"] and fig["budget_state"] == "none":
        return ""
    n = fig["transactions"]
    pct = round(100 * fig["days_gone"] / fig["days_total"])
    lines = [f"FINANCE FIGURES (from code{when} — sums of the {n} transaction"
             f"{'' if n == 1 else 's'} logged this period; exact arithmetic over what was "
             f"logged, and a purchase never logged is not in them):",
             f"Period: {fig['period']} {fig['start']} to {fig['end']} ({fig['days_gone']} of "
             f"{fig['days_total']} days gone, {pct}%); finance logged on {fig['days_logged']} "
             f"day{'' if fig['days_logged'] == 1 else 's'}."]
    if fig["by_category"]:
        cats = "; ".join(f"{c} {money(v)}" for c, v in sorted(fig["by_category"].items()))
        lines.append(f"Spent by category: {cats}. Total spent {money(fig['total'])}.")
    else:
        lines.append("Nothing spent is logged this period.")
    skipped = [f"{v} {k}" for k, v in sorted(fig["excluded"].items())]
    if fig["unreadable_amounts"]:
        skipped.append(f"{fig['unreadable_amounts']} with an amount that is not a number")
    if skipped:
        lines.append(f"Not counted in spending: {', '.join(skipped)}.")
    if fig["budget_state"] == "unreadable":
        lines.append("The budget on file is not in the readable shape, so only totals are "
                     "given; rewrite it in the shape the budget_structure key takes.")
    elif fig["budget"]:
        lines.append("Budget:")
        for b in fig["budget"]["limits"]:
            label = b["name"] if b["categories"] == [b["name"]] else (
                f"{b['name']} ({', '.join(b['categories'])})")
            if not b["logged"]:
                lines.append(f"- {label}: limit {money(b['limit'])} — nothing logged under "
                             f"{' or '.join(f'`{c}`' for c in b['categories'])} this period.")
                continue
            left = b["limit"] - b["spent"]
            state = f"{money(left)} remaining" if left >= 0 else f"{money(-left)} over"
            lines.append(f"- {label}: limit {money(b['limit'])}, spent {money(b['spent'])}, "
                         f"{state}; {pct}% of the period gone.")
        if fig["budget"]["unbudgeted"]:
            un = "; ".join(f"{c} {money(v)}" for c, v in sorted(fig["budget"]["unbudgeted"].items()))
            lines.append(f"Logged under no budget: {un}.")
    new = first_seen(persona)
    if new:
        lines.append("First seen in the last 14 days: " + "; ".join(
            f"{'“' + x['value'] + '”' if x['key'] == 'description' else 'category `' + x['value'] + '`'}"
            f" first on {x['first_seen']}, {x['count']} times" for x in new) + ".")
    lines.append("Use these sums rather than re-adding transactions by hand.")
    return "\n".join(lines)


def finance_figures_block(persona: str | None = None) -> str:
    """The figures before this turn's writes — the head of Finance's user message. "" when there
    are no finance logs this period and no budget; "" plus a warning on any failure."""
    try:
        return _figures_text(persona, "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[finance] figures block failed: %s", exc)
        return ""


def finance_figures_note(persona: str | None = None) -> str:
    """The figures after this turn's writes — appended to Finance's result."""
    try:
        return _figures_text(persona, ", after this turn's writes")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[finance] figures note failed: %s", exc)
        return ""
