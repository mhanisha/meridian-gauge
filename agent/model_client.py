"""How the agent talks to a model.

The loop depends only on the ModelClient interface: one `chat(messages, tools)` method. The
model gateway (part 2) will provide this. Until it is ready, OpenAICompatibleClient reaches any
OpenAI-compatible host directly (vLLM, RunPod, OpenRouter, Groq, Hugging Face) so the agent can
be built and tried now. Swap it for the gateway without touching the loop.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, exactly as the model sent it


@dataclass
class ModelReply:
    message: dict  # the assistant message, ready to append to the conversation
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    model_served: str = ""


class ModelClient(Protocol):
    model_name: str

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


class OpenAICompatibleClient:
    """Temporary direct client. Replace with the model gateway once it is ready."""

    def __init__(self, model_name: str, base_url: str, api_key: str,
                 price_in_per_m: float = 0.0, price_out_per_m: float = 0.0,
                 temperature: float | None = None, request_timeout: float = 600):
        from openai import OpenAI  # imported here so tests do not need the package

        self.model_name = model_name
        self.price_in_per_m = price_in_per_m
        self.price_out_per_m = price_out_per_m
        self.temperature = temperature
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=request_timeout,
                              max_retries=3)

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        kwargs = {"model": self.model_name, "messages": messages, "tools": tools}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        calls = [ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or "")
                 for tc in (msg.tool_calls or [])]
        message: dict = {"role": "assistant", "content": msg.content or ""}
        if calls:
            message["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": c.arguments}} for c in calls]

        usage = resp.usage
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        cost = (tin * self.price_in_per_m + tout * self.price_out_per_m) / 1_000_000
        return ModelReply(message=message, tool_calls=calls, tokens_in=tin, tokens_out=tout,
                          cost_usd=cost, model_served=resp.model or "")


def message_to_json(message: dict) -> str:
    return json.dumps(message, ensure_ascii=False)
