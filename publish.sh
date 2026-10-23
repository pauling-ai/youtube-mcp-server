#!/usr/bin/env bash
# Publish youtube-studio-mcp to PyPI.
# Auth comes from macOS Keychain; no secrets live in this repo.
#   one-time setup: security add-generic-password -s pypi -a youtube-studio-mcp -w
set -euo pipefail

if ! security find-generic-password -s pypi -a youtube-studio-mcp >/dev/null 2>&1; then
  echo "error: keychain item not found (service: 'pypi', account: 'youtube-studio-mcp')" >&2
  echo "create it with: security add-generic-password -s pypi -a youtube-studio-mcp -w" >&2
  exit 1
fi

# Fresh artifacts only: never upload a stale dist/.
rm -rf dist
uv build

uv publish --token "$(security find-generic-password -s pypi -a youtube-studio-mcp -w)"
