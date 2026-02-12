"""YouTube search and SEO discovery tools."""

import json
import urllib.request

from youtube_mcp.server import auth, mcp, quota
from youtube_mcp.utils.formatting import format_video_summary


@mcp.tool()
def youtube_search(
    query: str,
    search_type: str = "video",
    channel_id: str | None = None,
    max_results: int = 10,
    order: str = "relevance",
    published_after: str | None = None,
    published_before: str | None = None,
    region_code: str | None = None,
) -> dict:
    """Search YouTube for videos, channels, or playlists.

    Costs 100 quota units per call — use sparingly.

    Args:
        query: Search query string
        search_type: Type of results: "video", "channel", or "playlist"
        channel_id: Limit search to a specific channel
        max_results: Number of results (max 50)
        order: Sort order: "relevance", "date", "viewCount", "rating"
        published_after: ISO 8601 datetime (e.g., "2025-01-01T00:00:00Z")
        published_before: ISO 8601 datetime
        region_code: ISO 3166-1 alpha-2 country code (e.g., "US")
    """
    quota.consume("search")
    youtube = auth.build_youtube_service()

    params = {
        "part": "snippet",
        "q": query,
        "type": search_type,
        "maxResults": min(max_results, 50),
        "order": order,
    }

    if channel_id:
        params["channelId"] = channel_id
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before
    if region_code:
        params["regionCode"] = region_code

    response = youtube.search().list(**params).execute()

    results = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        result = {
            "title": snippet.get("title"),
            "description": snippet.get("description", "")[:200],
            "channel_title": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        }

        # Extract the right ID based on type
        id_info = item.get("id", {})
        if search_type == "video":
            result["video_id"] = id_info.get("videoId")
        elif search_type == "channel":
            result["channel_id"] = id_info.get("channelId")
        elif search_type == "playlist":
            result["playlist_id"] = id_info.get("playlistId")

        results.append(result)

    return {
        "results": results,
        "total_results": response.get("pageInfo", {}).get("totalResults", len(results)),
        "quota_cost": 100,
    }


@mcp.tool()
def youtube_search_suggestions(query: str, language: str = "en") -> dict:
    """Get YouTube autocomplete/search suggestions for a query.

    Useful for SEO keyword research — shows what people are searching for.
    No quota cost (uses YouTube's public suggest endpoint).

    Args:
        query: Partial search query to get suggestions for
        language: Language code (e.g., "en", "es")
    """
    url = (
        f"https://suggestqueries-clients6.youtube.com/complete/search"
        f"?client=youtube&ds=yt&q={urllib.request.quote(query)}&hl={language}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        resp = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        # Response is JSONP, strip the callback wrapper
        resp = resp[resp.index("(") + 1 : resp.rindex(")")]
        data = json.loads(resp)
        suggestions = [item[0] for item in data[1]]
    except Exception as e:
        return {"query": query, "error": f"Failed to fetch suggestions: {e}"}

    return {
        "query": query,
        "suggestions": suggestions,
    }


@mcp.tool()
def youtube_trending(
    region_code: str = "US",
    category_id: str | None = None,
    max_results: int = 10,
) -> dict:
    """Get currently trending videos on YouTube.

    Costs 1 quota unit.

    Args:
        region_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "IN")
        category_id: Filter by category ID (e.g., "28" for Science & Technology)
        max_results: Number of videos to return (max 50)
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
    }
    if category_id:
        params["videoCategoryId"] = category_id

    response = youtube.videos().list(**params).execute()

    videos = [format_video_summary(v) for v in response.get("items", [])]

    return {
        "region": region_code,
        "category_id": category_id,
        "videos": videos,
    }


@mcp.tool()
def youtube_get_categories(region_code: str = "US") -> dict:
    """List available YouTube video categories for a region.

    Useful for filtering trending videos or setting video category on upload.
    Costs 1 quota unit.

    Args:
        region_code: ISO 3166-1 alpha-2 country code (e.g., "US")
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    response = youtube.videoCategories().list(
        part="snippet", regionCode=region_code
    ).execute()

    categories = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        if snippet.get("assignable"):
            categories.append({
                "id": item["id"],
                "title": snippet["title"],
            })

    return {"region": region_code, "categories": categories}
