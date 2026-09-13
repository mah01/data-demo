"""
NordFlow Executive Intelligence Demo: local web server.

    make demo        (or: phase2/.venv/bin/python -m phase3.server)

Environment:
    NORDFLOW_AGENT    api | cli | auto (default auto: api if ANTHROPIC_API_KEY is set, else cli)
    ANTHROPIC_API_KEY required for api mode
    NORDFLOW_MODEL    default claude-opus-5
    NORDFLOW_EFFORT   default medium (low | medium | high | xhigh | max)
    NORDFLOW_PORT     default 8765
"""
import asyncio
import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .agent.base import Conversation, McpConnection, Turn

WEB = Path(__file__).parent / "web"
SOURCES = [  # fictional/synthetic representations of the connected systems
    {"key": "erp", "system": "ERP", "product": "e-conomic", "role": "Finance",
     "tables": {"invoices": "invoices", "customers": "customers", "ledger_entries": "ledger entries"}},
    {"key": "crm", "system": "CRM", "product": "HubSpot", "role": "CRM",
     "tables": {"deals": "deals", "companies": "companies", "activities": "activities"}},
    {"key": "payroll", "system": "Payroll", "product": "Danløn", "role": "Payroll",
     "tables": {"employees": "employees", "payroll_entries": "pay slips"}},
]


def choose_agent(mcp):
    mode = os.environ.get("NORDFLOW_AGENT", "auto").lower()
    model = os.environ.get("NORDFLOW_MODEL", "claude-opus-5")
    effort = os.environ.get("NORDFLOW_EFFORT", "medium")
    if mode == "auto":
        mode = "api" if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") else \
            ("cli" if shutil.which("claude") else "api")
    if mode == "api":
        from .agent.api_agent import ApiAgent
        return ApiAgent(mcp, model, effort)
    if mode == "cli":
        from .agent.cli_agent import CliAgent
        return CliAgent(model, effort)
    raise SystemExit(f"Unknown NORDFLOW_AGENT '{mode}' (use api, cli or auto)")


async def source_cards(mcp):
    """Source metadata for the header cards, read through the same MCP tools the agent uses."""
    described = {r["system"]: r for r in (await mcp.call_json("meta_describe_sources", {}))["rows"]}
    cards = []
    for s in SOURCES:
        d = described.get(s["key"], {})
        cov = d.get("coverage") or {}
        cards.append({**{k: s[k] for k in ("key", "system", "product", "role")},
                      "coverage": [cov.get("first"), cov.get("last")],
                      "stats": [{"label": label, "count": d.get("tables", {}).get(t)} for t, label in s["tables"].items()]})
    return cards


def create_app(agent_factory=choose_agent, mcp_factory=McpConnection):
    state = {}

    @asynccontextmanager
    async def lifespan(app):
        mcp = await mcp_factory().start()
        state.update(mcp=mcp, agent=agent_factory(mcp), conversations={}, cards=await source_cards(mcp))
        try:
            yield
        finally:
            await mcp.close()

    async def index(request):
        return FileResponse(WEB / "index.html")

    async def config(request):
        return JSONResponse({"company": "NordFlow A/S", "agent": state["agent"].info(), "sources": state["cards"]})

    async def new_conversation(request):
        conv = Conversation()
        state["conversations"][conv.id] = conv
        return JSONResponse({"id": conv.id})

    async def get_conversation(request):
        conv = state["conversations"].get(request.path_params["cid"])
        if conv is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(json.loads(json.dumps({"id": conv.id, "turns": conv.turns}, default=str)))

    async def ask(request: Request):
        conv = state["conversations"].get(request.path_params["cid"])
        body = await request.json()
        question = (body.get("question") or "").strip()
        if conv is None or not question:
            return JSONResponse({"error": "unknown conversation or empty question"}, status_code=400)
        queue = asyncio.Queue()

        async def run():
            async with conv.lock:
                turn = Turn(question)
                try:
                    record = await state["agent"].ask(conv, turn, queue.put)
                    await queue.put({"type": "answer", "turn": record})
                except Exception as exc:  # surface unexpected failures to the UI and keep the server alive
                    await queue.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
                finally:
                    await queue.put(None)

        task = asyncio.create_task(run())

        async def events():
            try:
                while (event := await queue.get()) is not None:
                    yield {"event": event["type"], "data": json.dumps(event, default=str, ensure_ascii=False)}
            finally:
                if not task.done():
                    await task  # finish the turn even if the browser disconnects, so history stays consistent

        return EventSourceResponse(events(), ping=15)

    return Starlette(lifespan=lifespan, routes=[
        Route("/", index),
        Route("/api/config", config),
        Route("/api/conversations", new_conversation, methods=["POST"]),
        Route("/api/conversations/{cid}", get_conversation),
        Route("/api/conversations/{cid}/ask", ask, methods=["POST"]),
        Mount("/static", StaticFiles(directory=WEB), name="static"),
    ])


def main():
    port = int(os.environ.get("NORDFLOW_PORT", "8765"))
    print(f"NordFlow demo on http://127.0.0.1:{port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
