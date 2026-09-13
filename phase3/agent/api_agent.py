"""
Agent via the Anthropic API (requires ANTHROPIC_API_KEY or another SDK credential).

Manual agentic loop: Claude calls the demo MCP server's tools; every call is
executed through the persistent MCP connection. Conversation history is kept
per conversation, so follow-up questions have full context.
"""
import asyncio
import time

import anthropic

from .base import finish_turn, truncate
from .prompt import SYSTEM_PROMPT

MAX_STEPS = 40
BETAS = ["server-side-fallback-2026-07-01"]


class ApiAgent:
    mode = "api"

    def __init__(self, mcp, model, effort, client=None):
        self.mcp, self.model, self.effort = mcp, model, effort
        self.client = client or anthropic.AsyncAnthropic()
        self.tools = [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
                      for t in sorted(mcp.tools, key=lambda t: t.name)]

    def info(self):
        return {"mode": self.mode, "model": self.model, "effort": self.effort}

    async def _run_call(self, turn, block, emit):
        call = turn.new_call(block.name, dict(block.input))
        await emit({"type": "tool_call", "seq": call.seq, "tool": call.tool, "system": call.system,
                    "arguments": call.arguments})
        t0 = time.perf_counter()
        if block.name == "present_answer":
            turn.answer = dict(block.input)
        ok, text = await self.mcp.call(block.name, dict(block.input))
        call.ok, call.elapsed_ms, call.result_chars = ok, round((time.perf_counter() - t0) * 1000, 1), len(text)
        if not ok:
            call.error = text[:500]
        await emit({"type": "tool_result", "seq": call.seq, "ok": ok, "error": call.error,
                    "elapsed_ms": call.elapsed_ms})
        result = {"type": "tool_result", "tool_use_id": block.id, "content": truncate(text)}
        if not ok:
            result["is_error"] = True
        return result

    async def ask(self, conv, turn, emit):
        checkpoint = (len(conv.messages), list(conv.pending_tool_results))
        conv.messages.append({"role": "user", "content": conv.pending_tool_results + [{"type": "text", "text": turn.question}]})
        conv.pending_tool_results = []
        for _ in range(MAX_STEPS):
            try:
                response = await self.client.beta.messages.create(
                    model=self.model, max_tokens=16000, system=SYSTEM_PROMPT, tools=self.tools,
                    messages=conv.messages, thinking={"type": "adaptive"}, output_config={"effort": self.effort},
                    cache_control={"type": "ephemeral"}, betas=BETAS, fallbacks="default")
            except anthropic.APIError as exc:
                turn.errors.append(f"{type(exc).__name__}: {exc}")
                del conv.messages[checkpoint[0]:]              # roll back so the conversation stays valid
                conv.pending_tool_results = checkpoint[1]
                break
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                turn.usage[key] = turn.usage.get(key, 0) + (getattr(response.usage, key, 0) or 0)
            conv.messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason == "refusal":
                turn.errors.append("The model declined this request.")
                break
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                turn.fallback_text = "\n".join(b.text for b in response.content if b.type == "text").strip() or None
                break
            results = await asyncio.gather(*(self._run_call(turn, b, emit) for b in tool_uses))
            if turn.answer is not None:
                conv.pending_tool_results = list(results)  # sent with the next question
                break
            conv.messages.append({"role": "user", "content": list(results)})
        else:
            turn.errors.append(f"Stopped after {MAX_STEPS} model steps without an answer.")
        return finish_turn(conv, turn, self.info())
