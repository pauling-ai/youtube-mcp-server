"""Response formatting utilities for LLM consumption."""

from datetime import timedelta


def format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to human-readable format."""
    if not iso_duration:
        return "unknown"
    s = iso_duration.replace("PT", "")
    hours = minutes = seconds = 0
    if "H" in s:
        hours, s = s.split("H")
        hours = int(hours)
    if "M" in s:
        minutes, s = s.split("M")
        minutes = int(minutes)
    if "S" in s:
        seconds = int(s.replace("S", ""))
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_count(n: int | str) -> str:
    """Format large numbers with K/M/B suffixes."""
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_video_summary(video: dict) -> dict:
    """Extract and format key fields from a YouTube Data API video resource."""
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    content = video.get("contentDetails", {})

    return {
        "id": video.get("id"),
        "title": snippet.get("title"),
        "channel": snippet.get("channelTitle"),
        "published_at": snippet.get("publishedAt"),
        "duration": format_duration(content.get("duration", "")),
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "description": snippet.get("description", "")[:500],
        "tags": snippet.get("tags", []),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        "is_short": _is_likely_short(content.get("duration", "")),
    }


def _is_likely_short(iso_duration: str) -> bool:
    """Heuristic: videos <= 60 seconds are likely Shorts."""
    if not iso_duration:
        return False
    s = iso_duration.replace("PT", "")
    total_seconds = 0
    if "H" in s:
        return False
    if "M" in s:
        minutes, s = s.split("M")
        total_seconds += int(minutes) * 60
    if "S" in s:
        total_seconds += int(s.replace("S", ""))
    return total_seconds <= 60
