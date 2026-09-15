"""
Agent via the OpenAI Responses API (requires OPENAI_API_KEY).

Same manual loop as api_agent.py: the model calls the demo MCP server's tools as
function tools, every call runs through the persistent MCP connection, and the
turn ends when the model calls present_answer.

Stateless on OpenAI's side (store=False): the conversation history is held in this
process, like the Anthropic agent's. Reasoning items are passed back in encrypted
form so the model keeps its own context across steps; they are never summarised,
shown or logged.
"""
import asyncio
import copy
import json
import time

import openai

from .base import finish_turn, truncate
from .prompt import SYSTEM_PROMPT

MAX_STEPS = 40
MAX_OUTPUT_TOKENS = 16000


def function_parameters(schema):
    """MCP input schema -> OpenAI function parameters: local $defs inlined, always an object with properties."""
    schema = copy.deepcopy(schema or {})
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/") and ref.split("/")[-1] in defs:
                merged = {**copy.deepcopy(defs[ref.split("/")[-1]]), **{k: v for k, v in node.items() if k != "$ref"}}
                return resolve(merged)
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    schema = resolve(schema)
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return schema


class OpenAIAgent:
    mode = "openai"

    def __init__(self, mcp, model, effort, client=None):
        self.mcp, self.model, self.effort = mcp, model, effort
        self.client = client or openai.AsyncOpenAI()
        self.tools = [{"type": "function", "name": t.name, "description": t.description or "",
                       "parameters": function_parameters(t.input_schema), "strict": False}
                      for t in sorted(mcp.tools, key=lambda t: t.name)]

    def info(self):
        return {"mode": self.mode, "model": self.model, "effort": self.effort}

    async def _run_call(self, turn, item, emit):
        try:
            arguments, parse_error = json.loads(item.arguments or "{}"), None
        except json.JSONDecodeError as exc:
            arguments, parse_error = None, f"Arguments were not valid JSON: {exc}"
        if not isinstance(arguments, dict):
            parse_error = parse_error or "Arguments must be a JSON object."
        call = turn.new_call(item.name, arguments if isinstance(arguments, dict) else {})
        await emit({"type": "tool_call", "seq": call.seq, "tool": call.tool, "system": call.system,
                    "arguments": call.arguments})
        t0 = time.perf_counter()
        if parse_error:
            ok, text = False, parse_error
        else:
            if item.name == "present_answer":
                turn.answer = dict(arguments)
            ok, text = await self.mcp.call(item.name, arguments)
        call.ok, call.elapsed_ms, call.result_chars = ok, round((time.perf_counter() - t0) * 1000, 1), len(text)
        if not ok:
            call.error = text[:500]
        await emit({"type": "tool_result", "seq": call.seq, "ok": ok, "error": call.error,
                    "elapsed_ms": call.elapsed_ms})
        # the Responses API has no error flag on function output, so failures are labelled in the text
        return {"type": "function_call_output", "call_id": item.call_id,
                "output": truncate(text) if ok else f"Tool error: {truncate(text)}"}

    def _add_usage(self, turn, usage):
        if usage is None:
            return
        details_in = getattr(usage, "input_tokens_details", None)
        details_out = getattr(usage, "output_tokens_details", None)
        for key, value in (("input_tokens", usage.input_tokens),
                           ("cached_input_tokens", getattr(details_in, "cached_tokens", 0)),
                           ("cache_write_tokens", getattr(details_in, "cache_write_tokens", 0)),
                           ("output_tokens", usage.output_tokens),
                           ("reasoning_tokens", getattr(details_out, "reasoning_tokens", 0))):
            turn.usage[key] = turn.usage.get(key, 0) + (value or 0)

    async def ask(self, conv, turn, emit):
        checkpoint = (len(conv.messages), list(conv.pending_tool_results))
        conv.messages.extend(conv.pending_tool_results + [{"role": "user", "content": turn.question}])
        conv.pending_tool_results = []

        def roll_back():  # keep the stored history valid for the next question
            del conv.messages[checkpoint[0]:]
            conv.pending_tool_results = checkpoint[1]

        for _ in range(MAX_STEPS):
            try:
                response = await self.client.responses.create(
                    model=self.model, instructions=SYSTEM_PROMPT, input=conv.messages, tools=self.tools,
                    reasoning={"effort": self.effort}, max_output_tokens=MAX_OUTPUT_TOKENS,
                    store=False, include=["reasoning.encrypted_content"],
                    prompt_cache_key=f"nordflow-{conv.id}")
            except openai.OpenAIError as exc:
                turn.errors.append(f"{type(exc).__name__}: {exc}")
                roll_back()
                break
            self._add_usage(turn, response.usage)
            if response.status in ("failed", "cancelled") or response.error:
                detail = getattr(response.error, "message", None) or response.status
                turn.errors.append(f"The model request failed: {detail}")
                roll_back()
                break

            output = list(response.output or [])
            conv.messages.extend(item.model_dump(mode="json", exclude_none=True) for item in output)
            refusals = [c.refusal for item in output if item.type == "message"
                        for c in item.content if c.type == "refusal"]
            if refusals:
                turn.errors.append("The model declined this request.")
                break
            calls = [item for item in output if item.type == "function_call"]
            if not calls:
                if response.status == "incomplete":
                    reason = getattr(response.incomplete_details, "reason", None) or "unknown reason"
                    turn.errors.append(f"The model stopped before finishing ({reason}).")
                turn.fallback_text = response.output_text.strip() or None
                break
            results = await asyncio.gather(*(self._run_call(turn, item, emit) for item in calls))
            if turn.answer is not None:
                conv.pending_tool_results = list(results)  # sent with the next question
                break
            conv.messages.extend(results)
        else:
            turn.errors.append(f"Stopped after {MAX_STEPS} model steps without an answer.")
        return finish_turn(conv, turn, self.info())
