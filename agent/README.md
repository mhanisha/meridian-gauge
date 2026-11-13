# Coding agent (part 3)

**Owner:** Keerthana. The thing Meridian Gauge measures: one model, one task, five tools,
inside the sandbox. See [`SPEC.md`](SPEC.md) for what it does and why.

| File | What it holds |
| --- | --- |
| `loop.py` | The loop, the fixed instructions, and the limits |
| `tools.py` | The five tools (`run`, `read`, `write`, `replace`, `finish`) |
| `sandbox.py` | How the agent reaches a running container, and the inside-the-repo path check |
| `model_client.py` | The interface the loop needs, plus a temporary direct client until the gateway is ready |
| `__main__.py` | Run the agent on one task from the command line |

## Try it on one task

Needs a running sandbox container (part 1) and a model listed in `config.yaml`.

```bash
python -m agent --config config.yaml --model qwen3.8-27b \
    --task examples/task.md --container gauge-try-1 --out runs/try-1
```

It writes `runs/try-1/transcript.jsonl` (saved as it goes) and `runs/try-1/attempt.json`.
Saving the code changes as `patch.diff` and grading them are the orchestrator's and the
sandbox's jobs.

## Tests

`pytest tests/test_agent.py` runs without Docker or a model: a scripted stand-in model and an
in-memory stand-in sandbox check every limit and error path.
