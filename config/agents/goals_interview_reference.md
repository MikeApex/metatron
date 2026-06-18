# Goals Interview — Reference Material
*Supporting reference for `config/agents/goals_interviewer.md`. Not loaded at runtime — consulted during development and schema updates.*

---

## Phase 3 Domain List

All life domains for the domain sweep. Walk through any not yet covered. "No" answers are as useful as "yes" — they reveal what the user is consciously or unconsciously deprioritizing.

- Health and fitness
- Sleep and rest
- Nutrition and diet
- Mental and emotional wellbeing
- Romantic relationship / partnership
- Family (parents, children, siblings)
- Friendships and social life
- Career and vocation
- Finances and economic security
- Creative and artistic pursuits
- Learning and intellectual life
- Spiritual, philosophical, or meaning
- Home and environment
- Travel and adventure
- Community and civic life
- Recreation and hobbies
- Personal identity and self-concept

---

## Output Schema

Treat these as minimum fields. Include as much context as the interview warrants. Future sessions depend on rich, specific detail — a sparse record loses everything that was said.

### goals.yaml entry

```yaml
- id: goal_001
  shareable_what: "The concrete goal as stated"
  private_why: "The personal motivation as stated"
  domain: health          # one of the Phase 3 domains above
  timeline: "3 months"    # user's stated or inferred timeline
  essential: true         # survived trade-off forcing in Phase 5
  themes:                 # underlying motivations observed — to be developed in future interviews
    - "autonomy"
    - "recognition"
  open_questions:         # threads to follow up in dedicated future interviews
    - "Is this about the thing itself or what it represents? See doughnut shop note."
  retrospective_fit: ""   # how this compares to past goals that generated lasting satisfaction
  health_constraints: ""  # any Phase 1 health/limitation factors that affect this goal
  notes: ""               # anything else observed during the interview worth preserving
```

### mission.md

```markdown
# Mission

[1–3 sentences: current life chapter and direction.]

## Notes and Open Threads
[Observations from the interview that didn't fit cleanly into goals — patterns noticed,
tensions not yet resolved, things the user said that seemed important but unexplored.
These are context for the next conversation, not finished conclusions.]
```

### prime_directive.md

```markdown
# Prime Directive

[1–2 sentences: loose first draft of terminal values. What makes life feel worth living.]

*First draft — sharpens through use and future interviews.*

## Notes and Open Threads
[What was said that points toward deeper values. Tensions between stated values.
Things that seemed like they mattered more than the user acknowledged.
Anything worth returning to.]
```

---

## Phase 8 Write-back Notes

**Prototype / testing only.** Do not expose Phase 8 in production. Users should not see structured output — it breaks the conversational frame and exposes process that belongs to the tool, not the user.

- For prototype runs: output full draft YAML and Markdown inline for review and correction. Write files once confirmed using `write_goals` and `write_config`.
- For production: confirm each element conversationally, write files silently.
- Output should be as detailed as the session warrants. The schema above describes minimums, not limits.
