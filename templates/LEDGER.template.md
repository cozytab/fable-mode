# Ledger — <round name>

State machine: `- [ ]` open (blocks turn-end) · `- [x]` done AND verified ·
`- [~] ... -- deferred: reason` consciously out of this round.
A line `PAUSED: reason` anywhere suspends enforcement (for user-steered work
unrelated to this round) — the reason is required (bare `PAUSED` is ignored),
the model ceiling stays active; remove the line to resume. Evidence notes on
`- [x]` must be concrete (`evidence: ok` counts as missing).

Only mark `- [x]` after the acceptance command actually ran — the Close Guard
blocks turn-end for any `- [x]` without an evidence note (`-- evidence:` /
`verified:` / `证据:`):

- [ ] 1. <card> — acceptance: `<command>`
- [ ] 2. <card> — acceptance: `<command>`
- [x] 0. (example) scaffold -- evidence: `pytest -q` -> 12 passed
- [~] 9. (example) dark mode -- deferred: not this round
