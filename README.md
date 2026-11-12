# Meridian Gauge

Tests whether open-weight AI models can do a team's real coding work as well as a commercial
assistant. It replays coding tasks that were already done with AI help in a repository, gives
each model the same task in a sealed sandbox, and grades the result with the tests written
alongside the original change.

The build guide (what each part does, step by step) is in the team's
[Meridian Gauge — Team Build Guide](https://claude.ai/artifact/1xNchZGSHAxETLbTxS13mB). Read it before writing code.

## Parts and owners

| Folder | Part | Owner | Guide step |
| --- | --- | --- | --- |
| `sandbox/` | Sandbox and test runner | Neetu (container), Keerthana (test logic) | 1 |
| `gateway/` | Model gateway | Neetu | 2 |
| `agent/` | Coding agent | Neetu | 3 |
| `orchestrator/` | Orchestrator | Keerthana (tech lead) | 4 |
| `finder/` | Task finder | Hanisha | 5 |
| `writer/` | Task writer | Zayna | 6 |
| `reporter/` | Reporter | Varsha, with Keerthana | 7 |
| `examples/` | Example files every part reads and writes | Everyone | — |
| `tests/` | Our own tests for the parts above | Everyone | — |

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
  candidates.jsonl                 finder/
  tasks/<task-id>/
    task.md, task.meta.json        writer/
    answer_key.json                sandbox/ (answer-key mode)
    attempts/<model>/
      patch.diff, transcript.jsonl agent/
      attempt.json                 orchestrator/
      result.json                  sandbox/ (grade mode)
  report/                          reporter/
```

## Team rules

- One pull request per change, reviewed by someone from another area.
- Never commit API keys. They go in `.env`, which git ignores.
- Model-written code runs only inside the sandbox, never directly on a laptop.
- Practise on xarray commit `b3f5db3728` first: every model solved it.
