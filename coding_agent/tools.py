"""The five tools the model can use, and how each one is run.

Every tool runs inside the sandbox. Errors are returned to the model as text, never raised,
so a bad tool call costs the model a step but never crashes the attempt.
"""
from __future__ import annotations

import json

from .sandbox import Sandbox, safe_path


def _spec(name: str, description: str, **params: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {p: {"type": "string", "description": d} for p, d in params.items()},
                "required": list(params),
            },
        },
    }


TOOL_SPECS = [
    _spec("run", "Run a shell command in the repository, for example to run tests.",
          command="The shell command to run."),
    _spec("read", "Show the contents of a file.",
          path="File path, relative to the repository root."),
    _spec("write", "Create a file or overwrite it completely.",
          path="File path, relative to the repository root.",
          content="The full new contents of the file."),
    _spec("replace", "Replace a piece of text that appears exactly once in a file.",
          path="File path, relative to the repository root.",
          old="The exact text to replace. It must appear exactly once.",
          new="The text to put in its place."),
    _spec("finish", "Call this when the change is complete.",
          summary="One or two sentences on what you changed."),
]

TOOL_NAMES = [t["function"]["name"] for t in TOOL_SPECS]


def truncate(text: str, max_chars: int) -> str:
    """Keep the last max_chars characters, which is where test failures usually are."""
    if len(text) <= max_chars:
        return text
    cut = len(text) - max_chars
    return f"[... {cut} characters cut ...]\n" + text[-max_chars:]


def _args(arguments: str, *required: str) -> dict:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"the tool arguments are not valid JSON ({e.msg})") from None
    if not isinstance(args, dict):
        raise ValueError("the tool arguments must be a JSON object")
    for name in required:
        if not isinstance(args.get(name), str):
            raise ValueError(f"missing or non-text argument '{name}'")
    return args


def run_tool(sandbox: Sandbox, name: str, arguments: str, command_timeout: int) -> str:
    """Run one tool call (other than finish) and return the text the model will see."""
    try:
        if name == "run":
            a = _args(arguments, "command")
            res = sandbox.run(a["command"], command_timeout)
            if res.timed_out:
                return f"Command stopped after {command_timeout} seconds.\n{res.output}"
            return f"exit code {res.exit_code}\n{res.output}"
        if name == "read":
            a = _args(arguments, "path")
            text = sandbox.read_file(safe_path(a["path"]))
            return text if text else "(empty file)"
        if name == "write":
            a = _args(arguments, "path", "content")
            sandbox.write_file(safe_path(a["path"]), a["content"])
            return "Written."
        if name == "replace":
            a = _args(arguments, "path", "old", "new")
            path = safe_path(a["path"])
            if not a["old"]:
                return "Error: 'old' must not be empty."
            text = sandbox.read_file(path)
            n = text.count(a["old"])
            if n != 1:
                return f"Error: that text appears {n} times in {path}; it must appear exactly once."
            sandbox.write_file(path, text.replace(a["old"], a["new"], 1))
            return "Replaced."
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(TOOL_NAMES)}."
    except Exception as e:  # any failure goes back to the model as text
        return f"Error: {e}"


def finish_summary(arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
        return str(args.get("summary", "")) if isinstance(args, dict) else ""
    except json.JSONDecodeError:
        return ""
