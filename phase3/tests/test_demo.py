"""
Phase 3 tests. The model is scripted (no LLM calls); the MCP server and runtime are real,
so these check the plumbing: tool calls go through MCP, context carries across turns,
answers/evidence/traces are assembled and logged, and the web API streams them.
"""
import ast
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from starlette.testclient import TestClient

from phase3.agent import base
from phase3.agent.api_agent import ApiAgent
from phase3.agent.base import Conversation, McpConnection, Turn
from phase3.agent.cli_agent import StreamParser, build_command
from phase3.agent.prompt import SYSTEM_PROMPT
from phase3.server import create_app

PHASE3 = Path(__file__).resolve().parents[1]
FIXTURE_DATA = PHASE3.parent / "phase2" / "tests" / "fixtures" / "data"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("NORDFLOW_DATA_DIR", str(FIXTURE_DATA))
    monkeypatch.setattr(base, "LOG_DIR", tmp_path / "logs")


def tool_use(i, name, **inp):
    return NS(type="tool_use", id=f"tu_{i}", name=name, input=inp)


def response(*blocks, stop="tool_use"):
    return NS(content=list(blocks), stop_reason=stop,
              usage=NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0))


class ScriptedClient:
    """Stands in for anthropic.AsyncAnthropic: returns scripted responses and records requests."""

    def __init__(self, script):
        self.script, self.requests = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    async def create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.script.pop(0)


ANSWER = dict(headline="Revenue rose while profit fell.", key_points=["Interpretation: costs grew faster."],
              evidence=[{"metric": "Revenue", "value": "22.9k DKK", "system": "ERP", "period": "H1 2026"},
                        {"metric": "Win rate", "value": "33%", "system": "CRM"}],
              follow_up_questions=["Why did costs grow?"])


def run(coro):
    return asyncio.run(coro)


async def two_turns(client):
    mcp = await McpConnection().start()
    try:
        agent = ApiAgent(mcp, "claude-opus-5", "medium", client=client)
        conv, events = Conversation(), []
        first = await agent.ask(conv, Turn("How is the business doing?"), lambda e: _append(events, e))
        second = await agent.ask(conv, Turn("Which customers caused that?"), lambda e: _append(events, e))
        return agent, conv, events, first, second
    finally:
        await mcp.close()


async def _append(lst, e):
    lst.append(e)


def test_api_agent_investigates_through_mcp_and_keeps_context():
    client = ScriptedClient([
        response(tool_use(1, "meta_describe_sources"), tool_use(2, "erp_financial_summary", period="2026-H1")),
        response(tool_use(3, "crm_win_rate", period="nonsense")),              # tool error must be survivable
        response(tool_use(4, "present_answer", **ANSWER)),
        response(tool_use(5, "erp_customer_revenue", period="2026-H1", compare_to="2025-H1")),
        response(tool_use(6, "present_answer", headline="Customer 10001 fell most.",
                          evidence=[{"metric": "Alpha Vand change", "value": "-9.0k DKK", "system": "ERP"}])),
    ])
    agent, conv, events, first, second = run(two_turns(client))

    # tools offered to the model = Phase 2A tools + present_answer, with the demo system prompt
    names = {t["name"] for t in client.requests[0]["tools"]}
    assert "erp_financial_summary" in names and "present_answer" in names and len(names) == 34
    assert client.requests[0]["system"] == SYSTEM_PROMPT

    # real MCP results flowed back to the model
    tool_results = client.requests[1]["messages"][-1]["content"]
    fin = next(r for r in tool_results if r["tool_use_id"] == "tu_2")
    assert json.loads(fin["content"])["rows"][0]["revenue_dkk"] == 22860.0
    err = client.requests[2]["messages"][-1]["content"][0]
    assert err["is_error"] is True and "Unrecognised period" in err["content"]

    # turn 1 record
    assert first["answer"]["headline"] == ANSWER["headline"] and first["answer_structured"]
    assert first["tool_call_count"] == 3 and len(first["mcp_errors"]) == 1
    assert first["sources"] == ["CRM", "ERP"]
    assert [e["verified_source"] for e in first["answer"]["evidence"]] == [True, False]  # CRM call failed
    assert [e["type"] for e in events[:2]] == ["tool_call", "tool_call"]

    # turn 2 carries the whole history, and answers present_answer's pending tool_result first
    msgs = client.requests[3]["messages"]
    assert "How is the business doing?" in json.dumps([m["content"] for m in msgs if m["role"] == "user"], default=str)
    last_user = msgs[-1]["content"]
    assert last_user[0]["type"] == "tool_result" and last_user[0]["tool_use_id"] == "tu_4"
    assert last_user[-1] == {"type": "text", "text": "Which customers caused that?"}
    assert second["turn"] == 2 and second["answer"]["evidence"][0]["verified_source"] is True

    # both turns logged
    log = (base.LOG_DIR / f"{conv.id}.jsonl").read_text().splitlines()
    assert [json.loads(l)["question"] for l in log] == ["How is the business doing?", "Which customers caused that?"]


