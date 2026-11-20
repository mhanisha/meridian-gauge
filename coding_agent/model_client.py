"""How the agent talks to a model.

The loop depends only on the ModelClient interface: one `chat(messages, tools)` method. The
model gateway (part 2) will provide this. Until it is ready, OpenAICompatibleClient reaches any
OpenAI-compatible host directly (vLLM, RunPod, OpenRouter, Groq, Hugging Face) so the agent can
be built and tried now. Swap it for the gateway without touching the loop.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")

# Errors worth waiting out: rate limits, busy or failing hosts, timeouts, dropped connections.
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}
RETRY_ERROR_NAMES = {"APIConnectionError", "APITimeoutError", "EmptyReply"}


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


class EmptyReply(Exception):
    """The host answered but sent no reply (some hosts do this when overloaded)."""


def is_daily_quota(error: Exception) -> bool:
    """A daily allowance is used up (OpenRouter: "free-models-per-day"). Waiting minutes will
    not help; it only resets the next day."""
    text = str(error).lower()
    return "per-day" in text or "per day" in text or "daily limit" in text


def is_retryable(error: Exception) -> bool:
    if is_daily_quota(error):
        return False
    return (getattr(error, "status_code", None) in RETRY_STATUS
            or type(error).__name__ in RETRY_ERROR_NAMES)


def wait_before_retry(error: Exception, retry: int) -> float:
    """Seconds to wait before retry number `retry` (1, 2, ...): what the host asks for in its
    Retry-After header if it says, otherwise 5, 10, 20, 40, then 60 seconds; never over 60."""
    response = getattr(error, "response", None)
    try:
        asked = float(response.headers.get("retry-after"))
    except (AttributeError, TypeError, ValueError):
        asked = None
    wait = asked if asked is not None and asked >= 0 else 5 * 2 ** (retry - 1)
    return min(wait, 60.0)


def call_with_retries(fn: Callable[[], T], max_wait_seconds: float = 300,
                      sleep: Callable[[float], None] = time.sleep,
                      on_retry: Callable[[Exception, float], None] | None = None) -> T:
    """Call fn(); on a rate limit or other temporary host error, wait and try again, until the
    total waiting would pass max_wait_seconds. Then, or on any other error, raise it."""
    waited = 0.0
    retry = 0
    while True:
        try:
            return fn()
        except Exception as e:
            retry += 1
            wait = wait_before_retry(e, retry)
            if not is_retryable(e) or waited + wait > max_wait_seconds:
                raise
            if on_retry:
                on_retry(e, wait)
            sleep(wait)
            waited += wait


class ModelClient(Protocol):
    model_name: str

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


class OpenAICompatibleClient:
    """Temporary direct client. Replace with the model gateway once it is ready."""

    def __init__(self, model_name: str, base_url: str, api_key: str,
                 price_in_per_m: float = 0.0, price_out_per_m: float = 0.0,
                 temperature: float | None = None, request_timeout: float = 600,
                 max_retry_wait_seconds: float = 300,
                 on_retry: Callable[[Exception, float], None] | None = None):
        from openai import OpenAI  # imported here so tests do not need the package

        self.model_name = model_name
        self.price_in_per_m = price_in_per_m
        self.price_out_per_m = price_out_per_m
        self.temperature = temperature
        self.max_retry_wait_seconds = max_retry_wait_seconds
        self.on_retry = on_retry
        self.waited_seconds = 0.0  # total time spent waiting out rate limits; not the model's time
        # Retries are handled by call_with_retries, which waits longer than the library would.
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=request_timeout,
                              max_retries=0)

    def chat(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        kwargs = {"model": self.model_name, "messages": messages, "tools": tools}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        def ask():
            r = self._client.chat.completions.create(**kwargs)
            if not r.choices:
                raise EmptyReply("the host sent no reply")
            return r

        def note_wait(error: Exception, wait: float) -> None:
            self.waited_seconds += wait
            if self.on_retry:
                self.on_retry(error, wait)

        resp = call_with_retries(ask, self.max_retry_wait_seconds, on_retry=note_wait)
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
