"""Checks the shared example files exist and have the agreed fields."""
import json
from pathlib import Path

EX = Path(__file__).resolve().parent.parent / "examples"

REQUIRED = {
    "task.meta.json": {"task_id", "repo", "commit", "parent", "ai_tool",
                       "text_source", "clarity", "status", "drop_reason"},
    "answer_key.json": {"task_id", "test_patch", "hidden_tests", "existing_tests_to_check"},
    "attempt.json": {"task_id", "model_requested", "model_served", "host", "ended",
                     "steps", "minutes", "tokens_in", "tokens_out", "cost_usd", "gpu_hours"},
    "result.json": {"task_id", "model", "hidden_tests", "existing_tests_broken",
                    "runtime_errors", "solved_strict", "solved_wording_ignored"},
}

def test_json_examples_have_required_fields():
    for name, fields in REQUIRED.items():
        data = json.loads((EX / name).read_text())
        missing = fields - data.keys()
        assert not missing, f"{name} is missing {sorted(missing)}"

def test_candidates_is_one_json_object_per_line():
    for line in (EX / "candidates.jsonl").read_text().splitlines():
        row = json.loads(line)
        assert {"commit", "parent", "ai_tool", "test_files"} <= row.keys()

def test_task_md_has_the_template_sections():
    text = (EX / "task.md").read_text()
    for heading in ("## What to change", "## Where", "## Details"):
        assert heading in text
