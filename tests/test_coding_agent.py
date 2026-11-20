"""Tests for the coding agent. No Docker and no model needed: a scripted stand-in model and an
in-memory stand-in sandbox. Nothing here runs model-written code on this machine."""
import json
import subprocess

import pytest

from coding_agent import (NUDGE, SYSTEM_PROMPT, TOOL_NAMES, CommandResult, DockerSandbox, Limits,
                   ModelReply, ToolCall, run_attempt, safe_path)
from coding_agent.tools import run_tool, truncate


# ---------- stand-ins ----------

class FakeSandbox:
    def __init__(self, files=None, run_output="ok", exit_code=0, timed_out=False):
        self.files = dict(files or {})
        self.run_output, self.exit_code, self.timed_out = run_output, exit_code, timed_out
        self.commands = []

    def run(self, command, timeout):
        self.commands.append((command, timeout))
        return CommandResult(self.exit_code, self.run_output, self.timed_out)

    def read_file(self, path):
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]

    def write_file(self, path, content):
        self.files[path] = content


def call(name, n=0, **args):
    return ToolCall(id=f"call_{n}_{name}", name=name, arguments=json.dumps(args))


def reply(*calls, text="", cost=0.0, tin=100, tout=10, served="test-model"):
    msg = {"role": "assistant", "content": text}
    if calls:
        msg["tool_calls"] = [{"id": c.id, "type": "function",
                              "function": {"name": c.name, "arguments": c.arguments}} for c in calls]
    return ModelReply(message=msg, tool_calls=list(calls), tokens_in=tin, tokens_out=tout,
                      cost_usd=cost, model_served=served)


class ScriptedModel:
    """Returns the given replies in order; repeats the last one forever."""
    model_name = "test-model"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.seen = []

    def chat(self, messages, tools):
        self.seen.append((list(messages), tools))
        r = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        if isinstance(r, Exception):
            raise r
        return r


class FakeClock:
    def __init__(self, step_seconds=0.0):
        self.t, self.step = 0.0, step_seconds

    def __call__(self):
        now = self.t
        self.t += self.step
        return now


# ---------- the loop ----------

def test_finish_ends_the_attempt():
    model = ScriptedModel(reply(call("finish", summary="done")))
    r = run_attempt("Fix it.", FakeSandbox(), model)
    assert r.ended == "finished" and r.steps == 1 and r.summary == "done"
    assert r.messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert r.messages[1] == {"role": "user", "content": "Fix it."}


def test_same_instructions_and_tools_every_time():
    model = ScriptedModel(reply(call("finish")))
    run_attempt("A", FakeSandbox(), model)
    messages, tools = model.seen[0]
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert [t["function"]["name"] for t in tools] == ["run", "read", "write", "replace", "finish"]
    assert TOOL_NAMES == ["run", "read", "write", "replace", "finish"]


def test_tool_output_goes_back_to_the_model():
    sb = FakeSandbox(run_output="3 passed")
    model = ScriptedModel(reply(call("run", 1, command="pytest -q")), reply(call("finish", 2)))
    r = run_attempt("t", sb, model)
    assert r.ended == "finished" and r.steps == 2
    assert sb.commands == [("pytest -q", 180)]
    tool_msgs = [m for m in r.messages if m["role"] == "tool"]
    assert tool_msgs[0] == {"role": "tool", "tool_call_id": "call_1_run",
                            "content": "exit code 0\n3 passed"}


def test_step_limit():
    model = ScriptedModel(reply(call("read", path="a.py")))
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model, Limits(max_steps=2))
    assert r.ended == "step_limit" and r.steps == 2 and model.calls == 2


def test_time_limit():
    # every clock reading moves 20 minutes on, so the 60-minute limit is hit after a few steps
    model = ScriptedModel(reply(call("read", path="a.py")))
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model, Limits(max_minutes=60),
                    clock=FakeClock(step_seconds=20 * 60))
    assert r.ended == "time_limit"
    assert model.calls < 5


def test_cost_cap_stops_before_the_next_call():
    model = ScriptedModel(reply(call("read", path="a.py"), cost=1.5))
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model, Limits(max_cost_usd=2.0))
    assert r.ended == "cost_cap" and r.steps == 2 and r.cost_usd == pytest.approx(3.0)


