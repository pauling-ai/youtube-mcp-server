"""Playlist management tools."""

from youtube_mcp.server import auth, mcp, quota


@mcp.tool()
def youtube_list_playlists(
    channel_id: str | None = None,
    mine: bool = False,
    max_results: int = 25,
) -> dict:
    """List playlists for a channel.

    Args:
        channel_id: Channel ID to list playlists from
        mine: If True, list the authenticated user's playlists
        max_results: Number of playlists to return. Values above 50 are
            served by paging through results; pass 0 or a negative value to
            fetch every playlist.
    """
    youtube = auth.build_youtube_service()
    target = max_results if (max_results and max_results > 0) else None

    base_params = {"part": "snippet,contentDetails"}
    if mine:
        base_params["mine"] = True
    elif channel_id:
        base_params["channelId"] = channel_id
    else:
        return {"error": "Provide channel_id or set mine=True"}

    playlists = []
    page_token = None
    response = {}
    while True:
        page_size = 50 if target is None else min(50, target - len(playlists))
        if page_size <= 0:
            break
        quota.consume("list")
        response = (
            youtube.playlists()
            .list(**base_params, maxResults=page_size, pageToken=page_token)
            .execute()
        )
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            playlists.append({
                "id": item["id"],
                "title": snippet.get("title"),
                "description": snippet.get("description", "")[:200],
                "published_at": snippet.get("publishedAt"),
                "video_count": item.get("contentDetails", {}).get("itemCount", 0),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            })
        page_token = response.get("nextPageToken")
        if not page_token:
            break
        if target is not None and len(playlists) >= target:
            break

    total = response.get("pageInfo", {}).get("totalResults", len(playlists))
    return {"playlists": playlists, "total": total}


@mcp.tool()
def youtube_create_playlist(
    title: str,
    description: str = "",
    privacy_status: str = "private",
) -> dict:
    """Create a new playlist.

    Args:
        title: Playlist title
        description: Playlist description
        privacy_status: "private", "public", or "unlisted"
    """
    quota.consume("insert")
    youtube = auth.build_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    response = youtube.playlists().insert(part="snippet,status", body=body).execute()

    return {
        "id": response["id"],
        "title": response["snippet"]["title"],
        "privacy": response["status"]["privacyStatus"],
        "url": f"https://www.youtube.com/playlist?list={response['id']}",
    }


@mcp.tool()
def youtube_add_to_playlist(playlist_id: str, video_id: str, position: int | None = None) -> dict:
    """Add a video to a playlist.

    Args:
        playlist_id: Playlist ID to add the video to
        video_id: Video ID to add
        position: Position in the playlist (0-based). Defaults to end.
    """
    quota.consume("insert")
    youtube = auth.build_youtube_service()

    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id,
            },
        },
    }
    if position is not None:
        body["snippet"]["position"] = position

    response = youtube.playlistItems().insert(part="snippet", body=body).execute()

    return {
        "playlist_item_id": response["id"],
        "playlist_id": playlist_id,
        "video_id": video_id,
        "position": response["snippet"].get("position"),
        "added": True,
    }


@mcp.tool()
def youtube_remove_from_playlist(playlist_item_id: str) -> dict:
    """Remove a video from a playlist.

    Use youtube_list_playlists or the Data API to find the playlist_item_id.

    Args:
        playlist_item_id: The playlist item ID (not the video ID)
    """
    quota.consume("delete")
    youtube = auth.build_youtube_service()

    youtube.playlistItems().delete(id=playlist_item_id).execute()

    return {"playlist_item_id": playlist_item_id, "removed": True}
