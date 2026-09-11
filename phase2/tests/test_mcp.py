"""The MCP layer: every runtime operation is exposed as a read-only tool (in-process client)."""
import asyncio
import json

import pytest

pytest.importorskip("mcp")

from mcp import Client  # noqa: E402

from phase2.mcp.server import build_server  # noqa: E402
from phase2.runtime import Runtime  # noqa: E402

from .conftest import FIXTURE_DATA  # noqa: E402


def run(coro):
    return asyncio.run(coro)


async def _session(fn):
    async with Client(build_server(FIXTURE_DATA)) as c:
        return await fn(c)


def test_tools_match_runtime_operations_and_are_read_only():
    tools = run(_session(lambda c: c.list_tools())).tools
    assert {t.name for t in tools} == set(Runtime(FIXTURE_DATA).operations())
    for t in tools:
        assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False
        assert len(t.description) > 30 and t.input_schema["type"] == "object"


def test_tool_call_returns_runtime_json():
    res = run(_session(lambda c: c.call_tool("erp_financial_summary", {"period": "2026-H1"})))
    assert not res.is_error
    payload = json.loads(res.content[0].text)
    assert payload["rows"][0]["revenue_dkk"] == 22860.0 and payload["currency"] == "DKK"


def test_list_parameters_pass_through():
    res = run(_session(lambda c: c.call_tool("crm_win_rate", {"period": "2026-H1", "owner_ids": ["usr_000002"]})))
    assert json.loads(res.content[0].text)["totals"]["closed_count"] == 2


def test_stdio_server_subprocess():
    """The real transport: launch `python -m phase2.mcp.server` and talk to it over stdin/stdout."""
    import os
    import sys

    from mcp.client.stdio import StdioServerParameters

    from phase2.runtime.sources import REPO_ROOT
    params = StdioServerParameters(command=sys.executable, args=["-m", "phase2.mcp.server"], cwd=str(REPO_ROOT),
                                   env={**os.environ, "NORDFLOW_DATA_DIR": str(FIXTURE_DATA)})

    async def go():
        async with Client(params) as c:
            tools = (await c.list_tools()).tools
            res = await c.call_tool("identity_find_person", {"query": "bernd"})
            return len(tools), json.loads(res.content[0].text)
    n, payload = run(go())
    assert n == len(Runtime(FIXTURE_DATA).operations())
    assert payload["rows"][0]["payroll_employee_id"] == "DE0002"


def test_invalid_parameters_return_readable_error():
    res = run(_session(lambda c: c.call_tool("crm_win_rate", {"period": "last spring"})))
    assert res.is_error and "Unrecognised period" in res.content[0].text
    res = run(_session(lambda c: c.call_tool("erp_sales_summary", {"period": "2026", "group_by": ["planet"]})))
    assert res.is_error and "Allowed:" in res.content[0].text
