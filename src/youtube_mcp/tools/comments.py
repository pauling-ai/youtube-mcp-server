"""Comment tools — list, post, and reply to comments."""

from youtube_mcp.server import auth, mcp, quota


@mcp.tool()
def youtube_list_comments(
    video_id: str,
    max_results: int = 20,
    order: str = "relevance",
) -> dict:
    """List top-level comments on a video.

    Args:
        video_id: YouTube video ID
        max_results: Number of comment threads to return (max 100)
        order: Sort order: "relevance" or "time"
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    response = (
        youtube.commentThreads()
        .list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_results, 100),
            order=order,
        )
        .execute()
    )

    comments = []
    for item in response.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "comment_id": item["snippet"]["topLevelComment"]["id"],
            "thread_id": item["id"],
            "author": top.get("authorDisplayName"),
            "text": top.get("textDisplay"),
            "likes": top.get("likeCount", 0),
            "published_at": top.get("publishedAt"),
            "reply_count": item["snippet"].get("totalReplyCount", 0),
        })

    return {
        "video_id": video_id,
        "comments": comments,
        "total": len(comments),
    }


@mcp.tool()
def youtube_post_comment(video_id: str, text: str) -> dict:
    """Post a new top-level comment on a video.

    Args:
        video_id: YouTube video ID to comment on
        text: Comment text
    """
    quota.consume("insert")
    youtube = auth.build_youtube_service()

    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": text,
                },
            },
        },
    }

    response = youtube.commentThreads().insert(part="snippet", body=body).execute()

    top = response["snippet"]["topLevelComment"]["snippet"]
    return {
        "comment_id": response["snippet"]["topLevelComment"]["id"],
        "thread_id": response["id"],
        "text": top.get("textDisplay"),
        "video_id": video_id,
        "posted": True,
    }


@mcp.tool()
def youtube_reply_to_comment(parent_id: str, text: str) -> dict:
    """Reply to an existing comment.

    Args:
        parent_id: The comment ID to reply to (from youtube_list_comments)
        text: Reply text
    """
    quota.consume("insert")
    youtube = auth.build_youtube_service()

    body = {
        "snippet": {
            "parentId": parent_id,
            "textOriginal": text,
        },
    }

    response = youtube.comments().insert(part="snippet", body=body).execute()

    return {
        "reply_id": response["id"],
        "parent_id": parent_id,
        "text": response["snippet"].get("textDisplay"),
        "posted": True,
    }
