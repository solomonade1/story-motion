"""StoryMotion Studio media worker (Phase 0 headless proof of concept)."""

__version__ = "0.0.1"

# Bump whenever render output could change for identical inputs. Used by cache keys later
# (PRD 10.4: cache nodes include worker/encoder version).
PROCESSOR_VERSION = "phase0-1"
