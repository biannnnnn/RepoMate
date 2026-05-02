"""RepoMate MCP Server — repo analysis tools for the onboarding agent.

Provides 5 tools: repo_structure, repo_analyze_file, repo_find_tests,
repo_git_stats, repo_dependency_graph.

Usage:
    python -m repomate.server
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,  # stderr — never pollute stdout (stdio JSON-RPC protocol)
)
logger = logging.getLogger("repomate-server")

from repomate.tools.analyze import repo_analyze_file
from repomate.tools.deps import repo_dependency_graph
from repomate.tools.git_stats import repo_git_stats
from repomate.tools.structure import repo_structure
from repomate.tools.tests import repo_find_tests

# ── Tool definitions (used for list_tools and call_tool dispatch) ──────

TOOLS: dict[str, dict[str, Any]] = {
    "repo_structure": {
        "description": (
            "Generate an annotated directory tree of a repository. "
            "Classifies each file by type (source, test, config, documentation, etc.) "
            "and returns a markdown-formatted tree with per-directory file counts. "
            "Use this as the first step when analyzing an unfamiliar codebase."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository root directory",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory depth to traverse (default: 4)",
                    "default": 4,
                },
                "include_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns for files to include (default: common source files)",
                },
                "exclude_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns for directories to exclude (default: common noise dirs)",
                },
            },
            "required": ["repo_path"],
        },
        "handler": repo_structure,
    },
    "repo_analyze_file": {
        "description": (
            "Analyze a single source file and extract its structure. "
            "Returns imports, classes, methods, functions, and top-level constants "
            "with exact line numbers for every element. Supports Python (AST), "
            "TypeScript, JavaScript, Go, Rust, Java, Ruby, and more (regex fallback). "
            "Use this to deep-dive into key files after getting the repo structure. "
            "Every returned element includes line numbers — use them to cite code "
            "as file_path:line_number in your output."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to analyze",
                },
                "include_dependencies": {
                    "type": "boolean",
                    "description": "Whether to resolve and categorize internal/external dependencies",
                    "default": False,
                },
            },
            "required": ["file_path"],
        },
        "handler": repo_analyze_file,
    },
    "repo_find_tests": {
        "description": (
            "Locate test files, detect test frameworks, and identify untested source modules. "
            "Finds test files by naming convention (test_*.py, *.test.ts, etc.) and directory "
            "(names like tests/, __tests__/, spec/). Detects frameworks (pytest, jest, vitest, "
            "go test, junit, etc.) and provides test-to-source coverage assessment. "
            "Use this after architecture analysis to find test gaps and good first issues."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository root directory",
                },
                "framework_hint": {
                    "type": "string",
                    "description": "Optional test framework hint to prioritize (e.g., 'pytest', 'jest')",
                    "default": "auto",
                },
            },
            "required": ["repo_path"],
        },
        "handler": repo_find_tests,
    },
    "repo_git_stats": {
        "description": (
            "Analyze git history for code churn, hotspots, and contributor activity. "
            "Returns most-changed files (potential instability indicators), top contributors, "
            "commit frequency timeline, and recent branches. Flags high-churn files as "
            "potential bug areas. Use this when identifying risky code areas and understanding "
            "who to ask about specific modules."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository root directory",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to analyze (default: 90)",
                    "default": 90,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top entries per category (default: 20)",
                    "default": 20,
                },
            },
            "required": ["repo_path"],
        },
        "handler": repo_git_stats,
    },
    "repo_dependency_graph": {
        "description": (
            "Build an import dependency graph for a repository. "
            "Finds all source files, parses their imports/dependencies, and builds "
            "a directed graph. Computes centrality metrics (which modules are most "
            "depended upon), detects circular dependencies, and generates a Mermaid.js "
            "diagram. Use this after repo_structure to understand how modules relate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to the repository root directory",
                },
                "format": {
                    "type": "string",
                    "enum": ["mermaid", "json", "dot"],
                    "description": "Output format: 'mermaid' for Mermaid.js diagram, 'json' for raw data, 'dot' for Graphviz",
                    "default": "mermaid",
                },
                "depth": {
                    "type": "integer",
                    "description": "Max dependency resolution depth (default: 2)",
                    "default": 2,
                },
            },
            "required": ["repo_path"],
        },
        "handler": repo_dependency_graph,
    },
}


def _try_import_mcp() -> tuple[Any, Any, Any, Any] | None:
    """Attempt to import the MCP SDK. Returns (Server, types, stdio_server, Tool) or None."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types

        return Server, types, stdio_server, types.Tool
    except ImportError:
        pass
    try:
        # Older SDK paths
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server
        from mcp import types

        return Server, types, stdio_server, types.Tool
    except ImportError:
        pass
    return None


