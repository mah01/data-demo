"""
OpenAI agent tests. The model is scripted with the SDK's real Responses output item types
(no network, no API key); the MCP server and runtime are real, on fixture data.
"""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace as NS

import openai
import pytest
from openai.types.responses import (ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputRefusal,
                                    ResponseOutputText, ResponseReasoningItem)

from phase3.agent import base
from phase3.agent.base import Conversation, McpConnection, Turn
from phase3.agent.openai_agent import OpenAIAgent, function_parameters
from phase3.agent.prompt import SYSTEM_PROMPT
from phase3.config import Settings, redact

PHASE3 = Path(__file__).resolve().parents[1]
FIXTURE_DATA = PHASE3.parent / "phase2" / "tests" / "fixtures" / "data"
OPENAI_KEY = "sk-proj-EXAMPLEexample0123456789abcdef"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("NORDFLOW_DATA_DIR", str(FIXTURE_DATA))
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "NORDFLOW_AUTH_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(base, "LOG_DIR", tmp_path / "logs")


def call(i, name, **arguments):
    return ResponseFunctionToolCall(type="function_call", id=f"fc_{i}", call_id=f"call_{i}", name=name,
                                    arguments=json.dumps(arguments), status="completed")


def reasoning(i):
    return ResponseReasoningItem(type="reasoning", id=f"rs_{i}", summary=[], encrypted_content=f"opaque-{i}")


def message(text):
    return ResponseOutputMessage(type="message", id="msg_1", role="assistant", status="completed",
                                 content=[ResponseOutputText(type="output_text", text=text, annotations=[])])


def response(*items, status="completed", cached=0):
    text = "".join(c.text for i in items if i.type == "message" for c in i.content if c.type == "output_text")
    usage = NS(input_tokens=1000, output_tokens=50, input_tokens_details=NS(cached_tokens=cached, cache_write_tokens=0),
               output_tokens_details=NS(reasoning_tokens=20))
    return NS(output=list(items), status=status, error=None, incomplete_details=None, usage=usage, output_text=text)


class ScriptedOpenAI:
    """Stands in for openai.AsyncOpenAI: returns scripted responses and records requests."""

    def __init__(self, script):
        self.script, self.requests = list(script), []
        self.responses = NS(create=self.create)

    async def create(self, **kwargs):
        self.requests.append({**kwargs, "input": json.loads(json.dumps(kwargs["input"]))})
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


ANSWER = dict(headline="Revenue rose while profit fell.", key_points=["Interpretation: costs grew faster."],
              evidence=[{"metric": "Revenue", "value": "22.9k DKK", "system": "ERP", "period": "H1 2026"},
                        {"metric": "Win rate", "value": "33%", "system": "CRM"}],
              follow_up_questions=["Why did costs grow?"])


async def _noop(e):
    pass


def run_turns(client, questions):
    async def go():
        mcp = await McpConnection().start()
        try:
            agent, conv, events = OpenAIAgent(mcp, "gpt-5.6-sol", "medium", client=client), Conversation(), []

            async def emit(e):
                events.append(e)
            records = [await agent.ask(conv, Turn(q), emit) for q in questions]
            return agent, conv, events, records
        finally:
            await mcp.close()
    return asyncio.run(go())


def test_openai_agent_investigates_through_mcp_and_keeps_context():
    client = ScriptedOpenAI([
        response(reasoning(1), call(1, "meta_describe_sources"), call(2, "erp_financial_summary", period="2026-H1")),
        response(call(3, "crm_win_rate", period="nonsense"), cached=800),       # tool error must be survivable
        response(reasoning(2), call(4, "present_answer", **ANSWER), cached=900),
        response(call(5, "erp_customer_revenue", period="2026-H1", compare_to="2025-H1")),
        response(call(6, "present_answer", headline="Customer 10001 fell most.",
                      evidence=[{"metric": "Alpha Vand change", "value": "-9.0k DKK", "system": "ERP"}])),
    ])
    agent, conv, events, (first, second) = run_turns(client, ["How is the business doing?", "Which customers caused that?"])

    # request shape: all MCP tools as function tools, neutral instruction, stateless, cache key per conversation
    req = client.requests[0]
    names = {t["name"] for t in req["tools"]}
    assert len(names) == 34 and "present_answer" in names and all(t["type"] == "function" for t in req["tools"])
    assert req["instructions"] == SYSTEM_PROMPT and req["model"] == "gpt-5.6-sol"
    assert req["store"] is False and req["include"] == ["reasoning.encrypted_content"]
    assert req["reasoning"] == {"effort": "medium"} and req["prompt_cache_key"] == f"nordflow-{conv.id}"
    assert req["input"] == [{"role": "user", "content": "How is the business doing?"}]

    # real MCP results flowed back as function_call_output items, reasoning passed back encrypted
    second_input = client.requests[1]["input"]
    assert {"type": "reasoning", "id": "rs_1", "encrypted_content": "opaque-1"}.items() <= second_input[1].items()
    fin = next(i for i in second_input if i.get("type") == "function_call_output" and i["call_id"] == "call_2")
    assert json.loads(fin["output"])["rows"][0]["revenue_dkk"] == 22860.0
    err = client.requests[2]["input"][-1]
    assert err["output"].startswith("Tool error:") and "Unrecognised period" in err["output"]

    # turn 1 record: same contract as the Anthropic agent
    assert first["answer"]["headline"] == ANSWER["headline"] and first["answer_structured"]
    assert first["agent"] == {"mode": "openai", "model": "gpt-5.6-sol", "effort": "medium"}
    assert first["tool_call_count"] == 3 and len(first["mcp_errors"]) == 1 and first["sources"] == ["CRM", "ERP"]
    assert [e["verified_source"] for e in first["answer"]["evidence"]] == [True, False]
    assert first["usage"] == {"input_tokens": 3000, "cached_input_tokens": 1700, "cache_write_tokens": 0,
                              "output_tokens": 150, "reasoning_tokens": 60}
    assert [e["type"] for e in events[:2]] == ["tool_call", "tool_call"]

    # turn 2 carries the whole history and answers present_answer's pending output before the new question
    turn2 = client.requests[3]["input"]
    assert turn2[0] == {"role": "user", "content": "How is the business doing?"}
    assert turn2[-2]["type"] == "function_call_output" and turn2[-2]["call_id"] == "call_4"
    assert turn2[-1] == {"role": "user", "content": "Which customers caused that?"}
    assert second["turn"] == 2 and second["answer"]["evidence"][0]["verified_source"] is True
    log = (base.LOG_DIR / f"{conv.id}.jsonl").read_text().splitlines()
    assert [json.loads(l)["question"] for l in log] == ["How is the business doing?", "Which customers caused that?"]
    assert "opaque-1" not in "".join(log)  # reasoning never reaches the log


