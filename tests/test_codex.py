import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from ppt_ai_coach.codex_client import CodexClient, build_prompt, cli_prefix
from ppt_ai_coach.errors import CoachError


@pytest.fixture
def mocked_cli(monkeypatch):
    monkeypatch.setattr("ppt_ai_coach.codex_client.shutil.which", lambda _: "/fake/codex")
    reply = {
        "feedback": "Be specific.",
        "improved_example": "Let's try a two-week pilot.",
        "question": "Which team would join the pilot?",
    }

    def run(command, **kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        schema = json.loads(Path(command[command.index("--output-schema") + 1]).read_text())
        data = (
            {"summary": "## Next practice\nExplain value clearly."}
            if (schema["required"] == ["summary"])
            else reply
        )
        output.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    mock = Mock(side_effect=run)
    monkeypatch.setattr("ppt_ai_coach.codex_client.subprocess.run", mock)
    return mock, reply


def test_safe_invocation_and_context(session, mocked_cli):
    mock, _ = mocked_cli
    malicious_text = 'A fictional product. $(do_something) & echo "hello"'
    result = CodexClient(model="test-model").coach(
        session.slides[0], malicious_text, session.turns, "discussion"
    )
    args, kwargs = mock.call_args
    command = args[0]
    assert result.question.endswith("?")
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--model") + 1] == "test-model"
    assert malicious_text not in command
    assert "shell" not in kwargs or kwargs["shell"] is False
    assert kwargs["encoding"] == "utf-8"
    assert "Ask about goals" in kwargs["input"]
    assert "We help teams plan" in kwargs["input"]
    assert "untrusted" in kwargs["input"]
    assert not Path(kwargs["cwd"]).exists(), "CLI temporary directory must be deleted"


def test_context_is_bounded_and_bad_input_rejected(session):
    turns = session.turns * 12
    prompt = build_prompt(session.slides[0], "Hello", turns, "presentation")
    data = json.loads(prompt.split("PRACTICE_DATA:\n", 1)[1])
    assert len(data["previous_discussion"]) == 8
    for text, mode in [("", "presentation"), ("x" * 20001, "presentation"), ("Hi", "bad")]:
        with pytest.raises(CoachError):
            build_prompt(session.slides[0], text, [], mode)


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"feedback": "only one field"},
        {
            "feedback": 42,
            "improved_example": "Try again",
            "question": "Why?",
        },
        {"feedback": "Okay", "improved_example": "Hello", "question": "no question"},
    ],
)
def test_invalid_model_response(session, monkeypatch, mocked_cli, value):
    def run(command, **kwargs):
        Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(value))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("ppt_ai_coach.codex_client.subprocess.run", run)
    with pytest.raises(CoachError):
        CodexClient().coach(session.slides[0], "Hello", [], "presentation")


def test_timeout_and_cli_error_never_expose_stderr(session, monkeypatch, mocked_cli):
    monkeypatch.setattr(
        "ppt_ai_coach.codex_client.subprocess.run",
        Mock(side_effect=subprocess.TimeoutExpired("codex", 1)),
    )
    with pytest.raises(CoachError, match="超时"):
        CodexClient(timeout=1).coach(session.slides[0], "Hello", [], "presentation")
    monkeypatch.setattr(
        "ppt_ai_coach.codex_client.subprocess.run",
        Mock(return_value=subprocess.CompletedProcess([], 1, "", "private credential")),
    )
    with pytest.raises(CoachError) as error:
        CodexClient().coach(session.slides[0], "Hello", [], "presentation")
    assert "private credential" not in str(error.value)


def test_missing_cli_and_invalid_model(session, monkeypatch, mocked_cli):
    with pytest.raises(CoachError, match="模型名称"):
        CodexClient(model="bad & command").coach(session.slides[0], "Hello", [], "presentation")
    monkeypatch.setattr("ppt_ai_coach.codex_client.shutil.which", lambda _: None)
    with pytest.raises(CoachError, match="找不到"):
        CodexClient().coach(session.slides[0], "Hello", [], "presentation")


def test_overall_summary_preserves_all_pages(session, mocked_cli):
    mock, _ = mocked_cli
    assert "Next practice" in CodexClient().summarize(session)
    assert '"slide": 2' in mock.call_args.kwargs["input"]
    assert "Not practiced" in mock.call_args.kwargs["input"]


def test_windows_npm_shim_uses_node_without_cmd_shell(tmp_path, monkeypatch):
    base = tmp_path / "A&B user"
    script = base / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    script.parent.mkdir(parents=True)
    script.write_text("// mock npm CLI entrypoint")
    node = base / "node.exe"
    node.write_bytes(b"mock executable")
    assert cli_prefix(str(base / "codex.cmd"), windows=True) == [str(node), str(script)]


def test_unknown_windows_cmd_shim_rejected(tmp_path):
    with pytest.raises(CoachError, match="标准 npm"):
        cli_prefix(str(tmp_path / "custom.cmd"), windows=True)
    assert cli_prefix("codex.exe", windows=True) == ["codex.exe"]
