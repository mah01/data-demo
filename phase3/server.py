"""
NordFlow Executive Intelligence Demo: web server.

    make demo                                   local, http://127.0.0.1:8765
    make demo-check                             validate configuration and data, then exit
    phase2/.venv/bin/python -m phase3.server    same as make demo

Configuration is environment-only (see phase3/config.py and phase3/DEPLOY.md):

    NORDFLOW_MODE          local (default) | deploy
    NORDFLOW_AGENT         api | openai | cli | auto   (deploy requires api or openai)
    ANTHROPIC_API_KEY      required for the api agent (Anthropic); server-side only
    OPENAI_API_KEY         required for the openai agent; server-side only
    NORDFLOW_AUTH_USER     shared HTTP Basic user      (required in deploy)
    NORDFLOW_AUTH_PASSWORD shared HTTP Basic password  (required in deploy)
    NORDFLOW_MODEL / NORDFLOW_EFFORT / NORDFLOW_HOST / NORDFLOW_PORT
    NORDFLOW_MAX_CONVERSATIONS / NORDFLOW_MAX_QUESTION_CHARS
"""
import asyncio
import json
import os
import sys
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
from .auth import BasicAuthMiddleware
from .config import ConfigError, load_settings

WEB = Path(__file__).parent / "web"
SOURCES = [  # fictional/synthetic representations of the connected systems
    {"key": "erp", "system": "ERP", "product": "e-conomic", "role": "Finance",
     "tables": {"invoices": "invoices", "customers": "customers", "ledger_entries": "ledger entries"}},
    {"key": "crm", "system": "CRM", "product": "HubSpot", "role": "CRM",
     "tables": {"deals": "deals", "companies": "companies", "activities": "activities"}},
    {"key": "payroll", "system": "Payroll", "product": "Danløn", "role": "Payroll",
     "tables": {"employees": "employees", "payroll_entries": "pay slips"}},
]


def choose_agent(mcp, settings):
    if settings.agent == "api":
        from .agent.api_agent import ApiAgent
        return ApiAgent(mcp, settings.model, settings.effort)
    if settings.agent == "openai":
        from .agent.openai_agent import OpenAIAgent
        return OpenAIAgent(mcp, settings.model, settings.effort)
    from .agent.cli_agent import CliAgent
    return CliAgent(settings.model, settings.effort)


async def source_cards(mcp):
    """Source metadata for the header cards, read through the same MCP tools the agent uses."""
    described = {r["system"]: r for r in (await mcp.call_json("meta_describe_sources", {}))["rows"]}
    missing = [s["key"] for s in SOURCES if not described.get(s["key"], {}).get("tables")]
    if missing:
        raise RuntimeError(f"No data found for {', '.join(missing)}. Check NORDFLOW_DATA_DIR and that data/ is populated.")
    cards = []
    for s in SOURCES:
        d = described.get(s["key"], {})
        cov = d.get("coverage") or {}
        cards.append({**{k: s[k] for k in ("key", "system", "product", "role")},
                      "coverage": [cov.get("first"), cov.get("last")],
                      "stats": [{"label": label, "count": d.get("tables", {}).get(t)} for t, label in s["tables"].items()]})
    return cards


