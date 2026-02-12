"""Tests for SEO and discovery tools."""

from unittest.mock import MagicMock, patch


class TestSearchSuggestions:
    @patch("youtube_mcp.tools.search.urllib.request.urlopen")
    def test_suggestions(self, mock_urlopen):
        from youtube_mcp.tools.search import youtube_search_suggestions

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'window.google.ac.h([["test"],[["test query",0],["test video",0]],{}])'
        mock_urlopen.return_value = mock_resp

        result = youtube_search_suggestions("test")
        assert result["query"] == "test"
        assert "test query" in result["suggestions"]
        assert "test video" in result["suggestions"]

    def test_suggestions_error(self):
        from youtube_mcp.tools.search import youtube_search_suggestions

        with patch("youtube_mcp.tools.search.urllib.request.urlopen", side_effect=Exception("timeout")):
            result = youtube_search_suggestions("test")
            assert "error" in result


class TestTrending:
    @patch("youtube_mcp.tools.search.auth")
    @patch("youtube_mcp.tools.search.quota")
    def test_trending(self, mock_quota, mock_auth):
        from youtube_mcp.tools.search import youtube_trending

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.videos().list().execute.return_value = {
            "items": [{
                "id": "trend1",
                "snippet": {
                    "title": "Trending Video",
                    "channelTitle": "Popular Channel",
                    "publishedAt": "2025-06-01T00:00:00Z",
                    "description": "Trending",
                    "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                },
                "statistics": {"viewCount": "1000000", "likeCount": "50000", "commentCount": "1000"},
                "contentDetails": {"duration": "PT10M30S"},
            }]
        }

        result = youtube_trending(region_code="US")
        assert result["region"] == "US"
        assert len(result["videos"]) == 1
        assert result["videos"][0]["views"] == 1000000
        mock_quota.consume.assert_called_once_with("list")

    @patch("youtube_mcp.tools.search.auth")
    @patch("youtube_mcp.tools.search.quota")
    def test_trending_with_category(self, mock_quota, mock_auth):
        from youtube_mcp.tools.search import youtube_trending

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.videos().list().execute.return_value = {"items": []}

        result = youtube_trending(category_id="28")
        assert result["category_id"] == "28"


class TestGetCategories:
    @patch("youtube_mcp.tools.search.auth")
    @patch("youtube_mcp.tools.search.quota")
    def test_categories(self, mock_quota, mock_auth):
        from youtube_mcp.tools.search import youtube_get_categories

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.videoCategories().list().execute.return_value = {
            "items": [
                {"id": "28", "snippet": {"title": "Science & Technology", "assignable": True}},
                {"id": "99", "snippet": {"title": "Not Assignable", "assignable": False}},
            ]
        }

        result = youtube_get_categories()
        assert len(result["categories"]) == 1
        assert result["categories"][0]["id"] == "28"
