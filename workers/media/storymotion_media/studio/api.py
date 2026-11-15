"""Local HTTP API for the desktop shell / browser UI.

Security model (Charter B3; QG TRUST-01..03):
- binds to the loopback interface only; refuses any other host;
- every /api request needs a random per-session bearer token (media <img>/<video> may pass ?token=);
- the Host header must be the loopback origin (blocks DNS-rebinding) and a browser Origin must be on an allow-list;
- bodies are JSON only and capped at 1 MB; unknown routes/methods are rejected;
- the surface is a fixed list of narrow commands: no shell, no arbitrary file read/write, no raw SQL;
  the only client-supplied paths are the files a user explicitly chooses to import or relink;
- previews are served by asset id from the database, never by a client-supplied path;
- errors are readable messages with a code; internals and the token never appear in responses or logs.
"""

from __future__ import annotations

import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .. import __version__
from ..errors import ManifestValidationError, ToolchainError
from ..toolchain import Toolchain, get_toolchain
from .assets import AssetService, check_import_args
from .errors import InvalidInput, StudioError
from .jobs import JobManager
from .migrations import CURRENT
from .paths import PROJECT_ID_RE
from .picker import check_request
from .render_service import RenderService
from .store import Workspace
from .storyboard_service import StoryboardService

MAX_BODY = 1_000_000
# What the UI page may load/do. Scripts only from itself (no inline/eval), the API only on the same origin, no plugins,
# no framing, no form posts. Inline *styles* are allowed because the UI sets progress-bar widths.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
START = time.monotonic()


def readiness_checks(ws: Workspace, toolchain: Callable[[], Toolchain] = get_toolchain) -> list[dict[str, str]]:
    """First-run setup checks: what works, what is missing, and exactly how to fix it."""
    checks: list[dict[str, str]] = []

    def add(cid: str, label: str, status: str, detail: str, fix: str = "") -> None:
        checks.append({"id": cid, "label": label, "status": status, "detail": detail, "fix": fix})

    v = sys.version_info
    add(
        "python",
        "Python worker",
        "ok" if v >= (3, 11) else "fail",
        f"Python {v.major}.{v.minor}.{v.micro}",
        "Install Python 3.11 or newer." if v < (3, 11) else "",
    )
    try:
        tc = toolchain()
        add("ffmpeg", "FFmpeg + ffprobe", "ok", tc.version.split(" Copyright")[0])
    except ToolchainError as exc:
        add("ffmpeg", "FFmpeg + ffprobe", "fail", str(exc), "Install FFmpeg (see README 'Setup') and restart the app.")
    try:
        probe = ws.root / ".write-test"
        probe.write_text("ok")
        probe.unlink()
        add("workspace", "Workspace folder", "ok", str(ws.root))
    except OSError as exc:
        add(
            "workspace",
            "Workspace folder",
            "fail",
            f"{ws.root} is not writable ({exc.strerror or exc})",
            "Choose a folder you can write to.",
        )
    free_gb = shutil.disk_usage(ws.root).free / 1e9
    add(
        "disk",
        "Free disk space",
        "ok" if free_gb >= 5 else "warn" if free_gb >= 1 else "fail",
        f"{free_gb:.1f} GB free",
        "Free some space: video previews and exports need several GB." if free_gb < 5 else "",
    )
    import importlib.util

    piper = importlib.util.find_spec("piper") is not None
    add(
        "piper",
        "Piper voice (optional)",
        "ok" if piper else "warn",
        "installed" if piper else "not installed; narration can use the Windows voice instead",
        "" if piper else "pip install piper-tts (optional).",
    )
    add("offline", "Offline mode", "ok", "This app makes no network connections. Cloud AI is not part of this version.")
    return checks