def create_app(agent_factory=None, mcp_factory=McpConnection, settings=None):
    settings = settings or load_settings()
    # a supplied agent_factory brings its own credentials (tests, embedding), so skip that one check
    settings.check(check_agent_credentials=agent_factory is None)
    make_agent = agent_factory or (lambda mcp: choose_agent(mcp, settings))
    state = {}

    @asynccontextmanager
    async def lifespan(app):
        mcp = await mcp_factory().start()
        try:
            state.update(mcp=mcp, agent=make_agent(mcp), conversations={}, cards=await source_cards(mcp))
            yield
        finally:
            await mcp.close()

    def json_response(payload, status_code=200):
        return JSONResponse(payload, status_code=status_code, headers={"Cache-Control": "no-store"})

    async def index(request):
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})

    async def healthz(request):
        """Unauthenticated liveness probe. Reveals no configuration and no data."""
        return json_response({"status": "ok" if state.get("cards") else "starting"})

    async def config(request):
        return json_response({"company": "NordFlow A/S", "agent": state["agent"].info(), "sources": state["cards"]})

    async def new_conversation(request):
        conv = Conversation()
        conversations = state["conversations"]
        conversations[conv.id] = conv
        while len(conversations) > settings.max_conversations:  # bounded memory on a small VM
            conversations.pop(next(iter(conversations)))
        return json_response({"id": conv.id})

    async def get_conversation(request):
        conv = state["conversations"].get(request.path_params["cid"])
        if conv is None:
            return json_response({"error": "not found"}, status_code=404)
        return json_response(json.loads(json.dumps({"id": conv.id, "turns": conv.turns}, default=str)))

    async def ask(request: Request):
        conv = state["conversations"].get(request.path_params["cid"])
        try:
            body = await request.json()
        except ValueError:
            return json_response({"error": "invalid request body"}, status_code=400)
        question = (body.get("question") or "").strip()
        if conv is None or not question:
            return json_response({"error": "unknown conversation or empty question"}, status_code=400)
        if len(question) > settings.max_question_chars:
            return json_response({"error": f"question longer than {settings.max_question_chars} characters"},
                                 status_code=413)
        queue = asyncio.Queue()

        async def run():
            async with conv.lock:
                turn = Turn(question)
                try:
                    record = await state["agent"].ask(conv, turn, queue.put)
                    await queue.put({"type": "answer", "turn": record})
                except Exception as exc:  # surface unexpected failures to the UI and keep the server alive
                    await queue.put({"type": "error", "message": settings.redact(f"{type(exc).__name__}: {exc}")})
                finally:
                    await queue.put(None)

        task = asyncio.create_task(run())

        async def events():
            try:
                while (event := await queue.get()) is not None:
                    yield {"event": event["type"],
                           "data": settings.redact(json.dumps(event, default=str, ensure_ascii=False))}
            finally:
                if not task.done():
                    await task  # finish the turn even if the browser disconnects, so history stays consistent

        return EventSourceResponse(events(), ping=15, headers={"Cache-Control": "no-store"})

    app = Starlette(lifespan=lifespan, routes=[
        Route("/", index),
        Route("/healthz", healthz),
        Route("/api/config", config),
        Route("/api/conversations", new_conversation, methods=["POST"]),
        Route("/api/conversations/{cid}", get_conversation),
        Route("/api/conversations/{cid}/ask", ask, methods=["POST"]),
        Mount("/static", StaticFiles(directory=WEB), name="static"),
    ])
    app.state.settings = settings.without_secrets()
    if settings.auth_required:
        app.add_middleware(BasicAuthMiddleware, user=settings.auth_user, password=settings.auth_password)
    return app


async def health_check(settings, mcp_factory=McpConnection):
    """Start the MCP server, read the sources, and report what the demo would serve."""
    mcp = await mcp_factory().start()
    try:
        cards = await source_cards(mcp)
        return {"tools": len(mcp.tools),
                "sources": {c["product"]: sum(s["count"] or 0 for s in c["stats"]) for c in cards},
                "coverage": cards[0]["coverage"]}
    finally:
        await mcp.close()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    check_only = "--check" in argv
    settings = load_settings()
    try:
        settings.check()
    except ConfigError as exc:
        print(exc.report(), file=sys.stderr, flush=True)
        raise SystemExit(2)

    summary = settings.summary()
    print("NordFlow demo configuration: " + "  ".join(f"{k}={v}" for k, v in summary.items()), flush=True)
    try:
        health = asyncio.run(health_check(settings))
    except Exception as exc:
        print(f"Data/MCP health check failed: {type(exc).__name__}: {settings.redact(exc)}", file=sys.stderr, flush=True)
        raise SystemExit(2)
    print(f"Data/MCP health check: ok - {health['tools']} tools, "
          + ", ".join(f"{k} {v} records" for k, v in health["sources"].items())
          + f", {health['coverage'][0]} to {health['coverage'][1]}", flush=True)
    if check_only:
        print("Configuration and data are usable. (No LLM call was made and no port was opened.)", flush=True)
        return 0

    scheme_note = "" if settings.auth_required else "  (no authentication - local mode)"
    print(f"Serving on http://{settings.host}:{settings.port}{scheme_note}", flush=True)
    uvicorn.run(create_app(settings=settings), host=settings.host, port=settings.port,
                log_level="warning", access_log=False, proxy_headers=True,
                forwarded_allow_ips=os.environ.get("NORDFLOW_FORWARDED_ALLOW_IPS", "127.0.0.1"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
