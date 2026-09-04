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


class TestUpdatePlaylist:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_update_title_and_description(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_update_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list().execute.return_value = {
            "items": [{
                "id": "PL123",
                "snippet": {"title": "Old Title", "description": "Old Desc"},
                "status": {"privacyStatus": "public"},
            }]
        }
        mock_yt.playlists().update().execute.return_value = {
            "id": "PL123",
            "snippet": {"title": "New Title"},
            "status": {"privacyStatus": "public"},
        }

        result = youtube_update_playlist("PL123", title="New Title")
        assert result["title"] == "New Title"
        assert result["privacy"] == "public"
        assert result["updated"] is True

        call_kwargs = mock_yt.playlists().update.call_args.kwargs
        assert call_kwargs["part"] == "snippet"
        assert "status" not in call_kwargs["body"]

    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_update_privacy_status(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_update_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list().execute.return_value = {
            "items": [{
                "id": "PL123",
                "snippet": {"title": "T", "description": "D"},
                "status": {"privacyStatus": "public"},
            }]
        }
        mock_yt.playlists().update().execute.return_value = {
            "id": "PL123",
            "snippet": {"title": "T"},
            "status": {"privacyStatus": "unlisted"},
        }

        result = youtube_update_playlist("PL123", privacy_status="unlisted")
        assert result["privacy"] == "unlisted"

        call_kwargs = mock_yt.playlists().update.call_args.kwargs
        assert call_kwargs["part"] == "snippet,status"
        assert call_kwargs["body"]["status"]["privacyStatus"] == "unlisted"

    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_update_not_found(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_update_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list().execute.return_value = {"items": []}

        result = youtube_update_playlist("nope", title="X")
        assert "error" in result

    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_update_without_privacy_status_does_not_raise_keyerror(self, mock_quota, mock_auth):
        """Regression pattern from youtube_update_video: part='snippet'
        responses omit the 'status' block entirely, so the return builder
        must not unconditionally index into it.
        """
        from youtube_mcp.tools.playlists import youtube_update_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.playlists().list().execute.return_value = {
            "items": [{
                "id": "PL123",
                "snippet": {"title": "Old", "description": "D"},
                "status": {"privacyStatus": "public"},
            }]
        }
        mock_yt.playlists().update().execute.return_value = {
            "id": "PL123",
            "snippet": {"title": "New"},
        }

        result = youtube_update_playlist("PL123", title="New")
        assert result["title"] == "New"
        assert result["updated"] is True
        assert result.get("privacy") is None


class TestDeletePlaylist:
    @patch("youtube_mcp.tools.playlists.auth")
    @patch("youtube_mcp.tools.playlists.quota")
    def test_delete(self, mock_quota, mock_auth):
        from youtube_mcp.tools.playlists import youtube_delete_playlist

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt

        result = youtube_delete_playlist("PL123")
        assert result["deleted"] is True
        assert result["playlist_id"] == "PL123"
        mock_quota.consume.assert_called_once_with("delete")


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