def test_free_models_never_hit_the_cost_cap():
    model = ScriptedModel(reply(call("read", path="a.py"), cost=0.0))
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model, Limits(max_steps=5, max_cost_usd=2.0))
    assert r.ended == "step_limit"


def test_plain_text_reply_gets_a_nudge():
    model = ScriptedModel(reply(text="I think we should..."), reply(call("finish")))
    r = run_attempt("t", FakeSandbox(), model)
    assert r.ended == "finished" and r.steps == 2
    assert {"role": "user", "content": NUDGE} in r.messages


def test_model_error_ends_with_error():
    model = ScriptedModel(TimeoutError("host did not answer"))
    r = run_attempt("t", FakeSandbox(), model)
    assert r.ended == "error" and "host did not answer" in r.error and r.steps == 0


def test_counts_tokens_and_records_served_model():
    model = ScriptedModel(reply(call("read", path="a.py"), tin=1000, tout=50, served="m-v1"),
                          reply(call("finish"), tin=2000, tout=20, served="m-v1"))
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model)
    assert (r.tokens_in, r.tokens_out, r.model_served) == (3000, 70, "m-v1")


def test_attempt_fields_match_the_shared_format():
    r = run_attempt("t", FakeSandbox(), ScriptedModel(reply(call("finish"))))
    example = json.loads(open("examples/attempt.json").read())
    assert set(r.attempt_fields()) <= set(example)
    assert set(example) - set(r.attempt_fields()) == {"task_id", "host", "gpu_hours"}


def test_transcript_is_saved_as_it_goes():
    saved = []
    run_attempt("t", FakeSandbox(), ScriptedModel(reply(call("finish"))), on_message=saved.append)
    assert [m["role"] for m in saved] == ["system", "user", "assistant", "tool"]


def test_long_tool_output_is_cut_to_the_end():
    sb = FakeSandbox(run_output="x" * 50 + "FAILED test_foo")
    model = ScriptedModel(reply(call("run", command="pytest")), reply(call("finish")))
    r = run_attempt("t", sb, model, Limits(max_tool_output_chars=20))
    out = [m for m in r.messages if m["role"] == "tool"][0]["content"]
    assert out.endswith("FAILED test_foo") and "characters cut" in out


def test_finish_after_other_tools_runs_them_first():
    sb = FakeSandbox({"a.py": "old"})
    model = ScriptedModel(reply(call("replace", 1, path="a.py", old="old", new="new"),
                                call("finish", 2)))
    r = run_attempt("t", sb, model)
    assert r.ended == "finished" and sb.files["a.py"] == "new"


# ---------- the tools ----------

def test_bad_json_returns_an_error_not_a_crash():
    out = run_tool(FakeSandbox(), "run", "{not json", 180)
    assert out.startswith("Error:") and "JSON" in out


def test_missing_argument_returns_an_error():
    assert run_tool(FakeSandbox(), "read", "{}", 180).startswith("Error: missing")


def test_unknown_tool_returns_an_error():
    out = run_tool(FakeSandbox(), "delete_everything", "{}", 180)
    assert out.startswith("Error: unknown tool")


def test_run_reports_a_timeout():
    out = run_tool(FakeSandbox(run_output="partial", timed_out=True), "run",
                   json.dumps({"command": "sleep 999"}), 5)
    assert out.startswith("Command stopped after 5 seconds.")


def test_read_missing_file_returns_an_error():
    assert run_tool(FakeSandbox(), "read", json.dumps({"path": "nope.py"}), 180).startswith("Error:")


def test_write_then_read():
    sb = FakeSandbox()
    assert run_tool(sb, "write", json.dumps({"path": "pkg/new.py", "content": "x = 1\n"}), 180) == "Written."
    assert run_tool(sb, "read", json.dumps({"path": "pkg/new.py"}), 180) == "x = 1\n"


@pytest.mark.parametrize("text, expected", [
    ("a = 1\n", "Error: that text appears 0 times"),
    ("old\nold\n", "Error: that text appears 2 times"),
])
def test_replace_needs_exactly_one_match(text, expected):
    sb = FakeSandbox({"f.py": text})
    out = run_tool(sb, "replace", json.dumps({"path": "f.py", "old": "old", "new": "new"}), 180)
    assert out.startswith(expected) and sb.files["f.py"] == text