def test_api_agent_plain_text_answer_is_kept_as_fallback():
    client = ScriptedClient([response(NS(type="text", text="Data unavailable."), stop="end_turn")])

    async def go():
        mcp = await McpConnection().start()
        try:
            return await ApiAgent(mcp, "m", "low", client=client).ask(Conversation(), Turn("q"), _noop)
        finally:
            await mcp.close()
    rec = run(go())
    assert rec["answer"]["headline"] == "Data unavailable." and rec["answer_structured"] is False


async def _noop(e):
    pass


def test_cli_stream_parser_and_command():
    turn = Turn("q")
    p = StreamParser(turn)
    lines = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "mcp__nordflow__crm_win_rate", "input": {"period": "2026-H1"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": [{"type": "text", "text": "{}"}]}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b", "name": "mcp__nordflow__present_answer", "input": ANSWER}]}},
        {"type": "result", "result": "Done.", "usage": {"output_tokens": 9}},
    ]
    events = [e for l in lines for e in p.feed(json.dumps(l))]
    assert [e["type"] for e in events] == ["tool_call", "tool_result", "tool_call"]
    assert turn.calls[0].system == "CRM" and turn.calls[0].ok is True and turn.answer == ANSWER
    cmd = build_command("q", "cfg.json", "claude-opus-5", "medium", "sid", resume=True)
    assert cmd[cmd.index("--resume") + 1] == "sid" and cmd[cmd.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" not in cmd


class FakeAgent:
    mode = "fake"

    def info(self):
        return {"mode": "fake", "model": "none", "effort": "none"}

    async def ask(self, conv, turn, emit):
        call = turn.new_call("erp_sales_summary", {"period": "2026-H1"})
        call.ok = True
        await emit({"type": "tool_call", "seq": 1, "tool": call.tool, "system": call.system, "arguments": call.arguments})
        turn.answer = {"headline": f"Answer to: {turn.question}", "evidence": []}
        return base.finish_turn(conv, turn, self.info())


def test_web_api_serves_page_sources_and_streams_answers():
    app = create_app(agent_factory=lambda mcp: FakeAgent())
    with TestClient(app) as client:
        assert "Executive Intelligence Demo" in client.get("/").text
        assert client.get("/static/app.js").status_code == 200
        cfg = client.get("/api/config").json()
        assert [s["product"] for s in cfg["sources"]] == ["e-conomic", "HubSpot", "Danløn"]
        assert cfg["sources"][0]["stats"][0] == {"label": "invoices", "count": 6}   # read via MCP (fixture data)
        cid = client.post("/api/conversations").json()["id"]
        with client.stream("POST", f"/api/conversations/{cid}/ask", json={"question": "How is Germany?"}) as r:
            body = "".join(r.iter_text())
        assert "event: tool_call" in body and "event: answer" in body and "Answer to: How is Germany?" in body
        turns = client.get(f"/api/conversations/{cid}").json()["turns"]
        assert len(turns) == 1 and turns[0]["sources"] == ["ERP"]
        assert client.post(f"/api/conversations/{cid}/ask", json={"question": " "}).status_code == 400


def test_demo_code_has_no_access_to_evaluation_material():
    forbidden_modules = {"src", "analysis", "metrics", "validate", "robustness", "generate", "world", "config", "roster"}
    forbidden_text = ["ground_truth", "phase2/evaluation", "phase2.evaluation", "assessments", "reference_facts", "baseline_report", "rheinmark",
                      "brandauer"]
    files = [p for p in PHASE3.rglob("*") if p.suffix in (".py", ".js", ".html") and "tests" not in p.parts]
    for path in files:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(text)):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
                for m in mods:
                    assert m.split(".")[0] not in forbidden_modules, f"{path.name} imports {m}"
                    assert not m.startswith("phase2.evaluation"), f"{path.name} imports {m}"
        for token in forbidden_text:
            assert token not in text.lower(), f"{path.name} mentions '{token}'"
