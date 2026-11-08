"""実際の API を呼ばず、承認前・承認後・拒否後のファイルを検証する。"""

import pytest
from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolDenied
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, run_with_approval


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    path = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", path)
    return path


def saving_model():
    return TestModel(call_tools=["save_learning_log"])


def test_save_waits_for_approval(log_dir):
    result = agent.run_sync("学習内容を保存して", model=saving_model())
    assert isinstance(result.output, DeferredToolRequests)
    assert len(result.output.approvals) == 1
    assert result.output.approvals[0].tool_name == "save_learning_log"
    assert not log_dir.exists()


@pytest.mark.parametrize("approved", [True, False])
def test_resume_uses_approval_and_history(log_dir, approved):
    model = saving_model()
    pending = agent.run_sync("学習内容を保存して", model=model)
    call = pending.output.approvals[0]
    decision = True if approved else ToolDenied("保存しない")
    result = agent.run_sync(
        None,
        model=model,
        message_history=pending.all_messages(),
        deferred_tool_results=DeferredToolResults(approvals={call.tool_call_id: decision}),
    )
    assert isinstance(result.output, str)
    if approved:
        files = list(log_dir.glob("*.md"))
        assert len(files) == 1
        assert files[0].read_text(encoding="utf-8") == call.args_as_dict()["content"].strip() + "\n"
    else:
        assert not log_dir.exists()
        returns = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart)]
        assert any("保存しない" in str(p.content) for p in returns)


@pytest.mark.parametrize("reply, expected", [("y", True), ("YES", True), ("n", False), ("", False), ("maybe", False)])
def test_cli_only_saves_on_explicit_yes(log_dir, monkeypatch, capsys, reply, expected):
    def answer(prompt):
        assert not log_dir.exists()
        return reply

    monkeypatch.setattr("builtins.input", answer)
    result = run_with_approval(agent, "学習内容を保存して", saving_model())
    assert isinstance(result.output, str)
    assert log_dir.exists() is expected
    assert "save_learning_log" in capsys.readouterr().out


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
def test_interrupted_confirmation_does_not_save(log_dir, monkeypatch, error):
    def interrupt(prompt):
        raise error

    monkeypatch.setattr("builtins.input", interrupt)
    result = run_with_approval(agent, "学習内容を保存して", saving_model())
    assert isinstance(result.output, str)
    assert not log_dir.exists()


def test_records_are_utf8_and_do_not_overwrite(log_dir):
    tools.save_learning_log("LoRAについて学んだ。")
    tools.save_learning_log("LoRAについて学んだ。")
    files = list(log_dir.glob("*.md"))
    assert len(files) == 2
    assert all(p.read_text(encoding="utf-8") == "LoRAについて学んだ。\n" for p in files)


def test_empty_content_is_not_saved(log_dir):
    assert "保存しませんでした" in tools.save_learning_log(" \n ")
    assert not log_dir.exists()
