"""Check that every shot's filter output is bit-identical across runs (before x264 encoding).

Usage: python scripts/determinism_probe.py [runs]     (default 3)
This is how the rotate ``c=none`` non-reproducibility was found (ADR-0003).
"""

from __future__ import annotations

import sys
from pathlib import Path

from storymotion_media.contracts import load_manifest
from storymotion_media.ingest import verify_manifest_assets
from storymotion_media.render import build_segment_argv, plan_shots
from storymotion_media.toolchain import get_toolchain, run


def main() -> int:
    runs_n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tc = get_toolchain()
    root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "jonah"
    m = load_manifest(root / "manifest.json")
    infos = verify_manifest_assets(tc, m, root)
    bad = 0
    for plan in plan_shots(m, m.video.fps):
        runs: list[list[str]] = []
        for _ in range(runs_n):
            argv = [str(a) for a in build_segment_argv(tc, plan, m, infos, 1920, 1080, 24, Path("unused.mp4"))]
            argv = [*argv[: argv.index("-c:v")], "-f", "framemd5", "-"]
            proc = run(argv, timeout=600)
            if proc.returncode != 0:
                print(proc.stderr[-300:])
                return 2
            runs.append([ln.split(",")[-1] for ln in proc.stdout.splitlines() if not ln.startswith("#")])
        differing = sum(1 for k in range(len(runs[0])) if len({r[k] for r in runs}) > 1)
        bad += differing > 0
        print(
            f"{plan.shot.id:9s} {plan.effective_mode:10s} frames={len(runs[0])} differing_across_{runs_n}_runs={differing}"
        )
    print("RESULT:", "NON-DETERMINISTIC shots found" if bad else "all shots bit-identical across runs")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
