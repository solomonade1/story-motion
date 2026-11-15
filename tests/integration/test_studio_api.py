"""Local API: authentication, host/origin checks, input limits, project + asset flows, process supervision (TRUST-01..03)."""

from __future__ import annotations

import http.client
import json
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from helpers import make_image, make_wav
from storymotion_media.errors import ToolchainError
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.errors import InvalidInput
from storymotion_media.studio.store import Workspace
from storymotion_media.toolchain import Toolchain

pytestmark = pytest.mark.ffmpeg
ORIGIN_OK = "http://127.0.0.1:5173"


class Client:
    def __init__(self, port: int, token: str) -> None:
        self.port, self.token = port, token

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        token: str | None = "default",
        host: str | None = None,
        headers: dict[str, str] | None = None,
        raw: bytes | None = None,
    ) -> tuple[int, Any, dict[str, str]]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        tk = self.token if token == "default" else token
        if tk:
            h["Authorization"] = f"Bearer {tk}"
        h["Host"] = host or f"127.0.0.1:{self.port}"
        conn.request(method, path, body=data, headers=h)
        resp = conn.getresponse()
        payload = resp.read()
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()
        ctype = hdrs.get("content-type", "")
        return resp.status, (json.loads(payload) if "json" in ctype and payload else payload), hdrs


@pytest.fixture
def server(tmp_path: Path, tc: Toolchain) -> Iterator[tuple[ApiServer, Client, Path]]:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>app</html>")
    (tmp_path / "secret.txt").write_text("TOP SECRET")
    srv = ApiServer(Workspace(tmp_path / "ws"), static_dir=static, allowed_origins={ORIGIN_OK}, toolchain=lambda: tc)
    srv.start_background()
    yield srv, Client(srv.port, srv.token), tmp_path
    srv.shutdown()


