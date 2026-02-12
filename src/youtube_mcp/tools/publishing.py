"""Video publishing tools — upload, update metadata, thumbnails, delete."""

import os

from googleapiclient.http import MediaFileUpload

from youtube_mcp.server import auth, mcp, quota


@mcp.tool()
def youtube_upload_video(
    file_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    publish_at: str | None = None,
) -> dict:
    """Upload a video to YouTube.

    Costs 1,600 quota units. Video is uploaded as private by default.

    Args:
        file_path: Absolute path to the video file
        title: Video title (max 100 characters)
        description: Video description (max 5,000 characters)
        tags: List of tags
        category_id: YouTube category ID (default "22" = People & Blogs)
        privacy_status: "private", "public", or "unlisted"
        publish_at: ISO 8601 datetime to schedule publishing (requires privacy_status="private")
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    quota.consume("video_insert")
    youtube = auth.build_youtube_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if publish_at and privacy_status == "private":
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(file_path, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = request.execute()

    return {
        "id": response["id"],
        "title": response["snippet"]["title"],
        "privacy": response["status"]["privacyStatus"],
        "publish_at": response["status"].get("publishAt"),
        "url": f"https://www.youtube.com/watch?v={response['id']}",
        "quota_cost": 1600,
    }


@mcp.tool()
def youtube_update_video(
    video_id: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    category_id: str | None = None,
    privacy_status: str | None = None,
) -> dict:
    """Update metadata for an existing video.

    Only provided fields are updated; others remain unchanged.

    Args:
        video_id: YouTube video ID
        title: New title (max 100 characters)
        description: New description (max 5,000 characters)
        tags: New tags (replaces existing tags)
        category_id: New category ID
        privacy_status: "private", "public", or "unlisted"
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    # Fetch current video data first
    current = youtube.videos().list(part="snippet,status", id=video_id).execute()
    items = current.get("items", [])
    if not items:
        return {"error": f"Video not found: {video_id}"}

    video = items[0]
    snippet = video["snippet"]
    status = video["status"]

    # Update only provided fields
    if title is not None:
        snippet["title"] = title[:100]
    if description is not None:
        snippet["description"] = description[:5000]
    if tags is not None:
        snippet["tags"] = tags
    if category_id is not None:
        snippet["categoryId"] = category_id

    body = {"id": video_id, "snippet": snippet}

    if privacy_status is not None:
        body["status"] = {"privacyStatus": privacy_status}
        parts = "snippet,status"
    else:
        parts = "snippet"

    quota.consume("update")
    response = youtube.videos().update(part=parts, body=body).execute()

    return {
        "id": response["id"],
        "title": response["snippet"]["title"],
        "privacy": response["status"]["privacyStatus"],
        "updated": True,
    }


@mcp.tool()
def youtube_set_thumbnail(video_id: str, file_path: str) -> dict:
    """Upload a custom thumbnail for a video.

    Args:
        video_id: YouTube video ID
        file_path: Absolute path to the thumbnail image (JPEG, PNG, GIF, BMP; max 2MB)
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    quota.consume("thumbnail_set")
    youtube = auth.build_youtube_service()

    media = MediaFileUpload(file_path)
    response = youtube.thumbnails().set(videoId=video_id, media_body=media).execute()

    items = response.get("items", [])
    if items:
        return {
            "video_id": video_id,
            "thumbnail_url": items[0].get("default", {}).get("url"),
            "updated": True,
        }

    return {"video_id": video_id, "updated": True}


@mcp.tool()
def youtube_delete_video(video_id: str) -> dict:
    """Delete a video. This action is irreversible.

    Args:
        video_id: YouTube video ID to delete
    """
    quota.consume("delete")
    youtube = auth.build_youtube_service()

    youtube.videos().delete(id=video_id).execute()

    return {"video_id": video_id, "deleted": True}
