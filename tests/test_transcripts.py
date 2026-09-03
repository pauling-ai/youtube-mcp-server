"""Tests for youtube_get_transcript (scraping path)."""

from unittest.mock import MagicMock, patch

import pytest


def _make_snippet(text, start, duration):
    snippet = MagicMock()
    snippet.text = text
    snippet.start = start
    snippet.duration = duration
    return snippet


class TestGetTranscriptScraping:
    def test_fetches_via_instance_list_and_fetch(self):
        """Regression: youtube-transcript-api >=1.0 replaced the old
        YouTubeTranscriptApi.list_transcripts() classmethod with an instance
        method YouTubeTranscriptApi().list(), and Transcript.fetch() now
        returns an iterable of snippet objects (text/start/duration
        attributes) rather than dicts. Calling the removed classmethod raises
        AttributeError for every video (issue #1).
        """
        from youtube_mcp.tools.transcripts import _get_transcript_scraping

        snippets = [
            _make_snippet("Hello", 0.0, 1.5),
            _make_snippet("world", 1.5, 1.2),
        ]
        mock_transcript = MagicMock()
        mock_transcript.language_code = "en"
        mock_transcript.is_generated = False
        mock_transcript.fetch.return_value = snippets

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_transcript.return_value = mock_transcript

        mock_api_instance = MagicMock()
        mock_api_instance.list.return_value = mock_transcript_list

        with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api_instance) as mock_cls:
            result = _get_transcript_scraping("vid1", "en")

        mock_cls.assert_called_once_with()
        mock_api_instance.list.assert_called_once_with("vid1")
        mock_transcript_list.find_transcript.assert_called_once_with(["en"])

        assert "error" not in result
        assert result["video_id"] == "vid1"
        assert result["language"] == "en"
        assert result["is_generated"] is False
        assert result["full_text"] == "Hello world"
        assert result["segments"] == [
            {"text": "Hello", "start": 0.0, "duration": 1.5},
            {"text": "world", "start": 1.5, "duration": 1.2},
        ]

    def test_falls_back_to_any_transcript_when_language_not_found(self):
        from youtube_mcp.tools.transcripts import _get_transcript_scraping

        snippets = [_make_snippet("Bonjour", 0.0, 1.0)]
        mock_transcript = MagicMock()
        mock_transcript.language_code = "fr"
        mock_transcript.is_generated = True
        mock_transcript.fetch.return_value = snippets

        mock_transcript.translate.side_effect = Exception("not translatable")

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_transcript.side_effect = Exception("not found")
        mock_transcript_list.__iter__.return_value = iter([mock_transcript])

        mock_api_instance = MagicMock()
        mock_api_instance.list.return_value = mock_transcript_list

        with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api_instance):
            result = _get_transcript_scraping("vid1", "en")

        assert "error" not in result
        assert result["language"] == "fr"
        assert result["full_text"] == "Bonjour"

    def test_api_error_is_returned_not_raised(self):
        from youtube_mcp.tools.transcripts import _get_transcript_scraping

        mock_api_instance = MagicMock()
        mock_api_instance.list.side_effect = Exception("Subtitles are disabled for this video")

        with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api_instance):
            result = _get_transcript_scraping("vid1", "en")

        assert result["video_id"] == "vid1"
        assert "error" in result
        assert result["source"] == "youtube-transcript-api"
