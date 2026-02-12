# YouTube MCP Server

A comprehensive [Model Context Protocol](https://modelcontextprotocol.io/) server for the YouTube Data API v3, Analytics API, and Reporting API. Gives AI assistants full access to your YouTube channel — analytics, video management, comments, and more.

**40 tools** covering:
- Channel & video data
- YouTube Analytics (performance, audience, retention, revenue)
- Video publishing & playlist management
- Transcript extraction
- YouTube SEO (search suggestions, trending)
- Comments
- Bulk reporting

## Why This Server?

Existing YouTube MCP servers focus narrowly on transcript scraping or basic search. This server covers **three YouTube APIs** and is the only open-source MCP server that provides:

- **YouTube Analytics API** — channel performance, top videos/Shorts, audience retention curves, traffic sources, demographics, revenue, day-of-week analysis
- **YouTube Reporting API** — schedule and download bulk CSV reports
- **Full Data API coverage** — not just read, but also upload videos, manage playlists, post comments, set thumbnails
- **YouTube SEO tools** — autocomplete suggestions, trending videos, category discovery
- **Dual transcript strategy** — official captions API for your own videos, `youtube-transcript-api` fallback for any public video
- **Quota tracking** — client-side tracking with hard-fail protection so you don't silently exhaust your daily quota

| Feature | This server | Others |
|---------|------------|--------|
| Analytics API (watch time, retention, CTR) | Yes | No |
| Reporting API (bulk CSV exports) | Yes | No |
| Video upload & management | Yes | Rare |
| Playlist management | Yes | Rare |
| Comments (read + write) | Yes | No |
| SEO / trending / suggestions | Yes | No |
| Transcript extraction | Yes | Yes |
| Quota tracking | Yes | No |
| Total tools | 40 | 1-5 |

## Prerequisites

- Python 3.11+
- A Google Cloud project with YouTube APIs enabled
- OAuth 2.0 credentials

## Google Cloud Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)

### 2. Enable APIs

Enable all three APIs in **APIs & Services > Library**:

- **YouTube Data API v3**
- **YouTube Analytics API**
- **YouTube Reporting API**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Set User Type to **External**
3. Fill in the app name and required fields
4. Add the Google account that **owns** your YouTube channel as a **test user**

> **Important:** You must sign in with the Google account that **owns** the YouTube channel, not a manager. Only the owner account can access Analytics data.

### 4. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON file
5. Save it as `~/.youtube-mcp/client_secret.json`

Alternatively, set the `YOUTUBE_MCP_CLIENT_SECRET` environment variable to the path of your credentials file.

## Installation

```bash
pip install youtube-studio-mcp
```

Or with uv:

```bash
uv pip install youtube-studio-mcp
```

## MCP Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "youtube-studio-mcp"
    }
  }
}
```

### Claude Code

Add to your MCP settings:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "youtube-studio-mcp"
    }
  }
}
```

### With environment variables

```json
{
  "mcpServers": {
    "youtube": {
      "command": "youtube-studio-mcp",
      "env": {
        "YOUTUBE_MCP_CLIENT_SECRET": "/path/to/client_secret.json",
        "YOUTUBE_API_KEY": "your-api-key-for-public-data"
      }
    }
  }
}
```

## First Run

On first use, the server will open a browser window for Google OAuth consent. Sign in with the account that owns your YouTube channel and grant the requested permissions. The token is saved to `~/.youtube-mcp/token.json` and auto-refreshes.

## Tools Reference

### Auth & Setup (2 tools)

| Tool | Description |
|------|-------------|
| `youtube_auth` | Initiate OAuth 2.0 flow |
| `youtube_auth_status` | Check auth state and quota usage |

### Channel & Video (3 tools)

| Tool | Description |
|------|-------------|
| `youtube_get_channel` | Get channel details by ID, handle, or `mine=True` |
| `youtube_list_videos` | List videos from a channel or playlist |
| `youtube_get_video` | Get detailed video metadata and stats |

