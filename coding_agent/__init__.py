"""Coding agent (part 3): one model, one task, five tools, inside the sandbox."""
from .loop import NUDGE, SYSTEM_PROMPT, AttemptResult, Limits, run_attempt
from .model_client import ModelClient, ModelReply, OpenAICompatibleClient, ToolCall
from .sandbox import CommandResult, DockerSandbox, Sandbox, safe_path
from .tools import TOOL_NAMES, TOOL_SPECS

__all__ = [
    "AttemptResult", "CommandResult", "DockerSandbox", "Limits", "ModelClient", "ModelReply",
    "NUDGE", "OpenAICompatibleClient", "SYSTEM_PROMPT", "Sandbox", "TOOL_NAMES", "TOOL_SPECS",
    "ToolCall", "run_attempt", "safe_path",
]