def _run_standalone() -> None:
    """Run a simple stdin/stdout JSON-RPC loop without the full MCP SDK.

    This fallback implements just enough of the MCP JSON-RPC protocol to be
    usable. It's not a full implementation — it handles initialize, tools/list,
    and tools/call. All other requests get an empty response.
    """
    logger.info("MCP SDK not available, running in standalone JSON-RPC mode")

    async def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "repo-analysis-mcp",
                        "version": "0.1.0",
                    },
                },
            }
        elif method == "notifications/initialized":
            return None  # No response for notifications
        elif method == "tools/list":
            tools_list = []
            for name, tool_def in TOOLS.items():
                tools_list.append({
                    "name": name,
                    "description": tool_def["description"],
                    "inputSchema": tool_def["inputSchema"],
                })
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools_list},
            }
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name not in TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                }

            try:
                handler = TOOLS[tool_name]["handler"]
                result = handler(**arguments)
                if asyncio.iscoroutine(result):
                    result = await result

                # Format result
                if isinstance(result, dict):
                    text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                else:
                    text = str(result)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                    },
                }
            except Exception as exc:
                logger.exception(f"Tool {tool_name} failed")
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exc}"}],
                        "isError": True,
                    },
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

    async def _main_loop():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            lambda: asyncio.streams.FlowControlMixin(), sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        buffer = ""
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode("utf-8").strip()
                if not line:
                    continue

                buffer += line
                try:
                    request = json.loads(buffer)
                    buffer = ""
                except json.JSONDecodeError:
                    continue

                response = await _handle_request(request)
                if response is not None:
                    resp_str = json.dumps(response, ensure_ascii=False) + "\n"
                    writer.write(resp_str.encode("utf-8"))
                    await writer.drain()
            except Exception:
                logger.exception("Error in main loop")
                break

    asyncio.run(_main_loop())


async def _run_mcp_sdk(Server, types, stdio_server) -> None:
    """Run the server using the full MCP SDK."""
    server = Server("repo-analysis-mcp")

    @server.list_tools()
    async def handle_list_tools() -> list:
        tools_list = []
        for name, tool_def in TOOLS.items():
            tools_list.append(
                types.Tool(
                    name=name,
                    description=tool_def["description"],
                    inputSchema=tool_def["inputSchema"],
                )
            )
        return tools_list

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        if name not in TOOLS:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            handler = TOOLS[name]["handler"]
            result = handler(**arguments)
            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, dict):
                text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            else:
                text = str(result)

            return [types.TextContent(type="text", text=text)]
        except Exception as exc:
            logger.exception(f"Tool {name} failed")
            return [types.TextContent(type="text", text=f"Error: {exc}")]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the MCP server."""
    mcp_imports = _try_import_mcp()
    if mcp_imports is not None:
        logger.info("Starting RepoMate MCP server (full SDK mode)")
        Server, types, stdio_server, _Tool = mcp_imports
        asyncio.run(_run_mcp_sdk(Server, types, stdio_server))
    else:
        logger.info("Starting RepoMate MCP server (standalone JSON-RPC mode)")
        _run_standalone()


if __name__ == "__main__":
    main()
