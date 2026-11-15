"""Identifiers, names and workspace location. User text never becomes a path component."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

from .errors import InvalidInput

PROJECT_ID_RE = re.compile(r"^p-[0-9a-f]{12}$")
ASSET_ID_RE = re.compile(r"^a-[0-9a-f]{12}$")
JOB_ID_RE = re.compile(r"^j-[0-9a-f]{12}$")
TRASH_RE = re.compile(r"^p-[0-9a-f]{12}-\d{8}T\d{6}Z$")
MAX_NAME = 120


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(6)}"


def check_project_id(pid: str) -> str:
    if not PROJECT_ID_RE.match(pid):
        raise InvalidInput("That is not a valid project id.")
    return pid


def check_asset_id(aid: str) -> str:
    if not ASSET_ID_RE.match(aid):
        raise InvalidInput("That is not a valid asset id.")
    return aid


def validate_name(name: object) -> str:
    if not isinstance(name, str):
        raise InvalidInput("A project name must be text.")
    clean = name.strip()
    if not clean:
        raise InvalidInput("Please give the project a name.")
    if len(clean) > MAX_NAME:
        raise InvalidInput(f"The name is too long (maximum {MAX_NAME} characters).")
    if any(ord(c) < 32 or ord(c) == 127 for c in clean):
        raise InvalidInput("The name contains control characters.")
    return clean


def default_workspace() -> Path:
    env = os.environ.get("STORYMOTION_WORKSPACE")
    return Path(env) if env else Path.home() / "StoryMotion Studio"
