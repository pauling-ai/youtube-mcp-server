"""Tests for tool functions with mocked YouTube API responses."""

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_youtube():
    """Create a mock YouTube Data API service."""
    return MagicMock()


def _make_video_resource(
    video_id="abc123",
    title="Test Video",
    views=1000,
    likes=50,
    comments=10,
    duration="PT5M30S",
):
    """Create a mock YouTube video resource."""
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "channelTitle": "Test Channel",
            "publishedAt": "2025-01-01T00:00:00Z",
            "description": "Test description",
            "tags": ["test"],
            "thumbnails": {"high": {"url": f"https://i.ytimg.com/vi/{video_id}/hq.jpg"}},
        },
        "statistics": {
            "viewCount": str(views),
            "likeCount": str(likes),
            "commentCount": str(comments),
        },
        "contentDetails": {"duration": duration},
        "status": {
            "privacyStatus": "public",
            "license": "youtube",
            "embeddable": True,
        },
        "topicDetails": {"topicCategories": []},
    }


class TestGetVideo:
    @patch("youtube_mcp.tools.channel.auth")
    @patch("youtube_mcp.tools.channel.quota")
    def test_get_video_found(self, mock_quota, mock_auth):
        from youtube_mcp.tools.channel import youtube_get_video

        mock_yt = _make_mock_youtube()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.videos().list().execute.return_value = {
            "items": [_make_video_resource(video_id="xyz")]
        }

        result = youtube_get_video("xyz")
        assert result["id"] == "xyz"
        assert result["title"] == "Test Video"
        assert result["views"] == 1000
        assert result["privacy"] == "public"
        mock_quota.consume.assert_called_once_with("list")

    @patch("youtube_mcp.tools.channel.auth")
    @patch("youtube_mcp.tools.channel.quota")
    def test_get_video_not_found(self, mock_quota, mock_auth):
        from youtube_mcp.tools.channel import youtube_get_video

        mock_yt = _make_mock_youtube()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.videos().list().execute.return_value = {"items": []}

        result = youtube_get_video("nonexistent")
        assert "error" in result


class TestGetChannel:
    @patch("youtube_mcp.tools.channel.auth")
    @patch("youtube_mcp.tools.channel.quota")
    def test_get_channel_by_handle(self, mock_quota, mock_auth):
        from youtube_mcp.tools.channel import youtube_get_channel

        mock_yt = _make_mock_youtube()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.channels().list().execute.return_value = {
            "items": [{
                "id": "UC123",
                "snippet": {
                    "title": "My Channel",
                    "customUrl": "@mychannel",
                    "description": "A channel",
                    "publishedAt": "2020-01-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "10000",
                    "viewCount": "500000",
                    "videoCount": "100",
                },
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UU123"},
                },
            }]
        }

        result = youtube_get_channel(handle="@mychannel")
        assert result["id"] == "UC123"
        assert result["subscribers"] == 10000
        assert result["uploads_playlist_id"] == "UU123"

    @patch("youtube_mcp.tools.channel.auth")
    @patch("youtube_mcp.tools.channel.quota")
    def test_get_channel_no_args(self, mock_quota, mock_auth):
        from youtube_mcp.tools.channel import youtube_get_channel

        result = youtube_get_channel()
        assert "error" in result


class TestSearch:
    @patch("youtube_mcp.tools.search.auth")
    @patch("youtube_mcp.tools.search.quota")
    def test_search_videos(self, mock_quota, mock_auth):
        from youtube_mcp.tools.search import youtube_search

        mock_yt = _make_mock_youtube()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.search().list().execute.return_value = {
            "items": [{
                "id": {"videoId": "vid1"},
                "snippet": {
                    "title": "Found Video",
                    "description": "A result",
                    "channelTitle": "Some Channel",
                    "publishedAt": "2025-06-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                },
            }],
            "pageInfo": {"totalResults": 1},
        }

        result = youtube_search("test query")
        assert len(result["results"]) == 1
        assert result["results"][0]["video_id"] == "vid1"
        assert result["quota_cost"] == 100
        mock_quota.consume.assert_called_once_with("search")


class TestAnalytics:
    @patch("youtube_mcp.tools.analytics.auth")
    def test_analytics_overview(self, mock_auth):
        from youtube_mcp.tools.analytics import youtube_analytics_overview

        mock_analytics = MagicMock()
        mock_auth.build_youtube_analytics_service.return_value = mock_analytics
        mock_analytics.reports().query().execute.return_value = {
            "columnHeaders": [
                {"name": "views"},
                {"name": "estimatedMinutesWatched"},
            ],
            "rows": [[5000, 12000]],
        }

        result = youtube_analytics_overview()
        assert result["results"][0]["views"] == 5000
        assert result["results"][0]["estimatedMinutesWatched"] == 12000

    @patch("youtube_mcp.tools.analytics.auth")
    def test_analytics_top_shorts(self, mock_auth):
        from youtube_mcp.tools.analytics import youtube_analytics_top_shorts

        mock_analytics = MagicMock()
        mock_auth.build_youtube_analytics_service.return_value = mock_analytics
        mock_analytics.reports().query().execute.return_value = {
            "columnHeaders": [
                {"name": "video"},
                {"name": "views"},
            ],
            "rows": [
                ["short1", 10000],
                ["short2", 5000],
            ],
        }

        result = youtube_analytics_top_shorts()
        assert len(result["results"]) == 2
        assert result["results"][0]["video"] == "short1"
        assert result["results"][0]["views"] == 10000
