"""Tests for playlist tools with mocked YouTube API."""

from unittest.mock import MagicMock, patch


class TestListPlaylists:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_list_mine(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_list_playlists

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list().execute.return_value = {
            "items": [{
                "id": "PL123",
                "snippet": {
                    "title": "My Playlist",
                    "description": "A playlist",
                    "publishedAt": "2025-01-01T00:00:00Z",
                    "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                },
                "contentDetails": {"itemCount": 5},
            }]
        }

        result = youtube_list_playlists(mine=True)
        assert len(result["playlists"]) == 1
        assert result["playlists"][0]["title"] == "My Playlist"
        assert result["playlists"][0]["video_count"] == 5

    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_list_no_args(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_list_playlists

        result = youtube_list_playlists()
        assert "error" in result

    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_pages_beyond_50(self, mock_quota, mock_auth):
        """Regression: max_results above the API's 50-per-page cap must page
        through nextPageToken instead of silently truncating.
        """
        from youtube_mcp.tools.playlists import youtube_list_playlists

        def make_playlist(i):
            return {
                "id": f"PL{i}",
                "snippet": {"title": f"Playlist {i}", "description": ""},
                "contentDetails": {"itemCount": i},
            }

        state = {"cursor": 0}

        def list_side_effect(**kwargs):
            page_size = kwargs["maxResults"]
            token = kwargs.get("pageToken")
            assert token is None or token == f"tok{state['cursor']}"
            start = state["cursor"]
            end = min(start + page_size, 80)
            items = [make_playlist(i) for i in range(start, end)]
            state["cursor"] = end
            resp = {"items": items, "pageInfo": {"totalResults": 80}}
            if end < 80:
                resp["nextPageToken"] = f"tok{end}"
            return MagicMock(execute=MagicMock(return_value=resp))

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list.side_effect = list_side_effect

        result = youtube_list_playlists(mine=True, max_results=0)

        assert len(result["playlists"]) == 80
        assert result["total"] == 80


class TestCreatePlaylist:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_create(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_create_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().insert().execute.return_value = {
            "id": "PLnew",
            "snippet": {"title": "New Playlist"},
            "status": {"privacyStatus": "private"},
        }

        result = youtube_create_playlist("New Playlist")
        assert result["id"] == "PLnew"
        assert result["url"] == "https://www.youtube.com/playlist?list=PLnew"
        mock_quota.consume.assert_called_once_with("insert")


class TestAddToPlaylist:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_add(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_add_to_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlistItems().insert().execute.return_value = {
            "id": "PLitem1",
            "snippet": {"position": 0},
        }

        result = youtube_add_to_playlist("PL123", "vid1")
        assert result["added"] is True
        assert result["video_id"] == "vid1"


class TestRemoveFromPlaylist:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_remove(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_remove_from_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt

        result = youtube_remove_from_playlist("PLitem1")
        assert result["removed"] is True
        mock_quota.consume.assert_called_once_with("delete")
