"""
Read-only MCP server for the NordFlow runtime (stdio transport).

    phase2/.venv/bin/python -m phase2.mcp.server

Thin layer: every tool is a query-layer operation registered as-is (its
signature and docstring become the tool schema and description). No business
logic lives here.
"""
import functools

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from phase2.runtime import Runtime

INSTRUCTIONS = (
    "Read-only access to NordFlow A/S business systems: ERP (finance), CRM (sales), payroll (people) and the "
    "identity mappings that link them. Systems use different ids and names for the same entities; use the "
    "identity_* tools to cross between them. Money is DKK unless a field says otherwise. Periods: '2026-H1', "
    "'2026-Q2', '2026-03', '2026', '2026-01..2026-08' or '2025-01-01..2025-06-30'. Start with "
    "meta_describe_sources and meta_get_semantics for definitions."
)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def _user_errors_visible(op):
    """Invalid parameters (ValueError from the query layer) go back to the caller as a readable tool error;
    anything else stays a generic server-side crash."""
    @functools.wraps(op)
    def tool(*args, **kwargs):
        try:
            return op(*args, **kwargs)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
    return tool


def build_server(data_dir=None):
    runtime = Runtime(data_dir)
    server = MCPServer("nordflow-business-data", instructions=INSTRUCTIONS, version="0.1.0")
    for name, op in runtime.operations().items():
        server.add_tool(_user_errors_visible(op), name=name, annotations=READ_ONLY)
    return server


def main():
    build_server().run("stdio")


if __name__ == "__main__":
    main()