def test_replace_with_one_match_changes_the_file():
    sb = FakeSandbox({"f.py": "a = old\n"})
    out = run_tool(sb, "replace", json.dumps({"path": "f.py", "old": "old", "new": "new"}), 180)
    assert out == "Replaced." and sb.files["f.py"] == "a = new\n"


@pytest.mark.parametrize("bad", ["/etc/passwd", "../secret", "a/../../b", "", "/work/repository/x"])
def test_paths_outside_the_repo_are_refused(bad):
    with pytest.raises(ValueError):
        safe_path(bad)
    assert run_tool(FakeSandbox(), "read", json.dumps({"path": bad}), 180).startswith("Error:")


@pytest.mark.parametrize("good, expected", [
    ("xarray/core/x.py", "xarray/core/x.py"),
    ("/work/repo/xarray/core/x.py", "xarray/core/x.py"),
    ("./setup.cfg", "setup.cfg"),
])
def test_paths_inside_the_repo_are_allowed(good, expected):
    assert safe_path(good) == expected


def test_truncate_keeps_short_text():
    assert truncate("abc", 10) == "abc"


# ---------- the Docker connector (commands checked, nothing run) ----------

def test_docker_sandbox_commands(monkeypatch):
    seen = []

    def fake_run(args, **kwargs):
        seen.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="out", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sb = DockerSandbox("gauge-try-1")

    res = sb.run("pytest -q", 180)
    args, kwargs = seen[-1]
    assert args[:6] == ["docker", "exec", "gauge-try-1", "timeout", "--kill-after=5", "180"]
    assert args[-1] == "cd /work/repo && pytest -q" and res.exit_code == 0

    sb.write_file("pkg/a b.py", "x")
    args, kwargs = seen[-1]
    assert args[-1] == "/work/repo/pkg/a b.py"     # path passed as an argument, not in the script
    assert "a b.py" not in args[-3] and kwargs["input"] == "x"

    with pytest.raises(ValueError):
        sb.read_file("/etc/passwd")


# ---------- the temporary model client (canned reply, no network) ----------

def test_openai_client_parses_a_reply(monkeypatch):
    openai = pytest.importorskip("openai")
    from openai.types.chat import ChatCompletion
    from coding_agent import OpenAICompatibleClient

    canned = ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "qwen3.8-27b",
        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function",
                            "function": {"name": "read", "arguments": "{\"path\": \"a.py\"}"}}]}}],
        "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000, "total_tokens": 1_500_000},
    })
    client = OpenAICompatibleClient("qwen3.8-27b", "http://localhost:1/v1", "k",
                                    price_in_per_m=2.0, price_out_per_m=6.0, temperature=0.6)
    sent = {}

    def fake_create(**kwargs):
        sent.update(kwargs)
        return canned

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
    r = client.chat([{"role": "user", "content": "hi"}], [])
    assert sent["temperature"] == 0.6 and sent["model"] == "qwen3.8-27b"
    assert [(c.name, c.arguments) for c in r.tool_calls] == [("read", "{\"path\": \"a.py\"}")]
    assert r.message["tool_calls"][0]["function"]["name"] == "read" and r.message["content"] == ""
    assert (r.tokens_in, r.tokens_out, r.model_served) == (1_000_000, 500_000, "qwen3.8-27b")
    assert r.cost_usd == pytest.approx(2.0 + 3.0)


# ---------- the command line (stand-in model and sandbox) ----------

