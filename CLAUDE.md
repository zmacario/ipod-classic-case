# Project practices

## QC after every design change

After any change to `generate_case.py` or the STL parts made in response to
a request from the project owner, invoke the `ipod-case-reviewer` subagent
(`.claude/agents/ipod-case-reviewer.md`) before reporting the change as
done. It re-verifies that face, frame and rear still fit together correctly
(via `verify_case.py`) and separately judges whether the design still keeps
the iPod secure and easy to handle. Relay its findings to the owner; do not
silently absorb or drop them.

This applies to changes made *in this session and in future ones* -- it is
not a one-off request tied to whatever change prompted writing this file.

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
  the script would not catch, extend it rather than leaving the gap for
  the next change to fall into.
