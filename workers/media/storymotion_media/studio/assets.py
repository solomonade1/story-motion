"""Media intake for a project (FR-MEDIA-001..004,006; FR-PROJ-003; QG DATA-03..06).

Per file: validate -> SHA-256 -> duplicate check -> probe + real decode -> copy or link -> thumbnail -> proxy -> database row.
Each file is committed on its own, so cancelling or a crash never leaves a half-imported asset behind.
Source files are only ever read, never modified or moved.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

from ..contracts import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, AssetType
from ..errors import MediaError, ToolchainError
from ..ingest import decode_check
from ..toolchain import Toolchain, ffprobe_json, run
from .errors import AssetNotFound, InvalidInput, JobCancelled, StorageError
from .paths import check_asset_id, new_id
from .store import Project, now_iso

SUPPORTED = IMAGE_EXT | AUDIO_EXT | VIDEO_EXT
CATEGORIES = set(get_args(AssetType))
Progress = Callable[[float, str], None]
THUMB_W = 320
PROXY_IMAGE_MAX = 1280
MAX_RELINK_SCAN = 50_000


def kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    return "image" if ext in IMAGE_EXT else "audio" if ext in AUDIO_EXT else "video"


def default_category(kind: str) -> str:
    return {"image": "environment", "audio": "audio", "video": "rendered_video"}[kind]


def safe_stem(path: Path) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-.")[:40]
    return s or "file"


def sha256_cancellable(path: Path, cancel: threading.Event | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            if cancel and cancel.is_set():
                raise JobCancelled("Cancelled.")
            h.update(chunk)
    return h.hexdigest()


def load_rgb(src: Path, max_side: int) -> Any:
    """Open an image, apply its EXIF rotation, shrink to ``max_side`` and flatten transparency onto a dark backdrop."""
    from PIL import Image, ImageOps

    with Image.open(src) as opened:
        img: Any = ImageOps.exif_transpose(opened) or opened
        img = img.copy()
    img.thumbnail((max_side, max_side))
    if img.mode != "RGB":
        rgba = img.convert("RGBA")
        backdrop = Image.new("RGB", rgba.size, (40, 44, 52))
        backdrop.paste(rgba, mask=rgba.split()[3])
        return backdrop
    return img


def check_import_args(paths: object, mode: object, category: object) -> list[str]:
    """Validate an import request up front so bad requests fail immediately, not later inside a background job."""
    if mode not in ("copy", "link"):
        raise InvalidInput("Import mode must be 'copy' or 'link'.")
    if category is not None and category not in CATEGORIES:
        raise InvalidInput(f"Unknown category '{category}'.")
    if not isinstance(paths, list) or not paths or len(paths) > 500 or not all(isinstance(x, str) for x in paths):
        raise InvalidInput("Choose between 1 and 500 files to import (a list of full file paths).")
    return list(paths)


@dataclass
class ImportResult:
    imported: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    cancelled: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "imported": self.imported,
            "duplicates": self.duplicates,
            "errors": self.errors,
            "cancelled": self.cancelled,
        }


class AssetService:
    def __init__(self, project: Project, tc: Toolchain) -> None:
        self.p, self.tc = project, tc

    # ------------------------------------------------------------------ read
    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        d = dict(row)
        d["thumbUrl"] = f"thumbs/{d['id']}" if d.get("thumb_rel") else None
        d["proxyUrl"] = f"proxies/{d['id']}" if d.get("proxy_rel") else None
        d["path_hint"] = d["rel_path"] or d["abs_path"]
        return d

    def list_assets(self) -> list[dict[str, Any]]:
        with self.p.db() as con:
            rows = con.execute("SELECT * FROM assets ORDER BY created_at, orig_name").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, aid: str) -> dict[str, Any]:
        check_asset_id(aid)
        with self.p.db() as con:
            row = con.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone()
        if row is None:
            raise AssetNotFound("That asset is not in this project.")
        return self._row_to_dict(row)

    def current_path(self, asset: dict[str, Any]) -> Path | None:
        if asset["mode"] == "copy":
            return (self.p.dir / asset["rel_path"]) if asset["rel_path"] else None
        return Path(asset["abs_path"]) if asset["abs_path"] else None

    def served_file(self, aid: str, which: str) -> Path:
        """Thumbnail/proxy file for an asset, looked up from the database (never from client-supplied paths)."""
        a = self.get(aid)
        if which == "alpha":
            return self._alpha_preview(a)
        rel = a["thumb_rel"] if which == "thumbs" else a["proxy_rel"]
        if not rel:
            raise AssetNotFound("No preview is available for this asset.")
        path: Path = (self.p.dir / str(rel)).resolve()
        if not path.is_relative_to(self.p.dir.resolve()) or not path.is_file():
            raise AssetNotFound("The preview file is missing; it can be regenerated by re-checking the asset.")
        return path

    def _alpha_preview(self, a: dict[str, Any]) -> Path:
        """A small PNG that KEEPS transparency, for placing layers in the storyboard preview (made on first use)."""
        if a["kind"] != "image":
            raise AssetNotFound("Only pictures have a transparent preview.")
        dest = self.p.dir / "previews" / f"{a['id']}.png"
        if not dest.is_file():
            src = self.current_path(a)
            if src is None or not src.is_file():
                raise AssetNotFound("The picture file is missing; relink it in the media library.")
            from PIL import Image, ImageOps

            try:
                with Image.open(src) as opened:
                    img: Any = (ImageOps.exif_transpose(opened) or opened).convert("RGBA")
                img.thumbnail((PROXY_IMAGE_MAX, PROXY_IMAGE_MAX))
                dest.parent.mkdir(exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                img.save(tmp, "PNG")
                tmp.replace(dest)
            except OSError as exc:
                raise AssetNotFound(f"The preview could not be made ({exc.strerror or exc}).") from exc
        return dest

    # ------------------------------------------------------------------ import
    def import_files(
        self,
        paths: list[str],
        *,
        mode: str = "copy",
        category: str | None = None,
        progress: Progress | None = None,
        cancel: threading.Event | None = None,
    ) -> ImportResult:
        paths = check_import_args(paths, mode, category)
        cancel = cancel or threading.Event()
        report = progress or (lambda _f, _m: None)
        res = ImportResult()
        total = len(paths)
        for i, raw in enumerate(paths):  # noqa: B007
            name = Path(str(raw)).name
            report(i / total, f"Importing {name} ({i + 1} of {total})")
            if cancel.is_set():
                res.cancelled = True
                break
            try:
                outcome = self._import_one(str(raw), mode, category, cancel)
            except JobCancelled:
                res.cancelled = True
                break
            except _FileProblem as prob:
                res.errors.append({"path": str(raw), "code": prob.code, "message": prob.message})
                continue
            (res.duplicates if outcome.get("duplicate") else res.imported).append(outcome)
        report(
            1.0 if not res.cancelled else (len(res.imported) + len(res.errors)) / total,
            "Cancelled" if res.cancelled else "Done",
        )
        return res

    def _import_one(self, raw: str, mode: str, category: str | None, cancel: threading.Event) -> dict[str, Any]:
        name = Path(raw).name or raw
        if not raw or "\x00" in raw:
            raise _FileProblem("invalid_path", "That path is not valid.")
        src = Path(raw)
        if not src.is_absolute():
            raise _FileProblem("invalid_path", f"'{name}': please give the full path to the file.")
        try:
            src = src.resolve(strict=True)
        except OSError:
            raise _FileProblem(
                "not_found", f"'{name}' was not found. Check the path, or that the drive is connected."
            ) from None
        if not src.is_file():
            raise _FileProblem("not_a_file", f"'{name}' is a folder, not a file. Select the files inside it.")
        if src.suffix.lower() not in SUPPORTED:
            raise _FileProblem(
                "unsupported_type",
                f"'{name}' is a {src.suffix or 'type-less'} file, which is not supported. "
                "Supported: PNG, JPG, WebP images; WAV, MP3, AAC audio; MP4, MOV video.",
            )
        try:
            stat = src.stat()
            if stat.st_size == 0:
                raise _FileProblem("empty_file", f"'{name}' is empty (0 bytes).")
            digest = sha256_cancellable(src, cancel)
        except OSError as exc:
            raise _FileProblem("unreadable", f"'{name}' could not be read: {exc.strerror or exc}.") from exc

        with self.p.db() as con:
            dup = con.execute("SELECT id, orig_name, status FROM assets WHERE sha256=?", (digest,)).fetchone()
        if dup is not None:
            note = " It is currently missing; use Relink to repair it." if dup["status"] == "missing" else ""
            return {
                "duplicate": True,
                "path": raw,
                "existingId": dup["id"],
                "existingName": dup["orig_name"],
                "message": f"'{name}' is identical to '{dup['orig_name']}' which is already in the project.{note}",
            }

        kind = kind_of(src)
        meta = self._probe(src, kind, name)
        aid = new_id("a")
        dest_rel: str | None = None
        made: list[Path] = []
        try:
            if mode == "copy":
                dest_rel = f"assets/{aid}-{safe_stem(src)}{src.suffix.lower()}"
                self._copy_verified(src, self.p.dir / dest_rel, digest, name)
                made.append(self.p.dir / dest_rel)
            if cancel.is_set():
                raise JobCancelled("Cancelled.")
            work_src = self.p.dir / dest_rel if dest_rel else src
            thumb_rel, thumb_warn = self._make_thumb(work_src, kind, aid, meta)
            if thumb_rel:
                made.append(self.p.dir / thumb_rel)
            proxy_rel, proxy_warn = self._make_proxy(work_src, kind, aid)
            if proxy_rel:
                made.append(self.p.dir / proxy_rel)
            warnings = [w for w in (thumb_warn, proxy_warn) if w]
            row = {
                "id": aid,
                "sha256": digest,
                "category": category or default_category(kind),
                "kind": kind,
                "mode": mode,
                "rel_path": dest_rel,
                "abs_path": str(src) if mode == "link" else None,
                "orig_name": src.name,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "thumb_rel": thumb_rel,
                "proxy_rel": proxy_rel,
                "status": "ok",
                "status_detail": "; ".join(warnings) or None,
                "created_at": now_iso(),
                **meta,
            }
            with self.p.db() as con:
                cols = ",".join(row)
                con.execute(f"INSERT INTO assets({cols}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))  # noqa: S608
        except BaseException:
            for f in made:
                f.unlink(missing_ok=True)
            raise
        return {**self.get(aid), "duplicate": False, "warnings": warnings}

    def _probe(self, src: Path, kind: str, name: str) -> dict[str, Any]:
        try:
            data = ffprobe_json(self.tc, src)
        except ToolchainError as exc:
            raise _FileProblem("corrupt_media", self._corrupt_msg(name, kind, str(exc))) from exc
        streams = data.get("streams", [])
        vid = next((s for s in streams if s.get("codec_type") == "video"), None)
        aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if kind in ("image", "video") and (
            vid is None or int(vid.get("width", 0)) <= 0 or int(vid.get("height", 0)) <= 0
        ):
            raise _FileProblem("corrupt_media", self._corrupt_msg(name, kind, "no readable picture"))
        if kind == "audio" and aud is None:
            raise _FileProblem("corrupt_media", self._corrupt_msg(name, kind, "no readable audio"))
        problem = decode_check(self.tc, src, kind)
        if problem:
            raise _FileProblem("corrupt_media", self._corrupt_msg(name, kind, problem))
        dur = data.get("format", {}).get("duration")
        fps = None
        if vid and kind == "video" and "/" in str(vid.get("avg_frame_rate", "")):
            n, d = str(vid["avg_frame_rate"]).split("/")
            fps = float(n) / float(d) if float(d) else None
        return {
            "width": int(vid["width"]) if vid else None,
            "height": int(vid["height"]) if vid else None,
            "duration_ms": round(float(dur) * 1000) if dur not in (None, "N/A") and kind != "image" else None,
            "fps": fps,
            "sample_rate": int(aud["sample_rate"]) if aud else None,
            "channels": int(aud["channels"]) if aud else None,
        }

    @staticmethod
    def _corrupt_msg(name: str, kind: str, detail: str) -> str:
        return (
            f"'{name}' could not be read as {'an' if kind == 'image' else 'a'} {kind} file ({detail[:120]}). "
            "It looks damaged or incomplete. Try opening it in another program; if it plays there, export it again and re-import."
        )

    def _copy_verified(self, src: Path, dest: Path, digest: str, name: str) -> None:
        part = dest.with_name(dest.name + ".part")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, part)
            if sha256_cancellable(part) != digest:
                raise _FileProblem(
                    "copy_failed", f"The copy of '{name}' did not match the original, so it was discarded. Try again."
                )
            os.replace(part, dest)
        except OSError as exc:
            raise _FileProblem(
                "copy_failed",
                f"'{name}' could not be copied into the project ({exc.strerror or exc}). "
                "The disk may be full or read-only. The original file is untouched.",
            ) from exc
        finally:
            part.unlink(missing_ok=True)

    # ------------------------------------------------------------------ previews
    def _make_thumb(self, src: Path, kind: str, aid: str, meta: dict[str, Any]) -> tuple[str | None, str | None]:
        try:
            if kind == "image":
                rel = f"thumbs/{aid}.jpg"
                load_rgb(src, THUMB_W).save(self.p.dir / rel, "JPEG", quality=80)
                return rel, None
            if kind == "video":
                rel = f"thumbs/{aid}.jpg"
                at = min(1.0, (meta.get("duration_ms") or 0) / 2000)
                p = run(
                    [
                        self.tc.ffmpeg,
                        "-v",
                        "error",
                        "-y",
                        "-ss",
                        f"{at:.2f}",
                        "-protocol_whitelist",
                        "file",
                        "-i",
                        src,
                        "-frames:v",
                        "1",
                        "-vf",
                        f"scale={THUMB_W}:-2",
                        self.p.dir / rel,
                    ],
                    timeout=120,
                )
                return (
                    (rel, None)
                    if p.returncode == 0 and (self.p.dir / rel).exists()
                    else (None, "thumbnail could not be made")
                )
            rel = f"thumbs/{aid}.png"
            p = run(
                [
                    self.tc.ffmpeg,
                    "-v",
                    "error",
                    "-y",
                    "-protocol_whitelist",
                    "file",
                    "-i",
                    src,
                    "-filter_complex",
                    f"showwavespic=s={THUMB_W}x80:colors=0x5aa9ff",
                    "-frames:v",
                    "1",
                    self.p.dir / rel,
                ],
                timeout=120,
            )
            return (
                (rel, None)
                if p.returncode == 0 and (self.p.dir / rel).exists()
                else (None, "waveform could not be drawn")
            )
        except Exception as exc:  # a preview failure must never block the import itself
            return None, f"thumbnail could not be made ({str(exc)[:80]})"

    def _make_proxy(self, src: Path, kind: str, aid: str) -> tuple[str | None, str | None]:
        try:
            if kind == "image":
                rel = f"proxies/{aid}.jpg"
                load_rgb(src, PROXY_IMAGE_MAX).save(self.p.dir / rel, "JPEG", quality=80)
                return rel, None
            if kind == "video":
                rel = f"proxies/{aid}.mp4"
                p = run(
                    [
                        self.tc.ffmpeg,
                        "-v",
                        "error",
                        "-y",
                        "-protocol_whitelist",
                        "file",
                        "-i",
                        src,
                        "-vf",
                        "scale=-2:360",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "30",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "64k",
                        "-movflags",
                        "+faststart",
                        self.p.dir / rel,
                    ],
                    timeout=900,
                )
                if p.returncode != 0:
                    (self.p.dir / rel).unlink(missing_ok=True)
                    return None, "preview video could not be made"
                if p.stderr.strip():  # the preview reads the whole file, so mid-file damage shows up here
                    first = p.stderr.strip().splitlines()[0][:100]
                    return (
                        rel,
                        f"damaged sections were found while making the preview ({first}); the video may glitch or stop early",
                    )
                return rel, None
            rel = f"proxies/{aid}.m4a"
            p = run(
                [
                    self.tc.ffmpeg,
                    "-v",
                    "error",
                    "-y",
                    "-protocol_whitelist",
                    "file",
                    "-i",
                    src,
                    "-vn",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "64k",
                    self.p.dir / rel,
                ],
                timeout=600,
            )
            if p.returncode != 0:
                (self.p.dir / rel).unlink(missing_ok=True)
                return None, "preview audio could not be made"
            return rel, None
        except Exception as exc:
            return None, f"preview could not be made ({str(exc)[:80]})"

    # ------------------------------------------------------------------ maintenance
    def set_category(self, aid: str, category: str) -> dict[str, Any]:
        if category not in CATEGORIES:
            raise InvalidInput(f"Unknown category '{category}'.")
        self.get(aid)
        with self.p.db() as con:
            con.execute("UPDATE assets SET category=? WHERE id=?", (category, aid))
        return self.get(aid)

    def check_all(
        self, *, verify_hash: bool = False, progress: Progress | None = None, cancel: threading.Event | None = None
    ) -> dict[str, Any]:
        """Re-validate every asset: still there? still the same size (and hash if asked)?"""
        report = progress or (lambda _f, _m: None)
        assets = self.list_assets()
        counts = {"ok": 0, "missing": 0, "changed": 0}
        for i, a in enumerate(assets):
            if cancel and cancel.is_set():
                break
            report(i / max(1, len(assets)), f"Checking {a['orig_name']}")
            status, detail = self._status_of(a, verify_hash, cancel)
            if (status, detail) != (a["status"], a["status_detail"]) and not (status == "ok" and a["status"] == "ok"):
                with self.p.db() as con:
                    con.execute("UPDATE assets SET status=?, status_detail=? WHERE id=?", (status, detail, a["id"]))
            counts[status] += 1
        report(1.0, "Done")
        return {"counts": counts, "total": len(assets)}

    def _status_of(
        self, a: dict[str, Any], verify_hash: bool, cancel: threading.Event | None
    ) -> tuple[str, str | None]:
        path = self.current_path(a)
        if path is None or not path.is_file():
            where = "inside the project" if a["mode"] == "copy" else f"at {a['abs_path']}"
            return "missing", f"The file is no longer {where}. Use Relink to point to it again."
        try:
            st = path.stat()
            if st.st_size != a["size"]:
                return "changed", "The file's size changed since it was imported. Re-import it or relink the original."
            if verify_hash or st.st_mtime_ns != a["mtime_ns"]:
                if sha256_cancellable(path, cancel) != a["sha256"]:
                    return (
                        "changed",
                        "The file's contents changed since it was imported. Re-import it or relink the original.",
                    )
        except OSError as exc:
            return "missing", f"The file cannot be read ({exc.strerror or exc})."
        except JobCancelled:
            return a["status"], a["status_detail"]
        return "ok", None

    def relink(self, aid: str, new_path: str) -> dict[str, Any]:
        """Point an asset at a file again. The file must be byte-identical (same SHA-256)."""
        a = self.get(aid)
        src = Path(new_path)
        if not src.is_absolute() or not src.is_file():
            raise InvalidInput("Please choose an existing file (full path).")
        if src.suffix.lower() != Path(a["orig_name"]).suffix.lower():
            raise InvalidInput("That file has a different type from the original.")
        if sha256_cancellable(src) != a["sha256"]:
            raise InvalidInput(
                "That file is not identical to the original (its contents differ), so it was not linked. "
                "Import it as a new asset instead if you want to use it."
            )
        st = src.stat()
        if a["mode"] == "link":
            with self.p.db() as con:
                con.execute(
                    "UPDATE assets SET abs_path=?, mtime_ns=?, status='ok', status_detail=NULL WHERE id=?",
                    (str(src.resolve()), st.st_mtime_ns, aid),
                )
        else:  # copy-mode asset whose copy vanished: restore it into the project
            dest = self.p.dir / (a["rel_path"] or f"assets/{aid}-{safe_stem(src)}{src.suffix.lower()}")
            self._copy_verified(src, dest, a["sha256"], src.name)
            with self.p.db() as con:
                con.execute(
                    "UPDATE assets SET rel_path=?, mtime_ns=?, status='ok', status_detail=NULL WHERE id=?",
                    (str(dest.relative_to(self.p.dir)).replace("\\", "/"), dest.stat().st_mtime_ns, aid),
                )
        return self.get(aid)

    def relink_folder(self, folder: str) -> dict[str, Any]:
        """Search a folder (recursively) for files matching the missing assets by size + hash."""
        root = Path(folder)
        if not root.is_dir():
            raise InvalidInput("Please choose an existing folder.")
        missing = [a for a in self.list_assets() if a["status"] == "missing"]
        by_size: dict[int, list[dict[str, Any]]] = {}
        for a in missing:
            by_size.setdefault(a["size"], []).append(a)
        fixed: list[str] = []
        scanned = 0
        for dirpath, _dn, files in os.walk(root):
            for fn in files:
                scanned += 1
                if scanned > MAX_RELINK_SCAN:
                    raise InvalidInput("That folder has too many files to search; choose a smaller one.")
                fp = Path(dirpath) / fn
                try:
                    size = fp.stat().st_size
                except OSError:
                    continue
                for a in by_size.get(size, []):
                    if a["id"] in fixed:
                        continue
                    try:
                        if sha256_cancellable(fp) == a["sha256"]:
                            self.relink(a["id"], str(fp))
                            fixed.append(a["id"])
                    except (OSError, InvalidInput, _FileProblem):
                        continue
        return {
            "relinked": fixed,
            "stillMissing": [a["id"] for a in missing if a["id"] not in fixed],
            "scanned": scanned,
        }

    def cleanup_orphans(self, min_age_s: float = 30.0) -> list[str]:
        """Delete files a crashed import left behind: anything in assets/thumbs/proxies that no database row refers to.

        ``min_age_s`` protects files of an import that is still running right now; at worker start-up (when nothing can
        be running in this process) callers pass 0.
        """
        with self.p.db() as con:
            rows = con.execute("SELECT rel_path, thumb_rel, proxy_rel FROM assets").fetchall()
        keep = {(self.p.dir / r[k]).resolve() for r in rows for k in ("rel_path", "thumb_rel", "proxy_rel") if r[k]}
        removed: list[str] = []
        now = time.time()
        for sub in ("assets", "thumbs", "proxies"):
            folder = self.p.dir / sub
            if not folder.is_dir():
                continue
            for f in folder.iterdir():
                try:
                    if f.is_file() and f.resolve() not in keep and now - f.stat().st_mtime >= min_age_s:
                        f.unlink()
                        removed.append(f"{sub}/{f.name}")
                except OSError:
                    continue
        for f in self.p.dir.glob("*.tmp"):  # a save that was interrupted before its final rename
            try:
                if now - f.stat().st_mtime >= min_age_s:
                    f.unlink()
                    removed.append(f.name)
            except OSError:
                continue
        return removed

    def remove(self, aid: str) -> None:
        """Remove an asset from the project. Copies and previews are deleted; linked originals are never touched."""
        a = self.get(aid)
        with self.p.db() as con:
            con.execute("DELETE FROM assets WHERE id=?", (aid,))
        for rel in (a["thumb_rel"], a["proxy_rel"], f"previews/{aid}.png", a["rel_path"] if a["mode"] == "copy" else None):
            if rel:
                try:
                    (self.p.dir / rel).unlink(missing_ok=True)
                except OSError as exc:
                    raise StorageError(
                        f"The asset was removed but a file could not be deleted: {exc.strerror or exc}"
                    ) from exc


class _FileProblem(MediaError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code, self.message = code, message
