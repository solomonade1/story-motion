"""Studio errors. Messages are written for the creator: what happened and what to do next."""

from __future__ import annotations

from ..errors import StoryMotionError


class StudioError(StoryMotionError):
    code = "studio_error"
    http_status = 400


class InvalidInput(StudioError):
    code = "invalid_input"


class ProjectNotFound(StudioError):
    code = "project_not_found"
    http_status = 404


class AssetNotFound(StudioError):
    code = "asset_not_found"
    http_status = 404


class ProjectCorrupt(StudioError):
    code = "project_corrupt"
    http_status = 500


class StaleRevision(StudioError):
    code = "stale_revision"
    http_status = 409


class SchemaTooNew(StudioError):
    code = "schema_too_new"
    http_status = 409


class StorageError(StudioError):
    code = "storage_error"
    http_status = 507


class JobCancelled(StudioError):
    code = "cancelled"
