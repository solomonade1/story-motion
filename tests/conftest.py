from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from storymotion_media.errors import ToolchainError  # noqa: E402
from storymotion_media.toolchain import Toolchain, get_toolchain  # noqa: E402

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "jonah"


@pytest.fixture(scope="session")
def tc() -> Toolchain:
    try:
        return get_toolchain()
    except ToolchainError as exc:  # NOT RUN, never PASS, when the toolchain is absent
        pytest.skip(f"FFmpeg toolchain unavailable: {exc}")


@pytest.fixture(scope="session")
def jonah_root() -> Path:
    return FIXTURE_ROOT
