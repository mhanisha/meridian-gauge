"""How the agent reaches the sandbox.

The agent only needs three things from a sandbox: run a command, read a file, write a file.
Starting and deleting containers is the sandbox part's job (part 1); the agent attaches
to a container that is already running, with the repo copy at /work/repo.
"""
from __future__ import annotations

import posixpath
import subprocess
from dataclasses import dataclass
from typing import Protocol

REPO_ROOT = "/work/repo"


@dataclass
class CommandResult:
    exit_code: int
    output: str
    timed_out: bool = False


class Sandbox(Protocol):
    def run(self, command: str, timeout: int) -> CommandResult: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...


def safe_path(path: str) -> str:
    """Return a path relative to the repo, or raise ValueError if it points outside it.

    Accepts "xarray/core/x.py" and "/work/repo/xarray/core/x.py"; refuses anything that
    would leave the repo, such as "/etc/passwd" or "../secret".
    """
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        raise ValueError("path must be a non-empty string")
    path = path.strip()
    if path.startswith("/"):
        if path != REPO_ROOT and not path.startswith(REPO_ROOT + "/"):
            raise ValueError(f"path must be inside {REPO_ROOT}")
        path = path[len(REPO_ROOT):].lstrip("/") or "."
    norm = posixpath.normpath(path)
    if norm == ".." or norm.startswith("../"):
        raise ValueError(f"path must be inside {REPO_ROOT}")
    return norm


class DockerSandbox:
    """Talks to an already-running container through `docker exec`."""

    def __init__(self, container: str):
        self.container = container

    def run(self, command: str, timeout: int) -> CommandResult:
        # `timeout` inside the container stops the command itself; the outer timeout is a
        # safety net in case docker exec hangs.
        args = ["docker", "exec", self.container, "timeout", "--kill-after=5", str(timeout),
                "bash", "-lc", f"cd {REPO_ROOT} && {command}"]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, errors="replace",
                                  timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            return CommandResult(exit_code=124, output="", timed_out=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        return CommandResult(exit_code=proc.returncode, output=output,
                             timed_out=proc.returncode in (124, 137))

    def read_file(self, path: str) -> str:
        full = f"{REPO_ROOT}/{safe_path(path)}"
        proc = subprocess.run(["docker", "exec", self.container, "cat", "--", full],
                              capture_output=True, text=True, errors="replace", timeout=60)
        if proc.returncode != 0:
            raise FileNotFoundError(proc.stderr.strip() or f"cannot read {path}")
        return proc.stdout

    def write_file(self, path: str, content: str) -> None:
        full = f"{REPO_ROOT}/{safe_path(path)}"
        # The path is passed as an argument ($1), never pasted into the shell command.
        proc = subprocess.run(
            ["docker", "exec", "-i", self.container, "sh", "-c",
             'mkdir -p "$(dirname "$1")" && cat > "$1"', "sh", full],
            input=content, capture_output=True, text=True, errors="replace", timeout=60)
        if proc.returncode != 0:
            raise OSError(proc.stderr.strip() or f"cannot write {path}")