def test_bad_arguments_text_answers_and_refusals_are_handled():
    bad = ResponseFunctionToolCall(type="function_call", id="fc_x", call_id="call_x", name="crm_deals",
                                   arguments="{not json", status="completed")
    client = ScriptedOpenAI([response(bad), response(message("Data unavailable."))])
    _, _, _, (rec,) = run_turns(client, ["q"])
    assert client.requests[1]["input"][-1]["output"].startswith("Tool error: Arguments were not valid JSON")
    assert rec["answer"]["headline"] == "Data unavailable." and rec["answer_structured"] is False
    assert rec["mcp_errors"][0]["tool"] == "crm_deals"

    refusal = ResponseOutputMessage(type="message", id="msg_r", role="assistant", status="completed",
                                    content=[ResponseOutputRefusal(type="refusal", refusal="No.")])
    _, _, _, (rec,) = run_turns(ScriptedOpenAI([response(refusal)]), ["q"])
    assert rec["errors"] == ["The model declined this request."] and rec["answer"] is None


def test_provider_error_rolls_back_history_and_is_redacted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", OPENAI_KEY)
    client = ScriptedOpenAI([
        response(call(1, "erp_sales_summary", period="2026-H1")),
        openai.OpenAIError(f"Incorrect API key provided: {OPENAI_KEY}"),
        response(message("Recovered.")),
    ])
    _, conv, _, (failed, ok) = run_turns(client, ["first", "second"])
    assert OPENAI_KEY not in json.dumps(failed) and "[redacted]" in failed["errors"][0]
    assert OPENAI_KEY not in (base.LOG_DIR / f"{conv.id}.jsonl").read_text()
    # the failed turn left nothing behind: the next request starts from a clean history
    assert client.requests[2]["input"] == [{"role": "user", "content": "second"}]
    assert ok["answer"]["headline"] == "Recovered."


def test_function_parameters_inline_refs_and_always_have_properties():
    schema = {"type": "object", "$defs": {"E": {"type": "object", "properties": {"v": {"type": "string"}}}},
              "properties": {"evidence": {"type": "array", "items": {"$ref": "#/$defs/E"}}}}
    out = function_parameters(schema)
    assert "$defs" not in json.dumps(out) and "$ref" not in json.dumps(out)
    assert out["properties"]["evidence"]["items"]["properties"]["v"] == {"type": "string"}
    assert function_parameters({"type": "object"}) == {"type": "object", "properties": {}}
    assert "$defs" in schema  # input left untouched


def test_openai_configuration_and_redaction():
    deploy = {"NORDFLOW_MODE": "deploy", "NORDFLOW_AUTH_USER": "board", "NORDFLOW_AUTH_PASSWORD": "correct-horse-battery"}
    missing = Settings.from_env({**deploy, "NORDFLOW_AGENT": "openai"})
    assert any(p.startswith("OPENAI_API_KEY is not set") for p in missing.problems())

    s = Settings.from_env({**deploy, "NORDFLOW_AGENT": "openai", "OPENAI_API_KEY": OPENAI_KEY})
    assert s.problems() == [] and s.agent == "openai" and s.model == "gpt-5.6-sol"
    assert s.summary()["api_key"] == "OPENAI_API_KEY set" and OPENAI_KEY not in repr(s) + json.dumps(s.summary())
    assert s.without_secrets().secret_values() == ()

    # never chosen implicitly: an OPENAI_API_KEY left in a shell must not switch the demo to paid calls
    auto = Settings.from_env({**deploy, "OPENAI_API_KEY": OPENAI_KEY})
    assert auto.agent == "api" and any("only used when chosen explicitly" in p for p in auto.problems())
    local = Settings.from_env({"OPENAI_API_KEY": OPENAI_KEY})
    assert local.agent in ("api", "cli") and local.agent != "openai"
    assert Settings.from_env({**deploy, "OPENAI_API_KEY": OPENAI_KEY, "NORDFLOW_MODEL": "gpt-6-astra"}).model == "gpt-6-astra"

    assert redact(f"key {OPENAI_KEY} and sk-svcacct-ABCDEFGHIJKLMNOPQRSTUV") == "key [redacted] and [redacted]"
    ordinary = "desk-reassignment_of_key_accounts task-follow_up_on_renewals"
    assert redact(ordinary) == ordinary  # no false positives inside ordinary words
