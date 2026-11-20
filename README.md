# Meridian Gauge

Tests whether open-weight AI models can do a team's real coding work as well as a commercial
assistant. It replays coding tasks that were already done with AI help in a repository, gives
each model the same task in a sealed sandbox, and grades the result with the tests written
alongside the original change.

The build guide (what each part does, step by step) is in the team's
[Meridian Gauge — Team Build Guide](https://claude.ai/artifact/1xNchZGSHAxETLbTxS13mB). Read it before writing code.

## Parts

Each part has its own folder. The first file in a new part's folder is `SPEC.md`, approved in
a pull request before any code is written (see the build guide).

| Folder | Part |
| --- | --- |
| `sandbox/` | Sandbox and test runner |
| `gateway/` | Model gateway |
| `coding_agent/` (exists) | Coding agent |
| `orchestrator/` (exists) | Orchestrator |
| `task_builder/` | Task builder agent (turns commits into fair tasks) |
| `reporter/` | Reporter |

Shared by everyone: `examples/` (the file formats parts pass to each other) and `tests/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then add your own API keys
cp config.example.yaml config.yaml
docker run --rm hello-world        # Docker must work
pytest                             # checks the example files load
```

Clone the repository under test next to this one: `git clone https://github.com/pydata/xarray.git`.

## How the parts connect

Parts never call each other. Each one reads files from the run folder and writes files back,
in the formats shown in `examples/`. Change those formats only by team agreement.

```text
runs/<run-id>/
  config.yaml
  candidates.jsonl                 task builder
  tasks/<task-id>/
    task.md, task.meta.json        task builder
    answer_key.json                sandbox (answer-key mode)
    attempts/<model>/
      patch.diff, transcript.jsonl coding agent
      attempt.json                 orchestrator
      result.json                  sandbox (grade mode)
  report/                          reporter
```

## Team rules

- One pull request per change, reviewed by someone from another area.
- Never commit API keys. They go in `.env`, which git ignores.
- Model-written code runs only inside the sandbox, never directly on a laptop.
- Practise on xarray commit `b3f5db3728` first: every model solved it.
