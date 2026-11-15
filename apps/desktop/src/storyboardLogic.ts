import type { SbEasing, SbLayer, SbLayerPose, SbScene, SbShot, Storyboard } from "./types";

/** Pure storyboard edits. Each returns a new storyboard and never mutates its input. */

export function allShots(sb: Storyboard): SbShot[] {
  return sb.scenes.flatMap((s) => s.shots);
}

export function endMs(sb: Storyboard): number {
  return allShots(sb).reduce((m, s) => Math.max(m, s.startMs + s.durationMs), 0);
}

export function uniqueId(prefix: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  let n = 1;
  while (used.has(`${prefix}-${n}`)) n += 1;
  return `${prefix}-${n}`;
}

export function slugify(name: string, taken: Iterable<string>): string {
  const base = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "character";
  const used = new Set(taken);
  return used.has(base) ? uniqueId(base, used) : base;
}

export function addScene(sb: Storyboard): Storyboard {
  const id = uniqueId("scene", sb.scenes.map((s) => s.id));
  const scene: SbScene = { id, title: `Scene ${sb.scenes.length + 1}`, text: "", characterIds: [], shots: [] };
  return { ...sb, scenes: [...sb.scenes, scene] };
}

/** A new shot starts where the timeline currently ends and runs up to 3 s (or to the end of the narration). */
export function addShot(sb: Storyboard, sceneId: string, narrationMs: number | null): { sb: Storyboard; shotId: string } {
  const shotId = uniqueId("shot", allShots(sb).map((s) => s.id));
  const start = endMs(sb);
  const room = narrationMs !== null && narrationMs > start ? narrationMs - start : 3000;
  const shot: SbShot = {
    id: shotId, startMs: start, durationMs: Math.max(1, Math.min(3000, room)), mode: "STATIC", imageAssetId: null, clipAssetId: null,
    characterIds: [], action: "", mustShow: [], avoid: [], preset: null,
    transition: { type: "cut", durationMs: 0 }, trimStartMs: 0, speed: 1, fitSpeed: false, layers: [],
  };
  return { sb: { ...sb, scenes: sb.scenes.map((s) => (s.id === sceneId ? { ...s, shots: [...s.shots, shot] } : s)) }, shotId };
}

export function updateShot(sb: Storyboard, shotId: string, patch: Partial<SbShot>): Storyboard {
  return { ...sb, scenes: sb.scenes.map((s) => ({ ...s, shots: s.shots.map((h) => (h.id === shotId ? { ...h, ...patch } : h)) })) };
}

export function removeShot(sb: Storyboard, shotId: string): Storyboard {
  return { ...sb, scenes: sb.scenes.map((s) => ({ ...s, shots: s.shots.filter((h) => h.id !== shotId) })) };
}

export function updateScene(sb: Storyboard, sceneId: string, patch: Partial<SbScene>): Storyboard {
  return { ...sb, scenes: sb.scenes.map((s) => (s.id === sceneId ? { ...s, ...patch } : s)) };
}

export function removeScene(sb: Storyboard, sceneId: string): Storyboard {
  return { ...sb, scenes: sb.scenes.filter((s) => s.id !== sceneId) };
}

function swap<T>(items: T[], i: number, j: number): T[] {
  if (i < 0 || j < 0 || i >= items.length || j >= items.length) return items;
  const out = [...items];
  [out[i], out[j]] = [out[j] as T, out[i] as T];
  return out;
}

/** Reorder a shot inside its scene. Times are NOT changed: any resulting gap/overlap is reported, not hidden. */
export function moveShot(sb: Storyboard, shotId: string, dir: -1 | 1): Storyboard {
  return {
    ...sb,
    scenes: sb.scenes.map((s) => {
      const i = s.shots.findIndex((h) => h.id === shotId);
      return i < 0 ? s : { ...s, shots: swap(s.shots, i, i + dir) };
    }),
  };
}

export function moveScene(sb: Storyboard, sceneId: string, dir: -1 | 1): Storyboard {
  const i = sb.scenes.findIndex((s) => s.id === sceneId);
  return { ...sb, scenes: swap(sb.scenes, i, i + dir) };
}

/** Explicit user action: keep order and durations, make every shot start where the previous one ends. */
export function reflow(sb: Storyboard): Storyboard {
  let t = 0;
  return {
    ...sb,
    scenes: sb.scenes.map((s) => ({
      ...s,
      shots: s.shots.map((h) => {
        const out = { ...h, startMs: t };
        t += h.durationMs;
        return out;
      }),
    })),
  };
}

