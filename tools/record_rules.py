"""
tools/record_rules.py — the one home of rules every record writer carries.

A rule that applies to every tool that writes the user's record lives here, ONCE, and each
writer's schema appends it to the parameter that holds the content. The schema is the one
text every agent holding the tool reads at the moment it writes, so the rule needs no copy in
any agent file (One Home Per Rule Class; precedent: the stakes rule in open_task's schema,
2026-11-22).

Imports nothing, so every writer module can import it without a cycle.

Read by: tools/diarist.py (write_journal, write_archive), tools/logger.py (write_log),
tools/wisdom.py (write_wisdom), tools/data_objects.py (write_data_object, amend_data_object).
"""

# Mike, 2026-11-22: a record has to read true in ten years. "Last year" or "here" is true only
# on the day it was said; written down as-is it silently becomes wrong. Found live: a frog-log
# entry stored "caught last year", and its correction stored "two years ago". The first wording
# of the place example ("'here' → where the user was") was copied into an entry word for word
# (re-check, 2026-11-22) — an example must show a real value, never a description of one.
RELATIVE_REFERENCES = (
    "RECORD WHAT A RELATIVE REFERENCE MEANT, NEVER THE WORDS THAT POINT AT IT. Resolve it "
    "against when it was said, or against the time the user was talking about if they gave "
    "one: a time as a date or a year ('last year' → the year before; 'yesterday' → that "
    "date), a place by its name ('here', said in Greenwich → Greenwich; never a phrase such "
    "as 'where the user was' in its place), "
    "a comparison as the value ('same as last time' → that value). Keep the user's own words "
    "beside it. If what it points at is not known, keep the phrase as said — never guess."
)
