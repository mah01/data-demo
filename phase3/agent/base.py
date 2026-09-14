"""Shared pieces: MCP connection, conversation state, turn recording and answer assembly."""
import asyncio
import json
import sys
import time
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from phase2.runtime.sources import REPO_ROOT

from ..config import redact
from .prompt import system_of

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
MAX_TOOL_RESULT_CHARS = 60_000


def now():
    return datetime.now(timezone.utc).isoformat()


SECRET_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "NORDFLOW_AUTH_USER", "NORDFLOW_AUTH_PASSWORD")


def server_params(extra_env=None):
    import os
    # the MCP server only reads CSV files: it is started without the credentials this process holds
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}
    env |= {"PYTHONPATH": str(REPO_ROOT),
            "NORDFLOW_DATA_DIR": os.environ.get("NORDFLOW_DATA_DIR", str(REPO_ROOT / "data")),
            "PYTHONDONTWRITEBYTECODE": "1", **(extra_env or {})}
    return StdioServerParameters(command=sys.executable, args=["-m", "phase3.mcp_server"], cwd=str(REPO_ROOT), env=env)


class McpConnection:
    """One long-lived stdio connection to the demo MCP server."""

    def __init__(self):
        self._stack = AsyncExitStack()
        self.client = None
        self.tools = []

    async def start(self):
        self.client = await self._stack.enter_async_context(Client(server_params()))
        self.tools = (await self.client.list_tools()).tools
        return self

    async def close(self):
        await self._stack.aclose()

    async def call(self, name, arguments):
        """-> (ok, text). Tool errors come back as ok=False with the server's message."""
        try:
            res = await self.client.call_tool(name, arguments)
        except Exception as exc:  # transport-level failure
            return False, f"{type(exc).__name__}: {exc}"
        text = "\n".join(getattr(c, "text", "") for c in res.content)
        return not res.is_error, text

    async def call_json(self, name, arguments):
        ok, text = await self.call(name, arguments)
        if not ok:
            raise RuntimeError(text)
        return json.loads(text)


@dataclass
class ToolCall:
    seq: int
    tool: str
    arguments: dict
    system: str
    ok: bool | None = None
    error: str | None = None
    elapsed_ms: float | None = None
    result_chars: int | None = None

    def as_dict(self):
        return self.__dict__.copy()


@dataclass
class Turn:
    question: str
    started_at: str = field(default_factory=now)
    t0: float = field(default_factory=time.perf_counter)
    calls: list = field(default_factory=list)
    answer: dict | None = None
    fallback_text: str | None = None
    errors: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)

    def new_call(self, tool, arguments):
        call = ToolCall(len(self.calls) + 1, tool, arguments, system_of(tool))
        self.calls.append(call)
        return call


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=now)
    messages: list = field(default_factory=list)          # API agent: full message history
    pending_tool_results: list = field(default_factory=list)
    cli_session_id: str | None = None                     # CLI agent: Claude Code session
    cli_workdir: str | None = None
    turns: list = field(default_factory=list)             # rendered turns (for reload)
    systems_seen: set = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def finish_turn(conv, turn, agent_info):
    """Assemble the UI answer, check evidence against the systems actually queried, and log the turn."""
    turn.errors = [redact(e) for e in turn.errors]          # provider messages never reach the UI or the log raw
    for call in turn.calls:
        if call.error:
            call.error = redact(call.error)
    data_calls = [c for c in turn.calls if c.tool != "present_answer"]
    turn_systems = {c.system for c in data_calls if c.ok and c.system not in ("Metadata", "Other")}
    conv.systems_seen |= turn_systems
    answer = turn.answer or ({"headline": turn.fallback_text, "evidence": [], "key_points": [],
                              "follow_up_questions": []} if turn.fallback_text else None)
    if answer:
        for ev in answer.get("evidence", []):
            ev["verified_source"] = ev.get("system") in conv.systems_seen
        sources = sorted(turn_systems | {ev.get("system") for ev in answer.get("evidence", []) if ev.get("system")})
    else:
        sources = sorted(turn_systems)
    record = {
        "conversation_id": conv.id, "turn": len(conv.turns) + 1, "question": turn.question,
        "started_at": turn.started_at, "elapsed_s": round(time.perf_counter() - turn.t0, 1),
        "agent": agent_info, "answer": answer, "answer_structured": turn.answer is not None,
        "sources": sources, "tool_calls": [c.as_dict() for c in turn.calls],
        "tool_call_count": len(data_calls), "mcp_errors": [c.as_dict() for c in turn.calls if c.ok is False],
        "errors": turn.errors, "usage": turn.usage,
    }
    conv.turns.append(record)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"{conv.id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def truncate(text):
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return text[:MAX_TOOL_RESULT_CHARS] + f"\n... [truncated {len(text) - MAX_TOOL_RESULT_CHARS} characters; " \
                                          "narrow the query with filters or a lower limit]"
