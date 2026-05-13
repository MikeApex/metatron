# Development Persona: Samuel Pepys
*Source: The Diary of Samuel Pepys (1660–1669)*
*Use: Testing the tool against a richly ordinary life — domestic, professional, social, sensual, and financially anxious.*

---

## Who He Is

Samuel Pepys, 27. Clerk of the Acts to the Navy Board, London, 1660. Recently risen from modest origins through family connections and his own considerable competence. Married to Elisabeth, 20. No children yet. Lives in a Navy Office house on Seething Lane. Income improving but never quite feels secure.

He is curious about everything: music, theatre, science, food, clothes, books, the mechanics of government. He is vain, self-aware about his vanity, and diligent despite it. He records everything — the great events of his age (the Plague, the Fire, the Restoration) alongside what he had for dinner and whether he was unkind to his wife.

---

## Prime Directive (terminal values)

- **Advancement:** Rise in the world — financially and socially. Not for its own sake but because competence without recognition feels incomplete.
- **Pleasure:** Life is for living. Music, theatre, good company, good wine, good food. He is not ascetic and does not pretend to be.
- **Domestic order:** A well-run household, a marriage with warmth in it, accounts that balance.
- **Intellectual life:** Read widely, understand how things work, keep learning.
- **Integrity in his work:** Despite his flaws, he genuinely cares about doing his job well. The Navy matters.

---

## Mission (current life chapter)

This is the chapter of establishment. He is building the foundation — career position, financial base, social standing, marriage — from which everything else will come. He is also documenting it, though he does not know why that feels so necessary.

---

## Goals (illustrative — 90-day horizon)

```yaml
quarterly:
  - id: q1
    title: Bring Navy accounts into order
    private_why: Fear of exposure; also genuine professional pride
    shareable_what: Audit and reconcile Navy Board expense records
    status: active

  - id: q2
    title: Learn to play the flageolet
    private_why: Music is the deepest pleasure he knows; this is for himself alone
    shareable_what: Practice flageolet 30 minutes daily
    status: active

  - id: q3
    title: Build savings to £300
    private_why: Poverty haunts him; £300 feels like safety
    shareable_what: Reduce discretionary spending; log all income and outgoings
    status: active

weekly:
  - id: w1
    title: Finish the quarterly accounts for the Comptroller
    parent_goal: q1
    status: active

  - id: w2
    title: Attend two theatre performances
    parent_goal: q2
    status: active

daily:
  - id: d1
    title: Write up yesterday's diary entry
    context: morning, before the day begins
    essential: true
    status: active
```

---

## Energy & Day Structure

- **Morning:** Sharp. Best thinking before 9am. Does accounts, correspondence, diary.
- **Midday:** Social — meetings at the office, coffee houses, colleagues. Energy for politics and persuasion.
- **Afternoon:** Variable. Tends toward pleasure after 3pm — theatre, music, visiting friends.
- **Evening:** Domestic. Supper, music at home, reading. Sometimes stays late at the office if under pressure.

Sleeps badly when the accounts are off or when he has quarrelled with Elisabeth.

---

## Known Patterns & Quirks

- Records everything. Loves data about himself even before that concept exists.
- Prone to avoidance when something is genuinely difficult (a hard letter to write, an overdue reckoning).
- Needs external accountability — tells people about goals because it commits him.
- Buys books compulsively; reads them less reliably.
- His relationship with Elisabeth is loving and volatile. Guilt is a regular presence.
- Health anxiety: eyes are deteriorating (he will eventually go blind). Overwork is a recurring issue.

---

## Testing Notes

Use Pepys to test:
- **Competing pleasures vs. duties** — the system must hold both without moralizing
- **Financial anxiety** as a real constraint, not just a metric
- **Domestic life as a first-class concern** alongside professional life
- **Short-term pleasure-seeking** in tension with longer-term goals
- **The director's tone when goals are genuinely neglected** vs. legitimately deferred
