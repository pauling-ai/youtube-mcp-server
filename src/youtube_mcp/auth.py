"""OAuth 2.0 authentication for YouTube APIs.

Users must provide their own client_secret.json from their Google Cloud project.
On first use, a browser-based OAuth consent flow runs and stores the token locally.
"""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# All scopes we need across all phases
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

DEFAULT_CONFIG_DIR = Path.home() / ".youtube-mcp"
TOKEN_FILE = "token.json"


class AuthError(Exception):
    pass


class YouTubeAuth:
    """Manages OAuth 2.0 credentials and builds API service clients."""

    def __init__(
        self,
        client_secret_path: str | Path | None = None,
        config_dir: str | Path | None = None,
        api_key: str | None = None,
    ):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.token_path = self.config_dir / TOKEN_FILE
        self._credentials: Credentials | None = None

        # Resolve client_secret.json path
        if client_secret_path:
            self.client_secret_path = Path(client_secret_path)
        else:
            env_path = os.environ.get("YOUTUBE_MCP_CLIENT_SECRET")
            if env_path:
                self.client_secret_path = Path(env_path)
            else:
                self.client_secret_path = self.config_dir / "client_secret.json"

        # API key fallback for public-only operations
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")

    def _load_token(self) -> Credentials | None:
        """Load saved credentials from token file."""
        if not self.token_path.exists():
            return None
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            return creds
        except Exception:
            return None

    def _save_token(self, creds: Credentials):
        """Save credentials to token file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json())

    def authenticate(self) -> Credentials:
        """Get valid credentials, running OAuth flow if needed.

        Returns valid credentials. Raises AuthError if client_secret.json
        is missing or the flow fails.
        """
        creds = self._load_token()

        if creds and creds.valid:
            self._credentials = creds
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_token(creds)
                self._credentials = creds
                return creds
            except Exception as e:
                # Refresh failed, need to re-auth
                pass

        # Need to run the OAuth flow
        if not self.client_secret_path.exists():
            raise AuthError(
                f"client_secret.json not found at {self.client_secret_path}. "
                f"Download it from your Google Cloud Console "
                f"(APIs & Services > Credentials > OAuth 2.0 Client IDs) "
                f"and place it at this path, or set YOUTUBE_MCP_CLIENT_SECRET env var."
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secret_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            self._save_token(creds)
            self._credentials = creds
            return creds
        except Exception as e:
            raise AuthError(f"OAuth flow failed: {e}") from e

    @property
    def credentials(self) -> Credentials:
        """Get current credentials, authenticating if needed."""
        if self._credentials and self._credentials.valid:
            return self._credentials
        return self.authenticate()

    def build_youtube_service(self):
        """Build a YouTube Data API v3 service client."""
        return build("youtube", "v3", credentials=self.credentials)

    def build_youtube_analytics_service(self):
        """Build a YouTube Analytics API service client."""
        return build("youtubeAnalytics", "v2", credentials=self.credentials)

    def build_youtube_reporting_service(self):
        """Build a YouTube Reporting API service client."""
        return build("youtubereporting", "v1", credentials=self.credentials)

    def build_public_youtube_service(self):
        """Build a YouTube Data API client using API key only (public data)."""
        if not self.api_key:
            raise AuthError(
                "No API key available. Set YOUTUBE_API_KEY env var for public-only access."
            )
        return build("youtube", "v3", developerKey=self.api_key)

    def status(self) -> dict:
        """Return current auth status."""
        creds = self._load_token()
        if creds and creds.valid:
            return {
                "authenticated": True,
                "scopes": creds.scopes or [],
                "token_path": str(self.token_path),
                "expired": False,
            }
        if creds and creds.expired:
            return {
                "authenticated": False,
                "expired": True,
                "has_refresh_token": bool(creds.refresh_token),
                "token_path": str(self.token_path),
            }
        return {
            "authenticated": False,
            "token_exists": self.token_path.exists(),
            "client_secret_exists": self.client_secret_path.exists(),
            "client_secret_path": str(self.client_secret_path),
        }
