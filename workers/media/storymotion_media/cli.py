"""Command line for the Phase 0 headless proof of concept."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .contracts import export_json_schema, load_manifest
from .errors import StoryMotionError
from .generation_demo import run_mock_generation
from .ingest import verify_manifest_assets
from .plan import build_manifest
from .preview import build_preview
from .render import RenderOptions, render
from .scan import scan_project
from .studio.api import ApiServer, watch_stdin_and_exit
from .studio.locking import WorkspaceLock
from .studio.paths import default_workspace
from .studio.store import Workspace
from .timing_check import check_render
from .toolchain import get_toolchain

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "tests" / "fixtures" / "jonah"
DEMO_MARKER = ".storymotion-demo-project"


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def cmd_doctor(_: argparse.Namespace) -> int:
    tc = get_toolchain()
    print(f"OK  {tc.description}\nOK  ffprobe {tc.ffprobe}")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    path = Path(a.manifest)
    m = load_manifest(path)
    print(f"schema OK: {len(m.shots)} shots, {len(m.assets)} assets, narration {m.narration.durationMs} ms")
    if a.check_assets:
        infos = verify_manifest_assets(get_toolchain(), m, path.parent)
        print(f"assets OK: {len(infos)} verified (hash + decodable)")
    return 0


def cmd_render(a: argparse.Namespace) -> int:
    mpath = Path(a.manifest)
    m = load_manifest(mpath)
    out = Path(a.output)
    rep = render(m, mpath.parent, out, RenderOptions(draft=a.draft, overwrite=a.overwrite, keep_work=a.keep_work))
    _write_json(out.with_suffix(".report.json"), asdict(rep))
    v = rep.verification
    print(
        f"rendered {out} ({rep.output['sizeBytes'] / 1e6:.1f} MB) in {rep.timings_s['total']}s; "
        f"{v['video']['width']}x{v['video']['height']}@{v['video']['fps']} {v['video']['frames']} frames; "
        f"A/V delta {v['videoVsAudioDeltaMs']} ms; sha256 {rep.output['sha256'][:16]}..."
    )
    for w in rep.warnings:
        print("WARNING:", w)
    return 0


def cmd_preview(a: argparse.Namespace) -> int:
    mpath = Path(a.manifest)
    page, rep = build_preview(
        load_manifest(mpath), mpath.parent, Path(a.out_dir), get_toolchain(), overwrite=a.overwrite
    )
    print(f"preview ready: {page}  (draft {rep.width}x{rep.height}; open it in a browser)")
    return 0


def cmd_scan(a: argparse.Namespace) -> int:
    root = Path(a.project).resolve()
    res = scan_project(get_toolchain(), root)
    out = root / "assets.scan.json"
    _write_json(out, {"assets": res.assets, "problems": res.problems, "warnings": res.warnings})
    print(f"scanned {root.name}: {len(res.assets)} usable asset(s) -> {out.name}")
    for kind, items in (("PROBLEM", res.problems), ("WARNING", res.warnings)):
        for it in items:
            print(f"{kind}: {it}")
    return 1 if res.problems else 0


def cmd_build(a: argparse.Namespace) -> int:
    root = Path(a.project).resolve()
    plan = json.loads((root / a.plan).read_text(encoding="utf-8"))
    m = build_manifest(get_toolchain(), root, plan)
    out = root / a.manifest
    out.write_text(m.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"manifest written: {out} ({len(m.shots)} shots, narration {m.narration.durationMs} ms)")
    return 0


def cmd_serve(a: argparse.Namespace) -> int:
    """Run the local API for the desktop shell / browser UI. Prints one JSON 'ready' line, then serves."""
    root = Path(a.workspace) if a.workspace else default_workspace()
    root.mkdir(parents=True, exist_ok=True)
    lock = WorkspaceLock(root)
    lock.acquire()  # raises a clear error if another StoryMotion already has this workspace open
    ws = Workspace(root)
    static = Path(a.static) if a.static else REPO / "apps" / "desktop" / "dist"
    server = ApiServer(
        ws, port=a.port, static_dir=static if static.is_dir() else None, allowed_origins=set(a.origin or [])
    )
    print(
        json.dumps(
            {
                "event": "ready",
                "port": server.port,
                "token": server.token,
                "url": f"http://127.0.0.1:{server.port}/#token={server.token}",
                "workspace": str(ws.root),
            }
        ),
        flush=True,
    )
    if a.exit_on_stdin_close:
        watch_stdin_and_exit(server)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        lock.release()
    return 0


def cmd_schema(a: argparse.Namespace) -> int:
    _write_json(Path(a.output), export_json_schema())
    print(f"wrote {a.output}")
    return 0


def cmd_phase0(a: argparse.Namespace) -> int:
    """Reproduce the whole Phase 0 demonstration from committed fixtures."""
    tc = get_toolchain()
    out = Path(a.out_dir).resolve()
    proj = out / "jonah-project"
    out.mkdir(parents=True, exist_ok=True)
    if proj.exists():
        if not (proj / DEMO_MARKER).exists():
            raise StoryMotionError(f"{proj} exists and is not a demo workspace; not touching it")
        shutil.rmtree(proj)
    shutil.copytree(FIXTURE, proj)
    (proj / DEMO_MARKER).write_text("disposable copy of tests/fixtures/jonah\n", encoding="utf-8")
    base = load_manifest(proj / "manifest.json")
    print(f"[1/4] manifest valid: {len(base.shots)} shots, narration {base.narration.durationMs} ms")

    opts = RenderOptions(overwrite=True)
    local = out / "jonah_phase0_local_only.mp4"
    rep1 = render(base, proj, local, opts, tc)
    _write_json(local.with_suffix(".report.json"), asdict(rep1))
    print(f"[2/4] cloud-free render OK: {local.name} in {rep1.timings_s['total']}s")

    m2, glog = run_mock_generation(tc, base, proj, "shot-07a", simulate_user_approval=True)
    _write_json(proj / "manifest.with_mock_clip.json", json.loads(m2.model_dump_json()))
    _write_json(out / "mock_generation_log.json", glog)
    print(f"[3/4] MOCK provider flow OK (no network, no real spend): job {glog['job']['id']}")

    clip = out / "jonah_phase0_with_mock_clip.mp4"
    rep2 = render(m2, proj, clip, opts, tc)
    _write_json(clip.with_suffix(".report.json"), asdict(rep2))
    print(f"[4/4] render with mock clip OK: {clip.name} in {rep2.timings_s['total']}s")

    page, _ = build_preview(m2, proj, out / "preview", tc, overwrite=True)
    print(f"preview: {page}")
    for r in (rep1, rep2):
        print(f"  {r.output['file']}  sha256={r.output['sha256']}")
    return 0


def cmd_launch(a: argparse.Namespace) -> int:
    """Open the Studio in its own app window (Edge app mode); closing the window stops the worker."""
    from .launcher import run_cli_launch

    return run_cli_launch(Path(a.workspace) if a.workspace else None, Path(a.static) if a.static else None)


def cmd_timing_check(a: argparse.Namespace) -> int:
    """Where do the cuts in a rendered video really land, compared with the render report (QG TIME-04)?"""
    video = Path(a.video)
    report = Path(a.report) if a.report else video.with_suffix(".json")
    result = check_render(get_toolchain(), video, report)
    print(json.dumps(result, indent=2))
    return 0 if result["withinTime04"] or not result["hardCutsExpected"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="storymotion-media", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check FFmpeg/ffprobe readiness").set_defaults(fn=cmd_doctor)
    v = sub.add_parser("validate", help="validate a scene manifest")
    v.add_argument("manifest")
    v.add_argument("--check-assets", action="store_true", help="also hash + probe every asset")
    v.set_defaults(fn=cmd_validate)
    r = sub.add_parser("render", help="render a manifest to MP4")
    r.add_argument("manifest")
    r.add_argument("output")
    r.add_argument("--draft", action="store_true")
    r.add_argument("--overwrite", action="store_true")
    r.add_argument("--keep-work", action="store_true")
    r.set_defaults(fn=cmd_render)
    pv = sub.add_parser("preview", help="draft render + preview.html")
    pv.add_argument("manifest")
    pv.add_argument("out_dir")
    pv.add_argument("--overwrite", action="store_true")
    pv.set_defaults(fn=cmd_preview)
    sc = sub.add_parser("scan", help="register the media in a project drop-folder")
    sc.add_argument("project")
    sc.set_defaults(fn=cmd_scan)
    b = sub.add_parser("build", help="plan.json + scanned folder -> manifest.json")
    b.add_argument("project")
    b.add_argument("--plan", default="plan.json")
    b.add_argument("--manifest", default="manifest.json")
    b.set_defaults(fn=cmd_build)
    ln = sub.add_parser("launch", help="open the Studio in its own app window (no browser tabs, no setup)")
    ln.add_argument("--workspace", help="folder for projects (default: ~/StoryMotion Studio or $STORYMOTION_WORKSPACE)")
    ln.add_argument("--static", help="built UI folder (default: apps/desktop/dist)")
    ln.set_defaults(fn=cmd_launch)
    tcp = sub.add_parser("timing-check", help="measure cut timing of a render against its report (TIME-04)")
    tcp.add_argument("video")
    tcp.add_argument("--report", help="render report JSON (default: <video>.json next to it)")
    tcp.set_defaults(fn=cmd_timing_check)
    sv = sub.add_parser("serve", help="run the local API for the desktop app / browser UI")
    sv.add_argument("--workspace", help="folder for projects (default: ~/StoryMotion Studio or $STORYMOTION_WORKSPACE)")
    sv.add_argument("--port", type=int, default=0)
    sv.add_argument("--static", help="built UI folder to serve (default: apps/desktop/dist)")
    sv.add_argument(
        "--origin", action="append", help="extra allowed browser origin (e.g. the dev server or the app shell)"
    )
    sv.add_argument(
        "--exit-on-stdin-close", action="store_true", help="exit when the parent closes stdin (used by the shell)"
    )
    sv.set_defaults(fn=cmd_serve)
    s = sub.add_parser("schema", help="export the manifest JSON Schema")
    s.add_argument("output")
    s.set_defaults(fn=cmd_schema)
    d = sub.add_parser("phase0", help="reproduce the full Phase 0 demo from fixtures")
    d.add_argument("--out-dir", default=str(REPO / "out"))
    d.set_defaults(fn=cmd_phase0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.fn(args))
    except StoryMotionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
