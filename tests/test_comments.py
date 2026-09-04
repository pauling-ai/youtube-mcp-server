"""Tests for comment tools with mocked YouTube API."""

from unittest.mock import MagicMock, patch


class TestListComments:
    @patch("youtube_mcp.tools.comments.auth")
    @patch("youtube_mcp.tools.comments.quota")
    def test_list(self, mock_quota, mock_auth):
        from youtube_mcp.tools.comments import youtube_list_comments

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.commentThreads().list().execute.return_value = {
            "items": [{
                "id": "thread1",
                "snippet": {
                    "topLevelComment": {
                        "id": "comment1",
                        "snippet": {
                            "authorDisplayName": "User1",
                            "textDisplay": "Great video!",
                            "likeCount": 5,
                            "publishedAt": "2025-06-01T00:00:00Z",
                        },
                    },
                    "totalReplyCount": 2,
                },
            }]
        }

        result = youtube_list_comments("vid1")
        assert result["video_id"] == "vid1"
        assert len(result["comments"]) == 1
        assert result["comments"][0]["text"] == "Great video!"
        assert result["comments"][0]["reply_count"] == 2
        mock_quota.consume.assert_called_once_with("list")

    @patch("youtube_mcp.tools.comments.auth")
    @patch("youtube_mcp.tools.comments.quota")
    def test_pages_beyond_100(self, mock_quota, mock_auth):
        """Regression: max_results above the API's 100-per-page cap must
        page through nextPageToken instead of silently truncating.
        """
        from youtube_mcp.tools.comments import youtube_list_comments

        def make_thread(i):
            return {
                "id": f"thread{i}",
                "snippet": {
                    "topLevelComment": {
                        "id": f"comment{i}",
                        "snippet": {
                            "authorDisplayName": f"User{i}",
                            "textDisplay": f"Comment {i}",
                            "likeCount": 0,
                            "publishedAt": "2025-06-01T00:00:00Z",
                        },
                    },
                    "totalReplyCount": 0,
                },
            }

        state = {"cursor": 0}

        def list_side_effect(**kwargs):
            page_size = kwargs["maxResults"]
            token = kwargs.get("pageToken")
            assert token is None or token == f"tok{state['cursor']}"
            start = state["cursor"]
            end = min(start + page_size, 150)
            items = [make_thread(i) for i in range(start, end)]
            state["cursor"] = end
            resp = {"items": items, "pageInfo": {"totalResults": 150}}
            if end < 150:
                resp["nextPageToken"] = f"tok{end}"
            return MagicMock(execute=MagicMock(return_value=resp))

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.commentThreads().list.side_effect = list_side_effect

        result = youtube_list_comments("vid1", max_results=120)

        assert len(result["comments"]) == 120
        assert result["total"] == 150
        assert result["comments"][0]["comment_id"] == "comment0"
        assert result["comments"][-1]["comment_id"] == "comment119"


class TestPostComment:
    @patch("youtube_mcp.tools.comments.auth")
    @patch("youtube_mcp.tools.comments.quota")
    def test_post(self, mock_quota, mock_auth):
        from youtube_mcp.tools.comments import youtube_post_comment

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.commentThreads().insert().execute.return_value = {
            "id": "thread2",
            "snippet": {
                "topLevelComment": {
                    "id": "comment2",
                    "snippet": {"textDisplay": "Nice work!"},
                },
            },
        }

        result = youtube_post_comment("vid1", "Nice work!")
        assert result["posted"] is True
        assert result["text"] == "Nice work!"
        mock_quota.consume.assert_called_once_with("insert")


class TestReplyToComment:
    @patch("youtube_mcp.tools.comments.auth")
    @patch("youtube_mcp.tools.comments.quota")
    def test_reply(self, mock_quota, mock_auth):
        from youtube_mcp.tools.comments import youtube_reply_to_comment

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt
        mock_yt.comments().insert().execute.return_value = {
            "id": "reply1",
            "snippet": {"textDisplay": "Thanks!"},
        }

        result = youtube_reply_to_comment("comment1", "Thanks!")
        assert result["posted"] is True
        assert result["parent_id"] == "comment1"
        mock_quota.consume.assert_called_once_with("insert")


class TestDeleteComment:
    @patch("youtube_mcp.tools.comments.auth")
    @patch("youtube_mcp.tools.comments.quota")
    def test_delete(self, mock_quota, mock_auth):
        from youtube_mcp.tools.comments import youtube_delete_comment

        mock_yt = MagicMock()
        mock_auth.build_youtube_service.return_value = mock_yt

        result = youtube_delete_comment("comment1")
        assert result["deleted"] is True
        assert result["comment_id"] == "comment1"
        mock_quota.consume.assert_called_once_with("delete")
