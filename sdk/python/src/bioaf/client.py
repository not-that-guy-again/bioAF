"""API client for bioAF."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger("bioaf")

_config: dict[str, Any] = {
    "api_url": None,
    "token": None,
    "experiment_id": None,
    "project_id": None,
    "session_id": None,
}


def connect(
    api_url: str | None = None,
    token: str | None = None,
) -> None:
    """Configure connection to bioAF API.

    Reads from environment variables if args not provided:
    BIOAF_API_URL, BIOAF_TOKEN, BIOAF_EXPERIMENT_ID, BIOAF_PROJECT_ID, BIOAF_SESSION_ID
    """
    _config["api_url"] = api_url or os.environ.get("BIOAF_API_URL", "")
    _config["token"] = token or os.environ.get("BIOAF_TOKEN", "")
    _config["experiment_id"] = os.environ.get("BIOAF_EXPERIMENT_ID")
    _config["project_id"] = os.environ.get("BIOAF_PROJECT_ID")
    _config["session_id"] = os.environ.get("BIOAF_SESSION_ID")

    if not _config["api_url"]:
        logger.warning("BIOAF_API_URL not set. Snapshots will fail until connect() is called with a valid URL.")


def _get_config() -> dict[str, Any]:
    """Return current config (for testing)."""
    return dict(_config)


def _post(path: str, json: dict | None = None, files: dict | None = None) -> dict:
    """Internal POST helper with auth headers."""
    url = f"{_config['api_url']}{path}"
    headers = {"Authorization": f"Bearer {_config['token']}"}

    if files:
        resp = requests.post(url, headers=headers, files=files, timeout=120)
    else:
        headers["Content-Type"] = "application/json"
        resp = requests.post(url, headers=headers, json=json, timeout=30)

    resp.raise_for_status()
    return resp.json()


def _get(path: str, params: dict | None = None) -> dict:
    """Internal GET helper with auth headers."""
    url = f"{_config['api_url']}{path}"
    headers = {
        "Authorization": f"Bearer {_config['token']}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