### Search & SEO (4 tools)

| Tool | Description |
|------|-------------|
| `youtube_search` | Search YouTube (100 quota units per call) |
| `youtube_search_suggestions` | Get autocomplete suggestions (no quota cost) |
| `youtube_trending` | Get trending videos by region/category |
| `youtube_get_categories` | List video categories for a region |

### Transcripts (2 tools)

| Tool | Description |
|------|-------------|
| `youtube_get_transcript` | Get video transcript (official API or scraping fallback) |
| `youtube_list_captions` | List caption tracks for own videos |

### Analytics — Performance (4 tools)

| Tool | Description |
|------|-------------|
| `youtube_analytics_overview` | Channel summary (views, watch time, subs, likes) |
| `youtube_analytics_top_videos` | Top videos by views (excludes Shorts) |
| `youtube_analytics_top_shorts` | Top Shorts by views |
| `youtube_analytics_video_detail` | Daily metrics for a specific video |

### Analytics — Audience (3 tools)

| Tool | Description |
|------|-------------|
| `youtube_analytics_traffic_sources` | Traffic source breakdown |
| `youtube_analytics_demographics` | Age and gender breakdown |
| `youtube_analytics_geography` | Views by country |

### Analytics — Schedule & Reach (3 tools)

| Tool | Description |
|------|-------------|
| `youtube_analytics_daily` | Daily performance over time |
| `youtube_analytics_day_of_week` | Average performance by weekday |
| `youtube_analytics_content_type_breakdown` | Shorts vs long-form vs live comparison |

### Analytics — Revenue & Retention (3 tools)

| Tool | Description |
|------|-------------|
| `youtube_analytics_revenue` | Revenue breakdown (requires YouTube Partner Program) |
| `youtube_analytics_revenue_by_video` | Per-video revenue |
| `youtube_analytics_retention` | Audience retention curve for a video |

### Publishing (4 tools)

| Tool | Description |
|------|-------------|
| `youtube_upload_video` | Upload a video (1,600 quota units) |
| `youtube_update_video` | Update video metadata |
| `youtube_set_thumbnail` | Upload custom thumbnail |
| `youtube_delete_video` | Delete a video |

### Playlists (4 tools)

| Tool | Description |
|------|-------------|
| `youtube_list_playlists` | List playlists for a channel |
| `youtube_create_playlist` | Create a new playlist |
| `youtube_add_to_playlist` | Add a video to a playlist |
| `youtube_remove_from_playlist` | Remove a video from a playlist |

### Comments (3 tools)

| Tool | Description |
|------|-------------|
| `youtube_list_comments` | List comments on a video |
| `youtube_post_comment` | Post a top-level comment |
| `youtube_reply_to_comment` | Reply to a comment |

### Bulk Reporting (5 tools)

| Tool | Description |
|------|-------------|
| `youtube_reporting_list_types` | List available report types |
| `youtube_reporting_create_job` | Schedule a daily report job |
| `youtube_reporting_list_jobs` | List active reporting jobs |
| `youtube_reporting_list_reports` | List generated reports for a job |
| `youtube_reporting_download` | Download a report CSV |

## Quota Management

The YouTube Data API v3 has a default daily quota of **10,000 units**. This server tracks quota usage client-side and **hard-fails** when the quota is exhausted.

Key costs:
- Most read operations: **1 unit**
- Search: **100 units**
- Write operations: **50 units**
- Video upload: **1,600 units**

Use `youtube_auth_status` to check current quota usage.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `YOUTUBE_MCP_CLIENT_SECRET` | Path to `client_secret.json` |
| `YOUTUBE_MCP_CONFIG_DIR` | Config directory (default: `~/.youtube-mcp`) |
| `YOUTUBE_API_KEY` | API key for public-only operations |

## Development

```bash
git clone https://github.com/pauling-ai/youtube-studio-mcp.git
cd youtube-studio-mcp
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -v
```

## License

MIT
