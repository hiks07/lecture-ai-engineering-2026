"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from app import tools

from app.agent import agent

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel(call_tools=sorted(BASE_TOOLS))
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    assert len(_parts(result, ToolReturnPart)) == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"

def test_approved_save_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DATA_DIR", tmp_path / "data")
    model = TestModel(call_tools=["save_learning_log"])

    pending = agent.run_sync("学習内容を保存して", model=model)
    assert isinstance(pending.output, DeferredToolRequests)
    call = pending.output.approvals[0]

    agent.run_sync(
        None,
        model=model,
        message_history=pending.all_messages(),
        deferred_tool_results=DeferredToolResults(
            approvals={call.tool_call_id: True}
        ),
    )

    files = list((tmp_path / "learning_log").glob("*.md"))
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == (
        call.args_as_dict()["content"].strip() + "\n"
    )


def test_denied_save_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DATA_DIR", tmp_path / "data")
    model = TestModel(call_tools=["save_learning_log"])

    pending = agent.run_sync("学習内容を保存して", model=model)
    assert isinstance(pending.output, DeferredToolRequests)
    call = pending.output.approvals[0]

    agent.run_sync(
        None,
        model=model,
        message_history=pending.all_messages(),
        deferred_tool_results=DeferredToolResults(
            approvals={call.tool_call_id: False}
        ),
    )

    assert not (tmp_path / "learning_log").exists()