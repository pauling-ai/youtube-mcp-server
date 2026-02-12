"""Tests for auth module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from youtube_mcp.auth import AuthError, YouTubeAuth


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
