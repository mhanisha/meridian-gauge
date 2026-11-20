"""Run the coding agent on one task, for trying it out before the orchestrator exists.

    python -m coding_agent --config config.yaml --model qwen3.8-27b \
        --task examples/task.md --container gauge-try-1 --out runs/try-1

The container must already be running (see the sandbox part) with the repo copy at /work/repo.
Writes transcript.jsonl (saved as it goes) and attempt.json to --out.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .loop import Limits, run_attempt
from .model_client import OpenAICompatibleClient, message_to_json
from .sandbox import DockerSandbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m coding_agent", description=__doc__.splitlines()[0])
    p.add_argument("--config", default="config.yaml", help="config file (default: config.yaml)")
    p.add_argument("--model", required=True, help="model name, as listed under models: in the config")
    p.add_argument("--task", required=True, help="path to task.md")
    p.add_argument("--container", required=True, help="name of the running sandbox container")
    p.add_argument("--out", required=True, help="folder for transcript.jsonl and attempt.json")
    a = p.parse_args(argv)

    import yaml  # only needed when running for real

    cfg = yaml.safe_load(Path(a.config).read_text())
    model_cfg = (cfg.get("models") or {}).get(a.model)
    if not model_cfg:
        p.error(f"model '{a.model}' is not listed under models: in {a.config}")
    key_env = model_cfg.get("api_key_env", "")
    api_key = os.environ.get(key_env, "") if key_env else "not-needed"
    if key_env and not api_key:
        p.error(f"environment variable {key_env} is not set (put it in .env)")

    client = OpenAICompatibleClient(
        model_name=a.model, base_url=model_cfg["base_url"], api_key=api_key,
        price_in_per_m=float(model_cfg.get("price_in_per_m", 0)),
        price_out_per_m=float(model_cfg.get("price_out_per_m", 0)),
        temperature=model_cfg.get("temperature"),
        max_retry_wait_seconds=float((cfg.get("budgets") or {}).get("max_retry_wait_seconds", 300)),
        on_retry=lambda e, wait: print(f"  {type(e).__name__}; waiting {wait:.0f}s and trying again",
                                       flush=True))
    limits = Limits.from_config(cfg.get("budgets"))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "transcript.jsonl", "w", encoding="utf-8") as transcript:
        def save(message: dict) -> None:
            transcript.write(message_to_json(message) + "\n")
            transcript.flush()

        result = run_attempt(Path(a.task).read_text(encoding="utf-8"),
                             DockerSandbox(a.container), client, limits, on_message=save)

    (out / "attempt.json").write_text(json.dumps(result.attempt_fields(), indent=2) + "\n")
    print(f"{a.model}: {result.ended} after {result.steps} steps, {result.minutes:.1f} min, "
          f"{result.tokens_in + result.tokens_out:,} tokens, ${result.cost_usd:.4f}"
          + (f", {result.waited_minutes:.1f} min of it waiting out rate limits"
             if result.waited_minutes else "")
          + (f" ({result.error})" if result.error else ""))
    return 0 if result.ended != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