def test_command_line_writes_transcript_and_attempt(tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    import coding_agent.__main__ as cli

    (tmp_path / "config.yaml").write_text(
        "budgets:\n  max_steps: 7\n"
        "models:\n  m1:\n    base_url: http://x/v1\n    api_key_env: TEST_KEY\n")
    (tmp_path / "task.md").write_text("Fix it.")
    monkeypatch.setenv("TEST_KEY", "k")
    built = {}

    def fake_client(**kwargs):
        built.update(kwargs)
        model = ScriptedModel(reply(call("finish", summary="ok")))
        model.model_name = kwargs["model_name"]
        return model

    monkeypatch.setattr(cli, "OpenAICompatibleClient", fake_client)
    monkeypatch.setattr(cli, "DockerSandbox", lambda name: FakeSandbox())
    out = tmp_path / "out"
    code = cli.main(["--config", str(tmp_path / "config.yaml"), "--model", "m1",
                     "--task", str(tmp_path / "task.md"), "--container", "c", "--out", str(out)])
    assert code == 0 and built["base_url"] == "http://x/v1" and built["api_key"] == "k"
    lines = (out / "transcript.jsonl").read_text().splitlines()
    assert [json.loads(l)["role"] for l in lines] == ["system", "user", "assistant", "tool"]
    attempt = json.loads((out / "attempt.json").read_text())
    assert attempt["ended"] == "finished" and attempt["model_requested"] == "m1"


def test_command_line_needs_the_api_key(tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    import coding_agent.__main__ as cli

    (tmp_path / "config.yaml").write_text(
        "models:\n  m1:\n    base_url: http://x/v1\n    api_key_env: MISSING_KEY_FOR_TEST\n")
    monkeypatch.delenv("MISSING_KEY_FOR_TEST", raising=False)
    with pytest.raises(SystemExit):
        cli.main(["--config", str(tmp_path / "config.yaml"), "--model", "m1", "--task", "t",
                  "--container", "c", "--out", str(tmp_path / "o")])


# ---------- waiting out rate limits ----------

from coding_agent.model_client import call_with_retries, wait_before_retry  # noqa: E402


class HostError(Exception):
    def __init__(self, status_code, retry_after=None):
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code
        self.response = type("R", (), {"headers": {"retry-after": retry_after} if retry_after else {}})()


def flaky(failures, result="reply"):
    """A call that raises each error in `failures` once, then returns `result`."""
    left = list(failures)

    def fn():
        if left:
            raise left.pop(0)
        return result
    return fn


def test_rate_limit_is_waited_out_then_succeeds():
    waits = []
    out = call_with_retries(flaky([HostError(429), HostError(429), HostError(503)]),
                            max_wait_seconds=300, sleep=waits.append)
    assert out == "reply"
    assert waits == [5, 10, 20]  # backs off: 5, 10, 20 seconds


def test_gives_up_when_total_wait_would_pass_the_limit():
    waits = []
    with pytest.raises(HostError):
        call_with_retries(flaky([HostError(429)] * 20), max_wait_seconds=60, sleep=waits.append)
    assert sum(waits) <= 60
    assert waits == [5, 10, 20]  # the next wait (40) would pass 60, so it stops


def test_other_errors_are_not_retried():
    waits = []
    with pytest.raises(HostError):  # 404: the model does not exist; waiting will not help
        call_with_retries(flaky([HostError(404)]), sleep=waits.append)
    assert waits == []


def test_retry_after_header_is_respected_and_capped():
    assert wait_before_retry(HostError(429, retry_after="7"), retry=1) == 7
    assert wait_before_retry(HostError(429, retry_after="3600"), retry=1) == 60
    assert wait_before_retry(HostError(429), retry=6) == 60


def test_dropped_connection_is_retried():
    class APIConnectionError(Exception):
        pass
    waits = []
    assert call_with_retries(flaky([APIConnectionError("reset")]), sleep=waits.append) == "reply"
    assert waits == [5]


def test_real_openai_rate_limit_error_is_recognised():
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    req = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    resp = httpx.Response(429, headers={"retry-after": "2"}, request=req)
    err = openai.RateLimitError("Provider returned error", response=resp, body=None)
    waits = []
    assert call_with_retries(flaky([err]), sleep=waits.append) == "reply"
    assert waits == [2]


def test_rate_limit_waiting_does_not_count_towards_the_time_limit():
    class WaitingModel(ScriptedModel):
        waited_seconds = 0.0

        def chat(self, messages, tools):
            self.waited_seconds += 15 * 60  # every call spends 15 minutes waiting on the host
            return super().chat(messages, tools)

    model = WaitingModel(reply(call("read", path="a.py")), reply(call("finish", summary="done")))
    # Each call takes 16 minutes of clock time, 15 of them waiting: well past 60 minutes in total.
    r = run_attempt("t", FakeSandbox({"a.py": "x"}), model, Limits(max_minutes=60),
                    clock=FakeClock(step_seconds=16 * 60))
    assert r.ended == "finished"
    assert r.waited_minutes == 30


def test_daily_quota_is_not_waited_out():
    err = HostError(429)
    err.args = ("Error code: 429 - Rate limit exceeded: free-models-per-day. Add 10 credits",)
    waits = []
    with pytest.raises(HostError):
        call_with_retries(flaky([err]), sleep=waits.append)
    assert waits == []  # stops at once: the allowance only resets the next day