class ApiError(StudioError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.http_status, self.code = status, code


class ApiServer:
    def __init__(
        self,
        workspace: Workspace,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        token: str | None = None,
        static_dir: Path | None = None,
        allowed_origins: set[str] | None = None,
        toolchain: Callable[[], Toolchain] = get_toolchain,
        picker: Callable[[dict[str, Any]], list[str]] | None = None,
    ) -> None:
        if host not in LOOPBACK:
            raise InvalidInput("The local API only listens on the loopback interface (127.0.0.1).")
        self.ws, self.jobs = workspace, JobManager()
        self.token = token or secrets.token_urlsafe(32)
        self.static_dir = static_dir.resolve() if static_dir else None
        self._toolchain = toolchain
        self.picker = picker  # opens a native chooser on this desktop; None = not offered
        self._tc: Toolchain | None = None
        self._opened: set[str] = set()
        self._httpd = ThreadingHTTPServer((host, port), _make_handler(self))
        self.port = self._httpd.server_address[1]
        self.extra_origins = set(allowed_origins or set())
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ lifecycle
    def origin_allowed(self, origin: str) -> bool:
        return origin in {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"} | self.extra_origins

    def host_allowed(self, host: str) -> bool:
        return host in {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="storymotion-api", daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self.jobs.shutdown()

    @property
    def toolchain(self) -> Toolchain:
        if self._tc is None:
            try:
                self._tc = self._toolchain()
            except ToolchainError as exc:
                raise ApiError(503, "toolchain_missing", str(exc)) from exc
        return self._tc

    def assets(self, pid: str) -> AssetService:
        p = self.ws.project(pid)
        self.jobs.reconcile(p)
        svc = AssetService(p, self.toolchain)
        if pid not in self._opened:  # first time this process touches the project: nothing of ours can be mid-import
            self._opened.add(pid)
            svc.cleanup_orphans(min_age_s=0)
        return svc


# ---------------------------------------------------------------------- routing
Route = tuple[str, re.Pattern[str], str]
_ID = r"(p-[0-9a-f]{12})"
_AID = r"(a-[0-9a-f]{12})"
_JID = r"(j-[0-9a-f]{12})"
ROUTES: list[Route] = [
    ("GET", re.compile(r"^/api/health$"), "health"),
    ("POST", re.compile(r"^/api/pick$"), "pick"),
    ("GET", re.compile(r"^/api/projects$"), "projects_list"),
    ("POST", re.compile(r"^/api/projects$"), "projects_create"),
    ("GET", re.compile(rf"^/api/projects/{_ID}$"), "project_get"),
    ("PATCH", re.compile(rf"^/api/projects/{_ID}$"), "project_patch"),
    ("DELETE", re.compile(rf"^/api/projects/{_ID}$"), "project_delete"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/duplicate$"), "project_duplicate"),
    ("PUT", re.compile(rf"^/api/projects/{_ID}/document$"), "document_put"),
    ("GET", re.compile(r"^/api/trash$"), "trash_list"),
    ("POST", re.compile(r"^/api/trash/(p-[0-9a-f]{12}-\d{8}T\d{6}Z)/restore$"), "trash_restore"),
    ("POST", re.compile(r"^/api/trash/(p-[0-9a-f]{12}-\d{8}T\d{6}Z)/purge$"), "trash_purge"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/assets$"), "assets_list"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/assets/import$"), "assets_import"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/assets/check$"), "assets_check"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/assets/relink-folder$"), "assets_relink_folder"),
    ("PATCH", re.compile(rf"^/api/projects/{_ID}/assets/{_AID}$"), "asset_patch"),
    ("DELETE", re.compile(rf"^/api/projects/{_ID}/assets/{_AID}$"), "asset_delete"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/assets/{_AID}/relink$"), "asset_relink"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/assets/{_AID}/(thumbs|proxies|alpha)$"), "asset_file"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/storyboard$"), "storyboard_get"),
    ("PUT", re.compile(rf"^/api/projects/{_ID}/storyboard$"), "storyboard_put"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/storyboard/import-script$"), "storyboard_import_script"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/storyboard/import-plan$"), "storyboard_import_plan"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/storyboard/render$"), "storyboard_render"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/storyboard/export$"), "storyboard_export"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/exports$"), "exports_list"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/exports/(x-[0-9a-f]{{12}}-(?:full|brief|assets))/open$"), "export_open"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/renders$"), "renders_list"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/renders/(r-[0-9a-f]{{12}}-(?:draft|final)\.(?:mp4|json))$"), "render_file"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/jobs$"), "jobs_list"),
    ("GET", re.compile(rf"^/api/projects/{_ID}/jobs/{_JID}$"), "job_get"),
    ("POST", re.compile(rf"^/api/projects/{_ID}/jobs/{_JID}/cancel$"), "job_cancel"),
]


