"""YouTube MCP Server — FastMCP entry point."""

import os

from mcp.server.fastmcp import FastMCP

from youtube_mcp.auth import YouTubeAuth
from youtube_mcp.utils.quota import QuotaTracker

mcp = FastMCP(
    "YouTube MCP Server",
    instructions="Comprehensive MCP server for YouTube Data API, Analytics API, and Reporting API",
)

# Shared state
auth = YouTubeAuth(
    client_secret_path=os.environ.get("YOUTUBE_MCP_CLIENT_SECRET"),
    config_dir=os.environ.get("YOUTUBE_MCP_CONFIG_DIR"),
    api_key=os.environ.get("YOUTUBE_API_KEY"),
)
quota = QuotaTracker()


# --- Auth tools ---


@mcp.tool()
def youtube_auth() -> dict:
    """Initiate OAuth 2.0 authentication flow.

    Opens a browser window for Google OAuth consent. Required before using
    any tools that access private channel data or analytics.
    """
    try:
        auth.authenticate()
        return {"status": "authenticated", "detail": auth.status()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@mcp.tool()
def youtube_auth_status() -> dict:
    """Check current authentication status and quota usage."""
    return {
        "auth": auth.status(),
        "quota": quota.status(),
    }


# --- Register tool modules ---
# Import tool modules so their @mcp.tool() decorators run

from youtube_mcp.tools import channel  # noqa: E402, F401
from youtube_mcp.tools import search  # noqa: E402, F401
from youtube_mcp.tools import transcripts  # noqa: E402, F401
from youtube_mcp.tools import analytics  # noqa: E402, F401
from youtube_mcp.tools import publishing  # noqa: E402, F401
from youtube_mcp.tools import playlists  # noqa: E402, F401
from youtube_mcp.tools import comments  # noqa: E402, F401
from youtube_mcp.tools import reporting  # noqa: E402, F401


def main():
    mcp.run()


if __name__ == "__main__":
    main()
