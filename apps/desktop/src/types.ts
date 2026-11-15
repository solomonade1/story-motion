export type Check = { id: string; label: string; status: "ok" | "warn" | "fail"; detail: string; fix: string };
export type Health = {
  ok: boolean;
  checks: Check[];
  version: string;
  projectSchema: string;
  uptimeSeconds: number;
  pid: number;
  workspace: string;
};
export type ProjectSummary = { id: string; name: string; created_at: string; updated_at: string; archived: number };
export type ProjectDoc = {
  schemaVersion: string;
  projectId: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  revision: number;
  archived: boolean;
  script: string;
  notes: string;
};
export type ProjectView = { document: ProjectDoc; warnings: string[]; migrated: string[]; assetCounts: Record<string, number> };
export type TrashItem = { trashId: string; projectId: string; name: string };
export type AssetStatus = "ok" | "missing" | "changed";
export type Asset = {
  id: string;
  category: string;
  kind: "image" | "audio" | "video";
  mode: "copy" | "link";
  orig_name: string;
  size: number;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  fps: number | null;
  sample_rate: number | null;
  status: AssetStatus;
  status_detail: string | null;
  thumbUrl: string | null;
  proxyUrl: string | null;
  path_hint: string | null;
};
export type JobState = "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted";
export type ImportFileError = { path: string; code: string; message: string };
export type ImportResult = {
  imported: Asset[];
  duplicates: { path: string; existingId: string; existingName: string; message: string }[];
  errors: ImportFileError[];
  cancelled: boolean;
};
export type Job = {
  id: string;
  kind: string;
  state: JobState;
  progress: number;
  message: string | null;
  error: string | null;
  result: (Partial<ImportResult> & { counts?: Record<string, number> }) | null;
  created_at: string;
};
export const CATEGORIES = ["character", "environment", "prop", "audio", "generated_video", "rendered_video", "effect"] as const;
export const ACTIVE: JobState[] = ["queued", "running"];

export type SbMode = "STATIC" | "CINEMATIC" | "LAYERED" | "RENDERED" | "GENERATIVE";
export type SbShot = {
  id: string;
  startMs: number;
  durationMs: number;
  mode: SbMode;
  imageAssetId: string | null;
  clipAssetId: string | null;
  characterIds: string[];
  action: string;
  mustShow: string[];
  avoid: string[];
  preset: string | null;
  transition: { type: "cut" | "crossfade" | "fadeblack"; durationMs: number };
  trimStartMs: number;
  speed: number;
  fitSpeed: boolean;
  layers: SbLayer[];
};
export type SbEasing = "linear" | "easeIn" | "easeOut" | "easeInOut";
export type SbLayerPose = { x: number; y: number; widthFrac: number; rotateDeg: number };
export type SbLayer = {
  assetId: string;
  start: SbLayerPose;
  end: SbLayerPose;
  easing: SbEasing;
  pivotX: number;
  pivotY: number;
  swayDeg: number;
  swayPeriodMs: number;
};
export type SbAudioTrack = {
  assetId: string;
  role: "music" | "ambience";
  gainDb: number;
  startMs: number;
  fadeInMs: number;
  fadeOutMs: number;
  loop: boolean;
  duckDb: number;
};
export type SbScene = { id: string; title: string; text: string; characterIds: string[]; shots: SbShot[] };
export type SbCharacter = { id: string; name: string };
export type Storyboard = {
  storyboardVersion: string;
  narrationAssetId: string | null;
  fadeInMs: number;
  fadeOutMs: number;
  audioTracks: SbAudioTrack[];
  characters: SbCharacter[];
  scenes: SbScene[];
};
export type Diagnostic = { severity: "error" | "warning" | "info"; code: string; where: string; message: string; shotId: string | null };
export type StoryboardView = { storyboard: Storyboard; narrationMs: number | null; diagnostics: Diagnostic[]; revision: number };
export const MODES: SbMode[] = ["STATIC", "CINEMATIC", "LAYERED", "RENDERED", "GENERATIVE"];
export const PRESETS = ["slow-push-in", "slow-pull-out", "pan-left", "pan-right", "reveal", "hold"] as const;

export type RenderInfo = { file: string; draft: boolean; sizeBytes: number; modified: number };
export type RenderResult = {
  file: string;
  draft: boolean;
  sha256: string;
  sizeBytes: number;
  frames: number;
  width: number;
  height: number;
  fps: number;
  seconds: number | null;
  warnings: string[];
  fallbacks: { shot: string; usedMode: string; reason: string }[];
  fidelity: string;
};

export type ExportInfo = { folder: string; mode: "full" | "brief" | "assets"; sizeBytes: number; modified: number };
export type ExportResult = { folder: string; mode: "full" | "brief" | "assets"; shots: number; files: number; totalBytes: number; seconds: number };