def wait_job(c: Client, pid: str, jid: str) -> dict[str, Any]:
    for _ in range(600):
        st, job, _ = c.call("GET", f"/api/projects/{pid}/jobs/{jid}")
        assert st == 200
        if job["state"] in ("completed", "failed", "cancelled", "interrupted"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


# ------------------------------------------------------------------ security
def test_only_loopback_is_allowed(tmp_path: Path, tc: Toolchain) -> None:
    with pytest.raises(InvalidInput, match="loopback"):
        ApiServer(Workspace(tmp_path / "w"), host="0.0.0.0", toolchain=lambda: tc)  # noqa: S104


def test_token_is_required_and_checked(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    for tk in (None, "", "wrong", c.token[:-1], c.token + "x"):
        st, body, _ = c.call("GET", "/api/health", token=tk)
        assert st == 401 and body["error"]["code"] == "unauthorised" and c.token not in json.dumps(body)
    assert c.call("GET", "/api/health")[0] == 200


def test_spoofed_host_header_is_rejected_even_with_a_valid_token(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    for host in (
        "evil.example.com",
        "evil.example.com:80",
        f"attacker.test:{c.port}",
        "",
        f"127.0.0.1.evil.test:{c.port}",
    ):
        st, body, _ = c.call("GET", "/api/health", host=host or "x")
        assert st == 403 and body["error"]["code"] == "bad_host"


def test_foreign_browser_origin_is_rejected_allowed_origin_gets_cors(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    st, body, h = c.call("GET", "/api/health", headers={"Origin": "https://evil.example"})
    assert st == 403 and body["error"]["code"] == "bad_origin" and "access-control-allow-origin" not in h
    st, _, h = c.call("GET", "/api/health", headers={"Origin": ORIGIN_OK})
    assert st == 200 and h["access-control-allow-origin"] == ORIGIN_OK
    st, _, h = c.call(
        "OPTIONS", "/api/projects", token=None, headers={"Origin": ORIGIN_OK, "Access-Control-Request-Method": "POST"}
    )
    assert st == 204 and "Authorization" in h["access-control-allow-headers"]
    st, _, h = c.call("OPTIONS", "/api/projects", token=None, headers={"Origin": "https://evil.example"})
    assert st == 403 and "access-control-allow-origin" not in h


def test_body_limits_and_content_type(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    st, body, _ = c.call("POST", "/api/projects", raw=b"x" * 1_100_000, headers={"Content-Type": "application/json"})
    assert st == 413 and body["error"]["code"] == "too_large"
    assert c.call("POST", "/api/projects", raw=b"{not json", headers={"Content-Type": "application/json"})[0] == 400
    assert c.call("POST", "/api/projects", raw=b"[1,2]", headers={"Content-Type": "application/json"})[0] == 400
    assert c.call("POST", "/api/projects", raw=b'{"name":"x"}', headers={"Content-Type": "text/plain"})[0] == 415


def test_unknown_routes_methods_and_traversal(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, root = server
    assert c.call("GET", "/api/nope")[0] == 404
    assert c.call("DELETE", "/api/health")[0] == 405
    assert c.call("POST", "/")[0] == 405
    for p in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "/a\\..\\secret.txt", "/api/../secret.txt"):
        st, body, _ = c.call("GET", p, token=None)
        assert st in (400, 404) or body == b"<html>app</html>", p
        assert b"TOP SECRET" not in (body if isinstance(body, bytes) else json.dumps(body).encode()), p
    st, body, h = c.call("GET", "/", token=None)  # the UI itself needs no token (it contains no secrets)
    assert st == 200 and body == b"<html>app</html>"
    csp = h["content-security-policy"]  # the page may run only its own scripts and talk only to its own origin
    for directive in (
        "script-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
    ):
        assert directive in csp
    assert "unsafe-eval" not in csp and "script-src 'self' 'unsafe" not in csp
    assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer"
    assert c.call("GET", "/api/projects/p-ZZZZ")[0] == 404  # malformed ids never reach the filesystem layer


def test_internal_errors_do_not_leak_details_or_the_token(
    server: tuple[ApiServer, Client, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    srv, c, _ = server

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError(f"secret path C:\\Users\\x and token {srv.token}")

    monkeypatch.setattr(srv.ws, "list_projects", boom)
    st, body, _ = c.call("GET", "/api/projects")
    text = json.dumps(body)
    assert st == 500 and body["error"]["code"] == "internal_error"
    assert "Users" not in text and srv.token not in text and "RuntimeError" not in text and "Traceback" not in text


def test_media_token_in_the_query_never_reaches_the_log(
    server: tuple[ApiServer, Client, Path], monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    srv, c, root = server
    monkeypatch.setenv("STORYMOTION_API_LOG", "1")
    pid = c.call("POST", "/api/projects", {"name": "P"})[1]["projectId"]
    make_image(root / "src" / "a.png", (10, 20, 30), size=(640, 360))
    job = c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": [str(root / "src" / "a.png")]})[1]
    wait_job(c, pid, job["id"])
    aid = c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"][0]["id"]
    st, data, h = c.call("GET", f"/api/projects/{pid}/assets/{aid}/thumbs?token={srv.token}", token=None)
    assert st == 200 and h["content-type"] == "image/jpeg" and data[:2] == b"\xff\xd8"
    assert c.call("GET", f"/api/projects/{pid}/assets/{aid}/thumbs", token=None)[0] == 401  # no token, no preview
    assert c.call("GET", f"/api/projects/{pid}/assets/{aid}/thumbs?token=nope", token=None)[0] == 401
    assert c.call("GET", f"/api/projects/{pid}/assets", token=None, raw=None, headers={})[0] == 401
    # a query token is accepted ONLY for media, never for ordinary endpoints
    assert c.call("GET", f"/api/projects/{pid}/assets?token={srv.token}", token=None)[0] == 401
    err = capfd.readouterr().err
    assert srv.token not in err and "?token" not in err and "api GET" in err


# ------------------------------------------------------------------ workflows
def test_project_lifecycle_over_http(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    st, p, _ = c.call("POST", "/api/projects", {"name": "Hezekiah"})
    pid = p["projectId"]
    assert st == 201 and p["revision"] == 0
    assert c.call("POST", "/api/projects", {"name": ""})[1]["error"]["code"] == "invalid_input"
    assert [x["name"] for x in c.call("GET", "/api/projects")[1]["projects"]] == ["Hezekiah"]
    assert c.call("PATCH", f"/api/projects/{pid}", {"name": "Hezekiah v2"})[1]["name"] == "Hezekiah v2"
    assert c.call("PATCH", f"/api/projects/{pid}", {"colour": "red"})[0] == 400
    st, d1, _ = c.call("PUT", f"/api/projects/{pid}/document", {"script": "Line one.", "baseRevision": 1})
    assert st == 200 and d1["script"] == "Line one." and d1["revision"] == 2
    st, err, _ = c.call("PUT", f"/api/projects/{pid}/document", {"script": "x", "baseRevision": 1})
    assert st == 409 and err["error"]["code"] == "stale_revision"
    assert c.call("PUT", f"/api/projects/{pid}/document", {"name": "hack"})[0] == 400
    got = c.call("GET", f"/api/projects/{pid}")[1]
    assert got["document"]["script"] == "Line one." and got["warnings"] == []
    dup = c.call("POST", f"/api/projects/{pid}/duplicate", {})[1]
    assert dup["name"] == "Hezekiah v2 (copy)" and dup["projectId"] != pid
    c.call("PATCH", f"/api/projects/{dup['projectId']}", {"archived": True})
    assert len(c.call("GET", "/api/projects")[1]["projects"]) == 1
    assert len(c.call("GET", "/api/projects?archived=1")[1]["projects"]) == 1
    tid = c.call("DELETE", f"/api/projects/{pid}")[1]["trashId"]
    assert c.call("GET", f"/api/projects/{pid}")[0] == 404
    assert [t["name"] for t in c.call("GET", "/api/trash")[1]["trash"]] == ["Hezekiah v2"]
    assert c.call("POST", f"/api/trash/{tid}/purge", {})[0] == 400  # permanent deletion needs explicit confirmation
    assert c.call("POST", f"/api/trash/{tid}/restore", {})[1]["name"] == "Hezekiah v2"
    assert c.call("GET", f"/api/projects/{pid}")[0] == 200


def test_import_check_relink_over_http(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, root = server
    src = root / "src"
    make_image(src / "pic.png", (150, 40, 40), size=(1280, 720))
    make_wav(src / "voice.wav", 1.5)
    pid = c.call("POST", "/api/projects", {"name": "P"})[1]["projectId"]
    (src / "bad.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"junk" * 40)
    st, job, _ = c.call(
        "POST",
        f"/api/projects/{pid}/assets/import",
        {"paths": [str(src / "pic.png"), str(src / "voice.wav"), str(src / "bad.png")], "mode": "link"},
    )
    assert st == 202
    done = wait_job(c, pid, job["id"])
    assert done["state"] == "completed" and done["progress"] == 1.0
    assert len(done["result"]["imported"]) == 2 and done["result"]["errors"][0]["code"] == "corrupt_media"
    assets = c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]
    assert {a["kind"] for a in assets} == {"image", "audio"}
    pic = next(a for a in assets if a["kind"] == "image")
    assert (
        c.call("PATCH", f"/api/projects/{pid}/assets/{pic['id']}", {"category": "character"})[1]["category"]
        == "character"
    )
    assert c.call("PATCH", f"/api/projects/{pid}/assets/{pic['id']}", {"category": "nonsense"})[0] == 400
    (src / "pic.png").rename(root / "pic-moved.png")
    chk = wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/assets/check", {})[1]["id"])
    assert chk["result"]["counts"] == {"ok": 1, "missing": 1, "changed": 0}
    assert c.call("GET", f"/api/projects/{pid}")[1]["assetCounts"] == {"ok": 1, "missing": 1}
    st, fixed, _ = c.call(
        "POST", f"/api/projects/{pid}/assets/{pic['id']}/relink", {"path": str(root / "pic-moved.png")}
    )
    assert st == 200 and fixed["status"] == "ok"
    assert c.call("POST", f"/api/projects/{pid}/assets/{pic['id']}/relink", {"path": str(src / "voice.wav")})[0] == 400
    assert c.call("DELETE", f"/api/projects/{pid}/assets/{pic['id']}")[1]["removed"] == pic["id"]
    assert (root / "pic-moved.png").exists()  # linked originals are never deleted


def test_import_validation_errors_are_clear(server: tuple[ApiServer, Client, Path]) -> None:
    _, c, _ = server
    pid = c.call("POST", "/api/projects", {"name": "P"})[1]["projectId"]
    for body in ({"paths": "nope"}, {"paths": [1, 2]}, {"paths": []}, {"paths": ["x"], "mode": "teleport"}):
        st, err, _ = c.call("POST", f"/api/projects/{pid}/assets/import", body)
        assert st == 400 and err["error"]["code"] == "invalid_input" and err["error"]["message"]


def test_missing_ffmpeg_is_a_clear_503_but_health_still_answers(tmp_path: Path) -> None:
    def no_tools() -> Toolchain:
        raise ToolchainError("Required tool(s) not found: ffmpeg. Install FFmpeg (see README 'Setup').")

    srv = ApiServer(Workspace(tmp_path / "w"), toolchain=no_tools)
    srv.start_background()
    try:
        c = Client(srv.port, srv.token)
        pid = c.call("POST", "/api/projects", {"name": "P"})[1]["projectId"]
        st, err, _ = c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": ["C:/x.png"]})
        assert st == 503 and err["error"]["code"] == "toolchain_missing" and "Install FFmpeg" in err["error"]["message"]
        st, health, _ = c.call("GET", "/api/health")
        ff = next(x for x in health["checks"] if x["id"] == "ffmpeg")
        assert st == 200 and health["ok"] is False and ff["status"] == "fail" and ff["fix"]
        assert next(x for x in health["checks"] if x["id"] == "offline")["status"] == "ok"
    finally:
        srv.shutdown()


# ------------------------------------------------------------------ process supervision
def test_serve_prints_ready_and_exits_when_the_parent_closes_stdin(tmp_path: Path) -> None:
    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "storymotion_media",
            "serve",
            "--workspace",
            str(tmp_path / "ws"),
            "--exit-on-stdin-close",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None and proc.stdin is not None
        ready = json.loads(proc.stdout.readline())
        assert ready["event"] == "ready" and ready["port"] > 0 and len(ready["token"]) >= 32
        st, body, _ = Client(ready["port"], ready["token"]).call("GET", "/api/health")
        assert st == 200 and isinstance(body["pid"], int)  # (on Windows the venv launcher has its own pid)
        proc.stdin.close()  # the shell went away: the worker must not linger as a hidden background process
        assert proc.wait(timeout=15) == 0
        time.sleep(0.3)
        with pytest.raises(OSError):  # nothing is listening any more: no hidden background worker is left
            Client(ready["port"], ready["token"]).call("GET", "/api/health")
    finally:
        if proc.poll() is None:
            proc.kill()