/** Explicit user action: stretch or trim the last shot so the timeline ends exactly with the narration. */
export function fitLastToNarration(sb: Storyboard, narrationMs: number): Storyboard {
  const last = allShots(sb).at(-1);
  if (!last || narrationMs <= last.startMs) return sb;
  return updateShot(sb, last.id, { durationMs: narrationMs - last.startMs });
}

export function shotAt(sb: Storyboard, ms: number): SbShot | null {
  return allShots(sb).find((s) => ms >= s.startMs && ms < s.startMs + s.durationMs) ?? null;
}

export function parseWholeMs(text: string, min: number): number | null {
  if (!/^\d{1,9}$/.test(text.trim())) return null;
  const n = Number(text.trim());
  return n >= min ? n : null;
}

export function lines(text: string): string[] {
  return text.split(/\r?\n/).map((t) => t.trim()).filter(Boolean);
}

export function clock(ms: number): string {
  const total = Math.max(0, Math.round(ms));
  const m = Math.floor(total / 60000);
  const s = Math.floor((total % 60000) / 1000);
  return `${m}:${String(s).padStart(2, "0")}.${String(total % 1000).padStart(3, "0")}`;
}

/**
 * Make a shot's transition finish where the shot now starts: the cut moves earlier by the transition's length, so
 * the dissolve plays in the pause before the next line. Only the boundary moves; every other time is unchanged.
 * Returns the same storyboard when there is no room (first shot, a cut, or a neighbour too short).
 */
export function leadTransition(sb: Storyboard, shotId: string): Storyboard {
  const shots = allShots(sb);
  const i = shots.findIndex((s) => s.id === shotId);
  const cur = shots[i];
  const prev = shots[i - 1];
  if (!cur || !prev || cur.transition.type === "cut") return sb;
  const d = cur.transition.durationMs;
  if (prev.durationMs <= d || prev.startMs + prev.durationMs !== cur.startMs) return sb;
  const withPrev = updateShot(sb, prev.id, { durationMs: prev.durationMs - d });
  return updateShot(withPrev, cur.id, { startMs: cur.startMs - d, durationMs: cur.durationMs + d });
}

export function parseDb(text: string, min: number, max: number): number | null {
  if (!/^-?\d{1,3}(\.\d{1,2})?$/.test(text.trim())) return null;
  const n = Number(text.trim());
  return n >= min && n <= max ? n : null;
}

export function defaultLayer(assetId: string): SbLayer {
  return {
    assetId,
    start: { x: 0.25, y: 0.5, widthFrac: 0.25, rotateDeg: 0 },
    end: { x: 0.75, y: 0.5, widthFrac: 0.25, rotateDeg: 0 },
    easing: "easeInOut",
    pivotX: 0.5,
    pivotY: 0.5,
    swayDeg: 0,
    swayPeriodMs: 4000,
  };
}

/** The same easing curves the renderer uses. */
export function ease(kind: SbEasing, p: number): number {
  if (kind === "linear") return p;
  if (kind === "easeIn") return p * p;
  if (kind === "easeOut") return p * (2 - p);
  return p * p * (3 - 2 * p);
}

/** Where a layer is, and how it is turned, a fraction ``p`` (0..1) of the way through a shot of ``durationMs``. */
export function layerPoseAt(layer: SbLayer, p: number, durationMs: number): SbLayerPose {
  const q = Math.min(1, Math.max(0, p));
  const e = ease(layer.easing, q);
  const mix = (a: number, b: number) => a + (b - a) * e;
  const sway = layer.swayDeg ? layer.swayDeg * Math.sin((2 * Math.PI * q * durationMs) / layer.swayPeriodMs) : 0;
  return {
    x: mix(layer.start.x, layer.end.x),
    y: mix(layer.start.y, layer.end.y),
    widthFrac: mix(layer.start.widthFrac, layer.end.widthFrac),
    rotateDeg: mix(layer.start.rotateDeg, layer.end.rotateDeg) + sway,
  };
}

/** CSS that puts the layer's pivot at (x, y) of the stage and turns it clockwise about that pivot, as the render does. */
export function layerCss(layer: SbLayer, pose: SbLayerPose): Record<string, string> {
  const px = layer.pivotX * 100;
  const py = layer.pivotY * 100;
  return {
    position: "absolute",
    left: `${pose.x * 100}%`,
    top: `${pose.y * 100}%`,
    width: `${pose.widthFrac * 100}%`,
    transformOrigin: `${px}% ${py}%`,
    transform: `translate(-${px}%, -${py}%) rotate(${pose.rotateDeg}deg)`,
  };
}

export function parseNum(text: string, min: number, max: number): number | null {
  if (!/^-?\d{1,4}(\.\d{1,3})?$/.test(text.trim())) return null;
  const n = Number(text.trim());
  return n >= min && n <= max ? n : null;
}
