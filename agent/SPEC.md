# Coding agent — spec

**Owner:** Keerthana · **Part:** 3 of 6 · **Status:** draft for review

## What it does

The coding agent is the thing Meridian Gauge measures. It gives one model one task, lets the
model work inside a sealed sandbox using five tools, and stops when the model says it is
finished or a limit is reached. It must behave identically for every model: same
instructions, same tools, same limits.

It does not start or delete sandboxes, save the code changes, or grade anything. The
orchestrator and the sandbox (part 1) do those.

## What it reads and writes

| | What | Format |
| --- | --- | --- |
| Reads | The task | `task.md` (see `examples/task.md`) |
| Reads | A running sandbox | A container started by the sandbox part, with the repo copy at `/work/repo` |
| Reads | A model to talk to | Anything with the model-client interface below (the gateway, once ready) |
| Reads | Limits | `budgets` in `config.yaml` |
| Writes | The full conversation | `transcript.jsonl`, one line per message, saved after every message so a crash still leaves it |
| Writes | How the attempt ended | the agent's fields of `attempt.json` (see below) |

Fields the agent fills in `attempt.json`: `model_requested`, `model_served`, `ended`,
`steps`, `minutes`, `tokens_in`, `tokens_out`, `cost_usd`. The orchestrator adds `task_id`,
`host` and `gpu_hours`.

`ended` is one of: `finished`, `step_limit`, `time_limit`, `cost_cap`, `error`.

## The steps

1. Start a conversation: the fixed instructions, then the task text.
2. Send the conversation and the tool descriptions to the model.
3. If the model asked for tools, run each one inside the sandbox and add its output to the
   conversation. If it asked for none, add one short nudge: "Use a tool, or call finish."
4. Repeat from step 2 until the model calls `finish`, or a limit is reached.
5. Return how it ended, the counts, and the conversation.

Limits are checked before every model call, so an attempt never starts a step it cannot
afford.

## Instructions the model gets (identical for every model)

> You are working in a Python repository at /work/repo. Make the change the user describes.
> You can run commands, read and edit files, and run the tests. There is no internet.
> When you are done, call finish.

## The five tools

| Tool | Inputs | What it does | Returns |
| --- | --- | --- | --- |
| `run` | `command` | Runs a shell command in `/work/repo` with a time limit | Exit code and output |
| `read` | `path` | Shows a file | The file's text |
| `write` | `path`, `content` | Creates or overwrites a file | "Written." |
| `replace` | `path`, `old`, `new` | Swaps text that appears exactly once | "Replaced.", or an error saying how many times it appears |
| `finish` | `summary` | Ends the attempt | — |

Rules:
- Every tool runs inside the sandbox. The model never runs anything itself.
- Paths must stay inside `/work/repo`. Absolute paths and `..` are refused.
- A tool error is returned to the model as text; it never crashes the loop.
- Tool output is cut to the last 10,000 characters, so a long test run cannot flood the
  conversation.

## Limits (from `config.yaml`, same for every model)

| Limit | Default |
| --- | --- |
| Steps (model calls) | 50 |
| Time | 60 minutes |
| Cost | $2.00 |
| One command | 180 seconds |
| Tool output kept | 10,000 characters |

## Model-client interface

Until Hanisha's gateway is ready, `agent/model_client.py` has a temporary client for any
OpenAI-compatible host. The agent only depends on one method, so the gateway can replace it
without changes to the loop:

`chat(messages, tools)` returns the assistant's message, its tool calls, tokens in and out,
cost, and the name of the model that actually answered.

## How it will be tested

- **Without a model or Docker:** a scripted stand-in model and an in-memory stand-in
  sandbox (`tests/test_agent.py`). These check that each limit ends the attempt with the
  right reason, that bad tool calls return an error, that long output is cut, that
  `replace` needs exactly one match, and that paths outside the repo are refused.
- **With Neetu's sandbox and a free model:** the agent works on `b3f5db3728` and the grader
  marks it solved.
- **Each limit on purpose:** steps set to 2, time to 1 minute, a tiny cost cap.
- **Two different models** on the same task, to check the loop works for both.

## Open questions

1. Does Neetu's sandbox give a container name we `docker exec` into? This spec assumes so.
2. Should a model that replies in plain text several times in a row be stopped early,
   rather than using up all its steps?
