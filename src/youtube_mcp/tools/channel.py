"""Channel and video read tools."""

from youtube_mcp.server import auth, mcp, quota
from youtube_mcp.utils.formatting import format_video_summary


@mcp.tool()
def youtube_get_channel(
    channel_id: str | None = None,
    handle: str | None = None,
    mine: bool = False,
) -> dict:
    """Get channel details by channel ID, handle (@username), or the authenticated user's channel.

    Args:
        channel_id: YouTube channel ID (e.g., "UCxxxxxxx")
        handle: Channel handle (e.g., "@mkbhd")
        mine: If True, get the authenticated user's own channel
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    params = {"part": "snippet,statistics,contentDetails,brandingSettings"}
    if mine:
        params["mine"] = True
    elif handle:
        params["forHandle"] = handle
    elif channel_id:
        params["id"] = channel_id
    else:
        return {"error": "Provide channel_id, handle, or set mine=True"}

    response = youtube.channels().list(**params).execute()
    items = response.get("items", [])
    if not items:
        return {"error": "Channel not found"}

    ch = items[0]
    snippet = ch.get("snippet", {})
    stats = ch.get("statistics", {})

    return {
        "id": ch["id"],
        "title": snippet.get("title"),
        "handle": snippet.get("customUrl"),
        "description": snippet.get("description", "")[:500],
        "published_at": snippet.get("publishedAt"),
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        "uploads_playlist_id": (
            ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        ),
    }


@mcp.tool()
def youtube_list_videos(
    channel_id: str | None = None,
    playlist_id: str | None = None,
    mine: bool = False,
    max_results: int = 20,
) -> dict:
    """List videos from a channel or playlist.

    For a channel, uses the channel's uploads playlist. Returns video summaries
    with stats, sorted by most recent.

    Args:
        channel_id: Channel ID to list videos from
        playlist_id: Playlist ID to list videos from (overrides channel_id)
        mine: If True, list the authenticated user's videos
        max_results: Number of videos to return. Values above 50 are served by
            paging through the playlist; pass 0 or a negative value to fetch
            every video in the playlist.
    """
    youtube = auth.build_youtube_service()
    target = max_results if (max_results and max_results > 0) else None

    # Resolve uploads playlist if needed
    if not playlist_id:
        quota.consume("list")
        ch_params = {"part": "contentDetails"}
        if mine:
            ch_params["mine"] = True
        elif channel_id:
            ch_params["id"] = channel_id
        else:
            return {"error": "Provide channel_id, playlist_id, or set mine=True"}

        ch_response = youtube.channels().list(**ch_params).execute()
        ch_items = ch_response.get("items", [])
        if not ch_items:
            return {"error": "Channel not found"}
        playlist_id = (
            ch_items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        )

    if not playlist_id:
        return {"error": "Could not resolve uploads playlist"}

    video_ids = []
    pi_map = {}
    page_token = None
    pl_response = {}
    while True:
        page_size = 50 if target is None else min(50, target - len(video_ids))
        if page_size <= 0:
            break
        quota.consume("list")
        pl_response = (
            youtube.playlistItems()
            .list(part="contentDetails", playlistId=playlist_id, maxResults=page_size, pageToken=page_token)
            .execute()
        )
        for _it in pl_response.get("items", []):
            _v = _it["contentDetails"]["videoId"]
            video_ids.append(_v)
            pi_map[_v] = _it["id"]
        page_token = pl_response.get("nextPageToken")
        if not page_token:
            break
        if target is not None and len(video_ids) >= target:
            break
    total = pl_response.get("pageInfo", {}).get("totalResults", len(video_ids))
    if not video_ids:
        return {"videos": [], "total": total}
    videos = []
    for i in range(0, len(video_ids), 50):
        quota.consume("list")
        chunk = video_ids[i : i + 50]
        videos_response = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(chunk))
            .execute()
        )
        for _vv in videos_response.get("items", []):
            _summ = format_video_summary(_vv)
            _summ["playlist_item_id"] = pi_map.get(_summ.get("id"))
            videos.append(_summ)
    return {"videos": videos, "total": total}


@mcp.tool()
def youtube_get_video(video_id: str) -> dict:
    """Get detailed metadata and statistics for a specific video.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    response = (
        youtube.videos()
        .list(part="snippet,statistics,contentDetails,status,topicDetails", id=video_id)
        .execute()
    )

    items = response.get("items", [])
    if not items:
        return {"error": f"Video not found: {video_id}"}

    video = items[0]
    summary = format_video_summary(video)

    # Add extra detail fields not in the summary
    status = video.get("status", {})
    summary["privacy"] = status.get("privacyStatus")
    summary["publish_at"] = status.get("publishAt")
    summary["license"] = status.get("license")
    summary["embeddable"] = status.get("embeddable")
    summary["topic_categories"] = video.get("topicDetails", {}).get("topicCategories", [])

    return summary
