# Coding agent — instructions

These are the instructions, tools, rules and limits every model gets. They must be identical
for every model, so change them only by team agreement, and update `loop.py` and `tools.py` in
the same pull request.

## Instructions

Sent first, word for word:

> You are working in a Python repository at /work/repo. Make the change the user describes.
> You can run commands, read and edit files, and run the tests. There is no internet.
> When you are done, call finish.

Then the task text (`task.md`), as the user's message.

## Tools

| Tool | Inputs | What it does | Returns |
| --- | --- | --- | --- |
| `run` | `command` | Runs a shell command in `/work/repo` | Exit code and output |
| `read` | `path` | Shows a file | The file's text |
| `write` | `path`, `content` | Creates or overwrites a file | "Written." |
| `replace` | `path`, `old`, `new` | Swaps text that appears exactly once | "Replaced.", or an error saying how many times it appears |
| `finish` | `summary` | Ends the attempt | — |

## Rules

- Every tool runs inside the sandbox. The model never runs anything itself.
- Paths must stay inside `/work/repo`. Paths outside it, and `..`, are refused.
- A tool error goes back to the model as text; it does not end the attempt.
- Tool output is cut to its last 10,000 characters.
- If the model replies without using a tool, it is told: "Use a tool, or call finish."

## Limits

The attempt stops at the first limit reached. Limits are checked before every model call.

| Limit | Default |
| --- | --- |
| Steps (model calls) | 50 |
| Time | 60 minutes |
| Cost | $2.00 |
| One command | 180 seconds |
| Tool output kept | 10,000 characters |
