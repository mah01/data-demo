"""
Agent via the Claude Code CLI in headless mode (uses an existing `claude` login;
no API key needed). Same isolation as the Phase 2B runs (no built-in tools,
only the demo MCP server, no user/project settings), but the Claude Code session
is kept and resumed so follow-up questions have context.
"""
import asyncio
import json
import tempfile
import time
import uuid
from pathlib import Path

from .base import finish_turn, server_params
from .prompt import SYSTEM_PROMPT

SERVER_KEY = "nordflow"
PREFIX = f"mcp__{SERVER_KEY}__"
TIMEOUT_S = 900


def build_command(question, mcp_config, model, effort, session_id, resume):
    return ["claude", "-p", question, "--model", model, "--effort", effort,
            "--system-prompt", SYSTEM_PROMPT, "--tools", "",
            "--mcp-config", str(mcp_config), "--strict-mcp-config",
            "--allowedTools", f"mcp__{SERVER_KEY}", "--permission-mode", "dontAsk",
            "--setting-sources", "", "--disable-slash-commands",
            *(["--resume", session_id] if resume else ["--session-id", session_id]),
            "--output-format", "stream-json", "--verbose"]


class StreamParser:
    """Turns Claude Code stream-json events into turn records and UI events."""

    def __init__(self, turn):
        self.turn, self.pending, self.result = turn, {}, None

    def feed(self, line):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return []
        out = []
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    name = b.get("name", "").removeprefix(PREFIX)
                    call = self.turn.new_call(name, b.get("input", {}))
                    call._t0 = time.perf_counter()
                    self.pending[b.get("id")] = call
                    if name == "present_answer":
                        self.turn.answer = dict(b.get("input", {}))
                    out.append({"type": "tool_call", "seq": call.seq, "tool": name, "system": call.system,
                                "arguments": call.arguments})
        elif ev.get("type") == "user":
            content = ev.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                call = self.pending.pop(b.get("tool_use_id"), None) if b.get("type") == "tool_result" else None
                if call is None:
                    continue
                c = b.get("content")
                text = c if isinstance(c, str) else "\n".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                call.ok, call.result_chars = not b.get("is_error"), len(text)
                call.elapsed_ms = round((time.perf_counter() - call.__dict__.pop("_t0")) * 1000, 1)
                call.error = None if call.ok else text[:500]
                out.append({"type": "tool_result", "seq": call.seq, "ok": call.ok, "error": call.error,
                            "elapsed_ms": call.elapsed_ms})
        elif ev.get("type") == "result":
            self.result = ev
        return out


class CliAgent:
    mode = "cli"

    def __init__(self, model, effort):
        self.model, self.effort = model, effort

    def info(self):
        return {"mode": self.mode, "model": self.model, "effort": self.effort}

    async def ask(self, conv, turn, emit):
        resume = conv.cli_session_id is not None
        if not resume:
            conv.cli_session_id = str(uuid.uuid4())
            conv.cli_workdir = tempfile.mkdtemp(prefix=f"nordflow-demo-{conv.id}-")
        params = server_params()
        config = Path(conv.cli_workdir) / "mcp.json"
        config.write_text(json.dumps({"mcpServers": {SERVER_KEY: {
            "command": params.command, "args": params.args, "env": {k: params.env[k] for k in
                                                                    ("PYTHONPATH", "NORDFLOW_DATA_DIR", "PYTHONDONTWRITEBYTECODE")}}}}))
        proc = await asyncio.create_subprocess_exec(
            *build_command(turn.question, config, self.model, self.effort, conv.cli_session_id, resume),
            cwd=conv.cli_workdir, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024)
        parser = StreamParser(turn)
        try:
            async with asyncio.timeout(TIMEOUT_S):
                async for raw in proc.stdout:
                    for event in parser.feed(raw.decode("utf-8", "replace")):
                        await emit(event)
                await proc.wait()
        except TimeoutError:
            proc.kill()
            turn.errors.append(f"Timed out after {TIMEOUT_S}s.")
        if proc.returncode not in (0, None):
            err = (await proc.stderr.read()).decode("utf-8", "replace").strip()
            turn.errors.append(f"claude exited with code {proc.returncode}: {err[-500:]}")
        res = parser.result or {}
        if res.get("is_error"):
            turn.errors.append(f"Agent error: {res.get('subtype')} {str(res.get('result'))[:300]}")
        if turn.answer is None and res.get("result"):
            turn.fallback_text = res["result"]
        u = res.get("usage") or {}
        turn.usage = {k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                             "cache_creation_input_tokens")}
        turn.usage["total_cost_usd"] = res.get("total_cost_usd")
        return finish_turn(conv, turn, self.info())
