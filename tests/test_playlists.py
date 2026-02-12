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
