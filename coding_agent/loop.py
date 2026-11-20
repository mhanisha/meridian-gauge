"""The agent loop: give a model a task and tools, and stop at finish or a limit.

The instructions, tools and limits are the same for every model. That is what makes the
comparison fair, so change them only by team agreement.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .model_client import ModelClient
from .sandbox import Sandbox
from .tools import TOOL_SPECS, finish_summary, run_tool, truncate

SYSTEM_PROMPT = (
    "You are working in a Python repository at /work/repo. Make the change the user describes. "
    "You can run commands, read and edit files, and run the tests. There is no internet. "
    "When you are done, call finish."
)
NUDGE = "Use a tool, or call finish."


@dataclass
class Limits:
    max_steps: int = 50
    max_minutes: float = 60.0
    max_cost_usd: float = 2.0
    command_timeout_seconds: int = 180
    max_tool_output_chars: int = 10_000

    @classmethod
    def from_config(cls, budgets: dict | None) -> "Limits":
        b = budgets or {}
        d = cls()
        return cls(
            max_steps=int(b.get("max_steps", d.max_steps)),
            max_minutes=float(b.get("max_minutes", d.max_minutes)),
            max_cost_usd=float(b.get("max_cost_usd", d.max_cost_usd)),
            command_timeout_seconds=int(b.get("command_timeout_seconds", d.command_timeout_seconds)),
            max_tool_output_chars=int(b.get("max_tool_output_chars", d.max_tool_output_chars)),
        )


@dataclass
class AttemptResult:
    ended: str  # finished | step_limit | time_limit | cost_cap | error
    steps: int
    minutes: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model_requested: str
    model_served: str
    messages: list[dict] = field(default_factory=list)
    summary: str = ""
    error: str = ""
    waited_minutes: float = 0.0  # time spent waiting out rate limits (included in `minutes`)

    def attempt_fields(self) -> dict:
        """The agent's share of attempt.json (the orchestrator adds task_id, host, gpu_hours)."""
        return {
            "model_requested": self.model_requested,
            "model_served": self.model_served,
            "ended": self.ended,
            "steps": self.steps,
            "minutes": round(self.minutes, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 6),
        }


def run_attempt(task_md: str, sandbox: Sandbox, client: ModelClient, limits: Limits | None = None,
                on_message: Callable[[dict], None] | None = None,
                clock: Callable[[], float] = time.monotonic) -> AttemptResult:
    """Run one attempt. `on_message` is called with every new message, so the caller can save
    the transcript as it goes and keep it even if the process crashes."""
    limits = limits or Limits()
    messages: list[dict] = []
    start = clock()
    steps = tokens_in = tokens_out = 0
    cost = 0.0
    served = ""

    def add(message: dict) -> None:
        messages.append(message)
        if on_message:
            on_message(message)

    def waited() -> float:
        """Seconds the client spent waiting out rate limits. They do not count towards the
        time limit, so a busy host does not cost the model its working time."""
        return float(getattr(client, "waited_seconds", 0) or 0)

    def out_of_time() -> bool:
        return clock() - start - waited() >= limits.max_minutes * 60

    def done(ended: str, summary: str = "", error: str = "") -> AttemptResult:
        return AttemptResult(ended=ended, steps=steps, minutes=(clock() - start) / 60,
                             tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
                             model_requested=client.model_name, model_served=served,
                             messages=messages, summary=summary, error=error,
                             waited_minutes=waited() / 60)

    add({"role": "system", "content": SYSTEM_PROMPT})
    add({"role": "user", "content": task_md})

    while True:
        # Check every limit before spending another model call.
        if steps >= limits.max_steps:
            return done("step_limit")
        if out_of_time():
            return done("time_limit")
        if cost >= limits.max_cost_usd:
            return done("cost_cap")

        try:
            reply = client.chat(messages, TOOL_SPECS)
        except Exception as e:  # the model or host failed; record it and stop
            return done("error", error=f"{type(e).__name__}: {e}")

        steps += 1
        tokens_in += reply.tokens_in
        tokens_out += reply.tokens_out
        cost += reply.cost_usd
        served = reply.model_served or served
        add(reply.message)

        if not reply.tool_calls:
            add({"role": "user", "content": NUDGE})
            continue

        for call in reply.tool_calls:
            if call.name == "finish":
                add({"role": "tool", "tool_call_id": call.id, "content": "Finished."})
                return done("finished", summary=finish_summary(call.arguments))
            if out_of_time():
                return done("time_limit")
            output = run_tool(sandbox, call.name, call.arguments, limits.command_timeout_seconds)
            add({"role": "tool", "tool_call_id": call.id,
                 "content": truncate(output, limits.max_tool_output_chars)})