def _make_handler(api: ApiServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "StoryMotion"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        # no query strings (they can carry the media token) and no bodies in logs
        def log_message(self, fmt: str, *args: Any) -> None:
            if os.environ.get("STORYMOTION_API_LOG"):
                sys.stderr.write(f"api {self.command} {urlsplit(self.path).path}\n")

        # ------------------------------------------------------------ plumbing
        def _send(self, status: int, body: bytes, ctype: str, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            origin = self.headers.get("Origin")
            if origin and api.origin_allowed(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: Any) -> None:
            self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

        def _error(self, status: int, code: str, message: str) -> None:
            self._json(status, {"error": {"code": code, "message": message}})

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(413, "too_large", "That request is too large.")
            if length == 0:
                return {}
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ApiError(415, "unsupported_media_type", "Requests must be JSON.")
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ApiError(400, "bad_json", "The request was not valid JSON.") from exc
            if not isinstance(data, dict):
                raise ApiError(400, "bad_json", "The request body must be a JSON object.")
            return data

        def _authorised(self, query: dict[str, list[str]], *, media: bool) -> bool:
            auth = self.headers.get("Authorization") or ""
            candidate = auth[7:] if auth.startswith("Bearer ") else ""
            if not candidate and media:
                candidate = (query.get("token") or [""])[0]
            return bool(candidate) and hmac.compare_digest(candidate.encode(), api.token.encode())

        # ------------------------------------------------------------ dispatch
        def _handle(self) -> None:
            try:
                if not api.host_allowed(self.headers.get("Host") or ""):
                    return self._error(403, "bad_host", "Requests must go to the local address.")
                origin = self.headers.get("Origin")
                if origin and not api.origin_allowed(origin):
                    return self._error(403, "bad_origin", "This page is not allowed to use the local API.")
                parts = urlsplit(self.path)
                path = unquote(parts.path)
                if "\\" in path or ".." in path.split("/") or "\x00" in path:
                    return self._error(400, "bad_path", "That path is not valid.")
                if not path.startswith("/api/"):
                    if self.command != "GET":
                        return self._error(405, "method_not_allowed", "Method not allowed.")
                    return self._static(path)
                query = parse_qs(parts.query)
                for method, pattern, name in ROUTES:
                    m = pattern.match(path)
                    if not m:
                        continue
                    if method != self.command:
                        continue
                    media = name in ("asset_file", "render_file")
                    if not self._authorised(query, media=media):
                        return self._error(401, "unauthorised", "Missing or invalid session token.")
                    result = getattr(self, f"r_{name}")(*m.groups(), query=query)
                    if isinstance(result, tuple):
                        return self._json(result[0], result[1])
                    if result is not None:
                        return self._json(200, result)
                    return None
                if any(p.match(path) for _m, p, _n in ROUTES):
                    return self._error(405, "method_not_allowed", "Method not allowed.")
                return self._error(404, "not_found", "Unknown address.")
            except StudioError as exc:
                self._error(exc.http_status, exc.code, str(exc))
            except ToolchainError as exc:
                self._error(503, "toolchain_missing", str(exc))
            except ManifestValidationError as exc:
                self._json(
                    422,
                    {
                        "error": {
                            "code": "invalid_plan",
                            "message": f"{len(exc.issues)} problem(s) found. Nothing was saved.",
                            "issues": [{"path": i.path, "message": i.message} for i in exc.issues[:200]],
                        }
                    },
                )
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                sys.stderr.write(f"api error {type(exc).__name__} on {self.command} {urlsplit(self.path).path}\n")
                self._error(
                    500, "internal_error", "Something went wrong inside the app. Your project files were not changed."
                )

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle  # noqa: N815

        def do_OPTIONS(self) -> None:  # noqa: N802 - CORS preflight for the allow-listed origins only
            origin = self.headers.get("Origin") or ""
            if not api.host_allowed(self.headers.get("Host") or "") or not api.origin_allowed(origin):
                return self._error(403, "bad_origin", "This page is not allowed to use the local API.")
            self._send(
                204,
                b"",
                "text/plain",
                {
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Access-Control-Max-Age": "600",
                },
            )

        def _static(self, path: str) -> None:
            root = api.static_dir
            if root is None:
                return self._error(404, "not_found", "The app UI is not installed here.")
            rel = path.lstrip("/") or "index.html"
            target = (root / rel).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                target = root / "index.html"  # single-page app fallback
                if not target.is_file():
                    return self._error(404, "not_found", "Not found.")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), ctype, {"Content-Security-Policy": CSP})

        # ------------------------------------------------------------ routes
        def r_health(self, *, query: dict[str, list[str]]) -> dict[str, Any]:
            checks = readiness_checks(api.ws, api._toolchain)
            return {
                "ok": not any(c["status"] == "fail" for c in checks),
                "checks": checks,
                "version": __version__,
                "projectSchema": CURRENT,
                "uptimeSeconds": round(time.monotonic() - START, 1),
                "pid": os.getpid(),
                "workspace": str(api.ws.root),
            }

        def r_pick(self, *, query: dict[str, list[str]]) -> dict[str, Any]:
            if api.picker is None:
                raise ApiError(409, "picker_unavailable", "The file chooser is only available in the app window. Type the path instead.")
            return {"paths": api.picker(check_request(self._body()))}

        def r_projects_list(self, *, query: dict[str, list[str]]) -> dict[str, Any]:
            arch = (query.get("archived") or ["0"])[0] == "1"
            return {"projects": api.ws.list_projects(archived=arch), "problems": []}

        def r_projects_create(self, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            return 201, api.ws.create(self._body().get("name")).model_dump()  # type: ignore[arg-type]

        def r_project_get(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            p = api.ws.project(pid)
            api.jobs.reconcile(p)
            doc, info = p.load()
            with p.db() as con:
                counts = {
                    r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) AS n FROM assets GROUP BY status")
                }
            return {
                "document": doc.model_dump(),
                "warnings": info.warnings,
                "migrated": info.migrated,
                "assetCounts": counts,
            }

        def r_project_patch(self, pid: str, *, query: dict[str, list[str]]) -> Any:
            body = self._body()
            unknown = set(body) - {"name", "archived"}
            if unknown or not body:
                raise InvalidInput("Send 'name' and/or 'archived'.")
            doc = None
            if "name" in body:
                doc = api.ws.rename(pid, body["name"])
            if "archived" in body:
                if not isinstance(body["archived"], bool):
                    raise InvalidInput("'archived' must be true or false.")
                doc = api.ws.set_archived(pid, body["archived"])
            return doc.model_dump() if doc else None

        def r_project_delete(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return {
                "trashId": api.ws.delete(pid),
                "message": "Moved to the trash. You can restore it until it is emptied.",
            }

        def r_project_duplicate(self, pid: str, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            return 201, api.ws.duplicate(pid, self._body().get("name")).model_dump()

        def r_document_put(self, pid: str, *, query: dict[str, list[str]]) -> Any:
            body = self._body()
            base = body.pop("baseRevision", None)
            if base is not None and not isinstance(base, int):
                raise InvalidInput("'baseRevision' must be a number.")
            return api.ws.project(pid).update(body, base).model_dump()

        def r_trash_list(self, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return {"trash": api.ws.trash_list()}

        def r_trash_restore(self, tid: str, *, query: dict[str, list[str]]) -> Any:
            return api.ws.restore(tid).model_dump()

        def r_trash_purge(self, tid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            api.ws.purge(tid, confirm=self._body().get("confirm") is True)
            return {"purged": tid}

        def r_assets_list(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return {"assets": api.assets(pid).list_assets()}

        def r_assets_import(self, pid: str, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            body = self._body()
            paths, mode, category = body.get("paths"), body.get("mode", "copy"), body.get("category")
            paths = check_import_args(paths, mode, category)
            svc = api.assets(pid)
            job = api.jobs.start(
                svc.p,
                "import",
                {"count": len(paths), "mode": mode},
                lambda rep, ev: svc.import_files(
                    paths, mode=mode, category=category, progress=rep, cancel=ev
                ).as_dict(),
            )
            return 202, job

        def r_assets_check(self, pid: str, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            verify = self._body().get("verifyHash") is True
            svc = api.assets(pid)
            job = api.jobs.start(
                svc.p,
                "check",
                {"verifyHash": verify},
                lambda rep, ev: svc.check_all(verify_hash=verify, progress=rep, cancel=ev),
            )
            return 202, job

        def r_assets_relink_folder(self, pid: str, *, query: dict[str, list[str]]) -> Any:
            folder = self._body().get("folder")
            if not isinstance(folder, str):
                raise InvalidInput("'folder' must be a folder path.")
            return api.assets(pid).relink_folder(folder)

        def r_asset_patch(self, pid: str, aid: str, *, query: dict[str, list[str]]) -> Any:
            cat = self._body().get("category")
            if not isinstance(cat, str):
                raise InvalidInput("'category' is required.")
            return api.assets(pid).set_category(aid, cat)

        def r_asset_delete(self, pid: str, aid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            api.assets(pid).remove(aid)
            return {"removed": aid}

        def r_asset_relink(self, pid: str, aid: str, *, query: dict[str, list[str]]) -> Any:
            path = self._body().get("path")
            if not isinstance(path, str):
                raise InvalidInput("'path' is required.")
            return api.assets(pid).relink(aid, path)

        def r_asset_file(self, pid: str, aid: str, which: str, *, query: dict[str, list[str]]) -> None:
            f = api.assets(pid).served_file(aid, which)
            data = f.read_bytes()
            self._send(200, data, mimetypes.guess_type(f.name)[0] or "application/octet-stream")

        def _storyboard(self, pid: str) -> StoryboardService:
            return StoryboardService(api.ws.project(pid), api.assets(pid))

        @staticmethod
        def _base(body: dict[str, Any]) -> int | None:
            base = body.get("baseRevision")
            if base is not None and (not isinstance(base, int) or isinstance(base, bool)):
                raise InvalidInput("'baseRevision' must be a number.")
            return base

        def r_storyboard_get(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return self._storyboard(pid).get()

        def r_storyboard_put(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            body = self._body()
            base = self._base(body)
            return self._storyboard(pid).put(body.get("storyboard"), base)

        def r_storyboard_import_script(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            body = self._body()
            return self._storyboard(pid).import_script(
                body.get("text"), body.get("filename"), replace=body.get("replace") is True, base_revision=self._base(body)
            )

        def r_storyboard_import_plan(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            body = self._body()
            return self._storyboard(pid).import_plan(
                body.get("text"), replace=body.get("replace") is True, base_revision=self._base(body)
            )

        def _renders(self, pid: str) -> RenderService:
            return RenderService(api.ws.project(pid), api.assets(pid), api.toolchain)

        def r_storyboard_render(self, pid: str, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            draft = self._body().get("draft", True)
            if not isinstance(draft, bool):
                raise InvalidInput("'draft' must be true or false.")
            svc = self._renders(pid)
            manifest, notes = svc.prepare()  # refuses, with reasons, before any job exists
            job = api.jobs.start(
                svc.p,
                "render",
                {"draft": draft, "shots": len(manifest.shots)},
                lambda rep, ev: svc.run(manifest, notes, draft=draft, progress=rep, cancel=ev),
            )
            return 202, job

        def r_storyboard_export(self, pid: str, *, query: dict[str, list[str]]) -> tuple[int, Any]:
            mode = self._body().get("mode", "full")
            if mode not in ("full", "brief", "assets"):
                raise InvalidInput("'mode' must be 'full', 'brief' or 'assets'.")
            svc = self._renders(pid)
            manifest, _notes = svc.prepare()  # same readiness rules as a render: refuse, with reasons, before any job exists
            job = api.jobs.start(
                svc.p, "export", {"mode": mode, "shots": len(manifest.shots)},
                lambda rep, ev: svc.export(manifest, mode, progress=rep, cancel=ev),
            )
            return 202, job

        def r_exports_list(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return {"exports": self._renders(pid).list_exports()}

        def r_export_open(self, pid: str, name: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            """Show an export folder in Windows Explorer on this computer (only a folder the worker itself made)."""
            folder = self._renders(pid).export_folder(name)
            if os.name != "nt" or api.picker is None:
                return {"opened": False, "path": str(folder)}  # plain browser / non-Windows: just say where it is
            os.startfile(folder)  # type: ignore[attr-defined,unused-ignore]  # noqa: S606 - a folder we created, chosen by validated name
            return {"opened": True, "path": str(folder)}

        def r_renders_list(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            return {"renders": self._renders(pid).list_renders()}

        def r_render_file(self, pid: str, name: str, *, query: dict[str, list[str]]) -> None:
            f = self._renders(pid).file(name)
            size = f.stat().st_size
            ctype = "video/mp4" if name.endswith(".mp4") else "application/json"
            start, end, status = 0, size - 1, 200
            rng = self.headers.get("Range")
            if rng:
                m = re.match(r"^bytes=(\d*)-(\d*)$", rng.strip())
                if not m or (not m.group(1) and not m.group(2)):
                    return self._error(416, "bad_range", "That byte range is not valid.")
                if m.group(1):
                    start = int(m.group(1))
                    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
                else:  # suffix range: the last N bytes
                    start = max(0, size - int(m.group(2)))
                if start > end or start >= size:
                    return self._error(416, "bad_range", "That byte range is not valid.")
                status = 206
            with f.open("rb") as fh:
                fh.seek(start)
                data = fh.read(end - start + 1)
            extra = {"Accept-Ranges": "bytes"}
            if status == 206:
                extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            self._send(status, data, ctype, extra)

        def r_jobs_list(self, pid: str, *, query: dict[str, list[str]]) -> dict[str, Any]:
            p = api.ws.project(pid)
            api.jobs.reconcile(p)
            return {"jobs": api.jobs.list_jobs(p)}

        def r_job_get(self, pid: str, jid: str, *, query: dict[str, list[str]]) -> Any:
            return api.jobs.get(api.ws.project(pid), jid)

        def r_job_cancel(self, pid: str, jid: str, *, query: dict[str, list[str]]) -> Any:
            return api.jobs.cancel(api.ws.project(pid), jid)

    return Handler


def watch_stdin_and_exit(server: ApiServer) -> None:
    """Exit when the parent process closes our stdin, so the worker never outlives the app (no orphan processes)."""

    def watch() -> None:
        try:
            while sys.stdin.read(1024):
                pass
        except (OSError, ValueError):
            pass
        server.shutdown()

    threading.Thread(target=watch, name="parent-watchdog", daemon=True).start()


__all__ = ["ApiError", "ApiServer", "PROJECT_ID_RE", "readiness_checks", "watch_stdin_and_exit"]
