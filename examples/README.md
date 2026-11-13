# Example files

One example of every file the parts pass to each other. Build and test your part against
these before the real pipeline exists. They describe xarray task `b3f5db3728`.

| File | Written by | Read by |
| --- | --- | --- |
| `candidates.jsonl` | task builder | task builder |
| `task.md` | task builder | coding agent |
| `task.meta.json` | task builder, sandbox | orchestrator, reporter |
| `answer_key.json` | sandbox (answer-key mode) | sandbox (grade mode) |
| `attempt.json` | orchestrator | reporter |
| `result.json` | sandbox (grade mode) | reporter |

The values are real (from xarray), except the made-up attempt numbers. Change a format only by team agreement, and update
the example in the same pull request.
