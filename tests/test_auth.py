"""Tests for auth module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from youtube_mcp.auth import SCOPES, AuthError, YouTubeAuth


def test_default_config_dir():
    yt_auth = YouTubeAuth()
    assert yt_auth.config_dir == Path.home() / ".youtube-mcp"
    assert yt_auth.token_path == Path.home() / ".youtube-mcp" / "token.json"


def test_custom_config_dir(tmp_path):
    yt_auth = YouTubeAuth(config_dir=tmp_path)
    assert yt_auth.config_dir == tmp_path
    assert yt_auth.token_path == tmp_path / "token.json"


def test_client_secret_from_env(tmp_path, monkeypatch):
    secret_path = tmp_path / "my_secret.json"
    monkeypatch.setenv("YOUTUBE_MCP_CLIENT_SECRET", str(secret_path))
    yt_auth = YouTubeAuth()
    assert yt_auth.client_secret_path == secret_path


def test_client_secret_explicit_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_MCP_CLIENT_SECRET", "/env/path.json")
    explicit = tmp_path / "explicit.json"
    yt_auth = YouTubeAuth(client_secret_path=explicit)
    assert yt_auth.client_secret_path == explicit


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key-123")
    yt_auth = YouTubeAuth()
    assert yt_auth.api_key == "test-key-123"


def test_api_key_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "env-key")
    yt_auth = YouTubeAuth(api_key="explicit-key")
    assert yt_auth.api_key == "explicit-key"


def test_status_no_token(tmp_path):
    yt_auth = YouTubeAuth(config_dir=tmp_path)
    status = yt_auth.status()
    assert status["authenticated"] is False
    assert status["token_exists"] is False


def test_authenticate_missing_client_secret(tmp_path):
    yt_auth = YouTubeAuth(
        config_dir=tmp_path,
        client_secret_path=tmp_path / "nonexistent.json",
    )
    with pytest.raises(AuthError, match="client_secret.json not found"):
        yt_auth.authenticate()


def test_build_public_youtube_service_no_key(tmp_path):
    yt_auth = YouTubeAuth(config_dir=tmp_path, api_key=None)
    # Clear env var too
    with patch.dict("os.environ", {}, clear=True):
        yt_auth.api_key = None
        with pytest.raises(AuthError, match="No API key available"):
            yt_auth.build_public_youtube_service()


def test_load_and_save_token(tmp_path):
    yt_auth = YouTubeAuth(config_dir=tmp_path)

    # Create a mock credential
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = json.dumps({
        "token": "test-token",
        "refresh_token": "test-refresh",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    })

    yt_auth._save_token(mock_creds)
    assert (tmp_path / "token.json").exists()


def _write_token(tmp_path, scopes, expiry="2099-01-01T00:00:00Z"):
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps({
        "token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "scopes": scopes,
        "expiry": expiry,
    }))
    return token_path


def test_scopes_include_force_ssl_for_comment_writes():
    """commentThreads.insert and comments.insert require youtube.force-ssl.
    Without this scope, write calls fail with 403 insufficientPermissions.
    """
    assert "https://www.googleapis.com/auth/youtube.force-ssl" in SCOPES


def test_load_token_reports_actual_scopes_from_disk(tmp_path):
    """Regression: from_authorized_user_file must not be passed a non-None
    `scopes` argument -- doing so makes it ignore the file's real "scopes"
    field and always report today's SCOPES constant instead, which silently
    defeats any scope-sufficiency check performed on the result.
    """
    old_scopes = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube",
    ]
    _write_token(tmp_path, old_scopes)

    yt_auth = YouTubeAuth(config_dir=tmp_path)
    creds = yt_auth._load_token()

    assert creds.scopes == old_scopes
    assert "https://www.googleapis.com/auth/youtube.force-ssl" not in creds.scopes


class TestCachedTokenScopeValidation:
    """Regression: when SCOPES is expanded (e.g. adding youtube.force-ssl),
    existing cached tokens authorize only the old scope set but still report
    creds.valid == True. authenticate() must detect the scope shortfall,
    invalidate the stale token, and fall back to the interactive flow
    instead of returning stale credentials.

    These round-trip through the real Credentials.from_authorized_user_file
    (a real token.json on disk) rather than mocking google-auth's Credentials
    class directly, since mocking at that boundary is what let the original
    bug (scopes silently ignored by _load_token) go undetected.
    """

    def test_cached_token_missing_scopes_triggers_reauth_and_invalidation(
        self, tmp_path
    ):
        old_scopes = [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
            "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
        ]
        token_path = _write_token(tmp_path, old_scopes)

        yt_auth = YouTubeAuth(
            config_dir=tmp_path,
            client_secret_path=tmp_path / "nonexistent.json",
        )

        # With no client_secret available, a forced re-auth surfaces as
        # AuthError. That proves we did not silently return the stale creds.
        with pytest.raises(AuthError, match="client_secret.json not found"):
            yt_auth.authenticate()

        assert not token_path.exists()

    def test_cached_token_with_all_scopes_is_accepted(self, tmp_path):
        _write_token(tmp_path, list(SCOPES))

        yt_auth = YouTubeAuth(config_dir=tmp_path)
        result = yt_auth.authenticate()

        assert result.valid
        assert yt_auth._has_required_scopes(result)
