# Project practices

## QC after design changes

The printed case is what matters; the tooling exists to serve it, not the
other way round. Keep verification proportional to the change.

- **Always**, after any change to `generate_case.py` or the STL parts: run
  `.venv/bin/python3 verify_case.py` (seconds). If it fails, fix the model
  before reporting the change as done, and mention the result in one line.
- **Only for big changes, or when the owner asks**: invoke the
  `ipod-case-reviewer` subagent (`.claude/agents/ipod-case-reviewer.md`) for
  an independent review, and mutation-test any new checks. A big change is
  one that alters how the parts fit together or carry load: the outer
  outline, the cavity, screw or nut positions and pockets, the frame, or a
  wall thickness. A local feature (a bevel, a cosmetic tweak) does not
  need it. When the review does run, relay its findings to the owner; do
  not silently absorb or drop them.
- The owner's test prints are the real validation. Prefer getting a change
  to the printer over further polishing the checks.

This applies to changes made *in this session and in future ones*.

## Verification tooling

- `verify_case.py` is the geometric check script (watertightness, wall
  thickness, screw clearances, mating-surface alignment across all three
  parts, assembly interference). It regenerates the parts in memory --
  `generate_case.py` does not need to be run first.
- `.venv/` (gitignored) holds `manifold3d`, `numpy` and `trimesh` for
  running both scripts. Create it with
  `python3 -m venv .venv && .venv/bin/pip install manifold3d numpy trimesh`
  if it is missing.
- `verify_case.py` is meant to evolve with the design: if a change adds a
  new failure mode (a new opening, a new pocket, a new minimum wall) that
  the script would not catch, add a check for it -- sized to the change,
  not an exhaustive one.
