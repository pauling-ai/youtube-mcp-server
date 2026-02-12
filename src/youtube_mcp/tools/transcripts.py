"""Transcript and caption tools.

Uses two strategies:
- Official YouTube Data API captions endpoint for own videos (requires OAuth)
- youtube-transcript-api library for public/competitor videos (scraping, no auth needed)
"""

from youtube_mcp.server import auth, mcp, quota


@mcp.tool()
def youtube_list_captions(video_id: str) -> dict:
    """List available caption tracks for a video you own.

    Requires OAuth. Only works for videos on the authenticated user's channel.

    Args:
        video_id: YouTube video ID
    """
    quota.consume("list")
    youtube = auth.build_youtube_service()

    response = youtube.captions().list(part="snippet", videoId=video_id).execute()

    tracks = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        tracks.append({
            "id": item["id"],
            "language": snippet.get("language"),
            "name": snippet.get("name"),
            "track_kind": snippet.get("trackKind"),
            "is_auto_synced": snippet.get("isAutoSynced"),
            "is_draft": snippet.get("isDraft"),
            "last_updated": snippet.get("lastUpdated"),
        })

    return {"video_id": video_id, "tracks": tracks}


@mcp.tool()
def youtube_get_transcript(
    video_id: str,
    language: str = "en",
    use_official_api: bool = False,
) -> dict:
    """Get the transcript/captions for a video.

    By default uses youtube-transcript-api (works for any public video, no quota cost).
    Set use_official_api=True to use the official Data API (only for your own videos,
    costs quota units).

    Args:
        video_id: YouTube video ID
        language: Preferred language code (e.g., "en", "es", "ja")
        use_official_api: If True, use official API (own videos only)
    """
    if use_official_api:
        return _get_transcript_official(video_id, language)
    return _get_transcript_scraping(video_id, language)


def _get_transcript_scraping(video_id: str, language: str) -> dict:
    """Get transcript using youtube-transcript-api (public videos)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to find the requested language, fall back to auto-generated
            try:
                transcript = transcript_list.find_transcript([language])
            except Exception:
                # Fall back to any available transcript
                transcript = next(iter(transcript_list))
                if transcript.language_code != language:
                    try:
                        transcript = transcript.translate(language)
                    except Exception:
                        pass  # Use whatever we have

            entries = transcript.fetch()
            segments = []
            full_text_parts = []
            for entry in entries:
                segments.append({
                    "text": entry.get("text", entry.text if hasattr(entry, "text") else str(entry)),
                    "start": entry.get("start", getattr(entry, "start", 0)),
                    "duration": entry.get("duration", getattr(entry, "duration", 0)),
                })
                full_text_parts.append(
                    entry.get("text", entry.text if hasattr(entry, "text") else str(entry))
                )

            return {
                "video_id": video_id,
                "language": transcript.language_code,
                "is_generated": transcript.is_generated,
                "source": "youtube-transcript-api",
                "full_text": " ".join(full_text_parts),
                "segments": segments,
            }
        except Exception as e:
            return {
                "video_id": video_id,
                "error": f"Could not fetch transcript: {e}",
                "source": "youtube-transcript-api",
            }
    except ImportError:
        return {
            "error": "youtube-transcript-api is not installed. "
            "Install it with: pip install youtube-transcript-api",
        }


def _get_transcript_official(video_id: str, language: str) -> dict:
    """Get transcript using official YouTube Data API (own videos only)."""
    quota.consume("list")
    youtube = auth.build_youtube_service()

    # First, list captions to find the right track
    response = youtube.captions().list(part="snippet", videoId=video_id).execute()

    target_caption = None
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        if snippet.get("language") == language:
            target_caption = item
            break

    if not target_caption:
        items = response.get("items", [])
        if items:
            target_caption = items[0]
        else:
            return {"video_id": video_id, "error": "No captions found"}

    # Download the caption track
    quota.consume("list")  # caption download costs vary
    caption_text = (
        youtube.captions().download(id=target_caption["id"], tfmt="srt").execute()
    )

    text = caption_text.decode("utf-8") if isinstance(caption_text, bytes) else caption_text

    return {
        "video_id": video_id,
        "language": target_caption["snippet"].get("language"),
        "track_kind": target_caption["snippet"].get("trackKind"),
        "source": "official_api",
        "full_text": text,
    }
