"""FastMCP stdio server entry point for mcp-rag."""

from fastmcp import FastMCP

from src.mcp.register import register_tools

mcp = FastMCP("mcp-rag")
register_tools(mcp)


def main() -> None:
    """
    Run the MCP server over stdio (default FastMCP transport).
    """

    mcp.run()


if __name__ == "__main__":
    main()
