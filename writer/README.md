# Task writer (guide step 6)

**Owner:** Zayna.

Writes `task.md` (everything the model is told) and `task.meta.json` for each candidate,
and flags descriptions that are too thin to be fair.

Rules: use the best source (PR description, issue, original prompt, release note, commit
title, in that order); never include test names, test code or solution code.

Done when:
- [ ] `task.md` and a clarity flag exist for all 29 xarray tasks
- [ ] an automatic check confirms no `task.md` contains a hidden test's name
- [ ] the flags roughly match the 11 tasks the xarray report flagged
