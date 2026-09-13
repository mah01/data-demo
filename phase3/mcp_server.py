"""
MCP server used by the demo: the Phase 2A read-only tools (same runtime,
names, descriptions and error handling), plus `present_answer`, which only
echoes the agent's structured answer back so the UI can render it.

    phase2/.venv/bin/python -m phase3.mcp_server
"""
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from phase2.mcp.server import INSTRUCTIONS, READ_ONLY, _user_errors_visible
from phase2.runtime import Runtime

from .agent.prompt import PRESENT_ANSWER_DESCRIPTION

PRESENT_ANSWER = "present_answer"


class Evidence(BaseModel):
    metric: str = Field(description="e.g. 'German revenue'")
    value: str = Field(description="e.g. '-8% (22.0M -> 20.2M DKK)'")
    system: Literal["ERP", "CRM", "Payroll", "Mappings"] = Field(description="Source system of the figure")
    period: str | None = Field(default=None, description="e.g. 'H1 2026 vs H1 2025'")


def present_answer(headline: str = Field(description="2-4 sentence executive conclusion"),
                   evidence: list[Evidence] = Field(description="3-7 supporting figures from tool results"),
                   key_points: list[str] = Field(default_factory=list, description="At most 4 short bullets"),
                   follow_up_questions: list[str] = Field(default_factory=list,
                                                          description="Up to 3 natural next questions")) -> str:
    return "Answer delivered to the executive."


def build_server(data_dir=None):
    server = MCPServer("nordflow-business-data", instructions=INSTRUCTIONS, version="0.2.0")
    for name, op in Runtime(data_dir).operations().items():
        server.add_tool(_user_errors_visible(op), name=name, annotations=READ_ONLY)
    server.add_tool(present_answer, name=PRESENT_ANSWER, description=PRESENT_ANSWER_DESCRIPTION,
                    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False))
    return server


if __name__ == "__main__":
    build_server().run("stdio")
