import { ApiError, type Api } from "../api";
import type { Asset, Health, Job, ProjectDoc, ProjectSummary, ExportInfo, ProjectView, RenderInfo, Storyboard, StoryboardView, TrashItem } from "../types";

const now = "2026-11-14T10:00:00Z";

export function makeAsset(over: Partial<Asset> = {}): Asset {
  return {
    id: "a-000000000001", category: "environment", kind: "image", mode: "copy", orig_name: "harbour.png", size: 2048, width: 1920,
    height: 1080, duration_ms: null, fps: null, sample_rate: null, status: "ok", status_detail: null, thumbUrl: "thumbs/a", proxyUrl: "proxies/a",
    path_hint: "assets/a.png", ...over,
  };
}

export function makeJob(over: Partial<Job> = {}): Job {
  return { id: "j-000000000001", kind: "import", state: "completed", progress: 1, message: "Done", error: null, result: null, created_at: now, ...over };
}

/** In-memory Api for UI tests. Set `fail` to make the next call(s) of a method throw. */
export class FakeApi implements Api {
  health_: Health = {
    ok: true, version: "0.0.1", projectSchema: "1.0.0", uptimeSeconds: 1, pid: 1, workspace: "C:\\Workspace",
    checks: [{ id: "ffmpeg", label: "FFmpeg + ffprobe", status: "ok", detail: "ffmpeg 9", fix: "" }],
  };
  projects: ProjectSummary[] = [];
  trash: TrashItem[] = [];
  docs = new Map<string, ProjectDoc>();
  assets: Asset[] = [];
  jobs: Job[] = [];
  fail = new Map<string, Error>();
  calls: { method: string; args: unknown[] }[] = [];
  warnings: string[] = [];
  private n = 0;

  private rec(method: string, args: unknown[]) {
    this.calls.push({ method, args });
    const err = this.fail.get(method);
    if (err) {
      this.fail.delete(method);
      throw err;
    }
  }
  called(method: string) {
    return this.calls.filter((c) => c.method === method);
  }

  addProject(name: string, extra: Partial<ProjectDoc> = {}): ProjectDoc {
    const id = `p-${String(++this.n).padStart(12, "0")}`;
    const doc: ProjectDoc = {
      schemaVersion: "1.0.0", projectId: id, name, createdAt: now, updatedAt: now, revision: 0, archived: false, script: "", notes: "", ...extra,
    };
    this.docs.set(id, doc);
    this.projects.push({ id, name, created_at: now, updated_at: now, archived: doc.archived ? 1 : 0 });
    return doc;
  }

  picked: string[] = [];
  async pick() {
    this.rec("pick", []);
    return this.picked;
  }
  async health() {
    this.rec("health", []);
    return this.health_;
  }
  async listProjects(archived: boolean) {
    this.rec("listProjects", [archived]);
    return this.projects.filter((p) => Boolean(p.archived) === archived);
  }
  async createProject(name: string) {
    this.rec("createProject", [name]);
    return this.addProject(name);
  }
  async getProject(id: string): Promise<ProjectView> {
    this.rec("getProject", [id]);
    const d = this.docs.get(id);
    if (!d) throw new ApiError(404, "project_not_found", "That project no longer exists.");
    return { document: { ...d }, warnings: this.warnings, migrated: [], assetCounts: {} };
  }
  async renameProject(id: string, name: string) {
    this.rec("renameProject", [id, name]);
    const d = this.docs.get(id)!;
    d.name = name;
    const p = this.projects.find((x) => x.id === id)!;
    p.name = name;
    return d;
  }
  async setArchived(id: string, archived: boolean) {
    this.rec("setArchived", [id, archived]);
    const d = this.docs.get(id)!;
    d.archived = archived;
    this.projects.find((x) => x.id === id)!.archived = archived ? 1 : 0;
    return d;
  }
  async duplicateProject(id: string) {
    this.rec("duplicateProject", [id]);
    return this.addProject(`${this.docs.get(id)!.name} (copy)`);
  }
  async deleteProject(id: string) {
    this.rec("deleteProject", [id]);
    const d = this.docs.get(id)!;
    this.projects = this.projects.filter((p) => p.id !== id);
    const trashId = `${id}-20261114T100000Z`;
    this.trash.push({ trashId, projectId: id, name: d.name });
    return { trashId };
  }
  async listTrash() {
    this.rec("listTrash", []);
    return this.trash;
  }
  async restore(trashId: string) {
    this.rec("restore", [trashId]);
    const t = this.trash.find((x) => x.trashId === trashId)!;
    this.trash = this.trash.filter((x) => x !== t);
    const d = this.docs.get(t.projectId)!;
    this.projects.push({ id: d.projectId, name: d.name, created_at: now, updated_at: now, archived: 0 });
    return d;
  }
  async purge(trashId: string) {
    this.rec("purge", [trashId]);
    this.trash = this.trash.filter((x) => x.trashId !== trashId);
  }
  async saveDocument(id: string, patch: Partial<Pick<ProjectDoc, "script" | "notes">>, baseRevision: number) {
    this.rec("saveDocument", [id, patch, baseRevision]);
    const d = this.docs.get(id)!;
    if (baseRevision !== d.revision) throw new ApiError(409, "stale_revision", "This project changed since you opened it. Reload before saving.");
    Object.assign(d, patch, { revision: d.revision + 1 });
    return { ...d };
  }
  async listAssets(id: string) {
    this.rec("listAssets", [id]);
    return this.assets;
  }
  async startImport(id: string, paths: string[], mode: "copy" | "link", category?: string) {
    this.rec("startImport", [id, paths, mode, category]);
    const job = makeJob({ id: `j-${String(++this.n).padStart(12, "0")}`, state: "running", progress: 0.2, message: "Importing…" });
    this.jobs.unshift(job);
    return job;
  }
  async startCheck(id: string, verifyHash: boolean) {
    this.rec("startCheck", [id, verifyHash]);
    const job = makeJob({ id: `j-${String(++this.n).padStart(12, "0")}`, kind: "check", state: "running", progress: 0.1, message: "Checking…" });
    this.jobs.unshift(job);
    return job;
  }
  async relink(id: string, assetId: string, path: string) {
    this.rec("relink", [id, assetId, path]);
    const a = this.assets.find((x) => x.id === assetId)!;
    a.status = "ok";
    a.status_detail = null;
    return a;
  }
  async relinkFolder(id: string, folder: string) {
    this.rec("relinkFolder", [id, folder]);
    return { relinked: [], stillMissing: [], scanned: 0 };
  }
  async setCategory(id: string, assetId: string, category: string) {
    this.rec("setCategory", [id, assetId, category]);
    const a = this.assets.find((x) => x.id === assetId)!;
    a.category = category;
    return a;
  }
  async removeAsset(id: string, assetId: string) {
    this.rec("removeAsset", [id, assetId]);
    this.assets = this.assets.filter((a) => a.id !== assetId);
  }
  async listJobs(id: string) {
    this.rec("listJobs", [id]);
    return this.jobs.map((j) => ({ ...j }));
  }
  async cancelJob(id: string, jobId: string) {
    this.rec("cancelJob", [id, jobId]);
    const j = this.jobs.find((x) => x.id === jobId)!;
    j.state = "cancelled";
    j.message = "Cancelled";
    return j;
  }
  renders: RenderInfo[] = [];
  exports: ExportInfo[] = [];
  openedPath = { opened: true, path: "C:/Workspace/exports/x-000000000001-full" };
  async startExport(id: string, mode: "full" | "brief" | "assets") {
    this.rec("startExport", [id, mode]);
    const job = makeJob({ id: `j-${String(++this.n).padStart(12, "0")}`, kind: "export", state: "running", progress: 0.4, message: "Encoding shot 2 of 5" });
    this.jobs.unshift(job);
    return job;
  }
  async listExports(id: string) {
    this.rec("listExports", [id]);
    return this.exports;
  }
  async openExport(id: string, folder: string) {
    this.rec("openExport", [id, folder]);
    return this.openedPath;
  }
  async startRender(id: string, draft: boolean) {
    this.rec("startRender", [id, draft]);
    const job = makeJob({ id: `j-${String(++this.n).padStart(12, "0")}`, kind: "render", state: "running", progress: 0.3, message: "Encoding shot 1 of 2" });
    this.jobs.unshift(job);
    return job;
  }
  async listRenders(id: string) {
    this.rec("listRenders", [id]);
    return this.renders;
  }
  renderUrl(projectId: string, file: string) {
    return `http://api.test/api/projects/${projectId}/renders/${file}?token=T`;
  }
  storyboards = new Map<string, { sb: Storyboard; revision: number }>();
  private sbState(id: string) {
    let st = this.storyboards.get(id);
    if (!st) {
      st = { sb: { storyboardVersion: "1.1.0", narrationAssetId: null, fadeInMs: 0, fadeOutMs: 0, audioTracks: [], characters: [], scenes: [] }, revision: 0 };
      this.storyboards.set(id, st);
    }
    return st;
  }
  private sbView(id: string): StoryboardView {
    const st = this.sbState(id);
    const nar = this.assets.find((a) => a.id === st.sb.narrationAssetId);
    return { storyboard: structuredClone(st.sb), narrationMs: nar?.duration_ms ?? null, diagnostics: this.diagnostics, revision: st.revision };
  }
  diagnostics: StoryboardView["diagnostics"] = [];
  async getStoryboard(id: string) {
    this.rec("getStoryboard", [id]);
    return this.sbView(id);
  }
  async saveStoryboard(id: string, storyboard: Storyboard, baseRevision: number) {
    this.rec("saveStoryboard", [id, structuredClone(storyboard), baseRevision]);
    const st = this.sbState(id);
    if (baseRevision !== st.revision) throw new ApiError(409, "stale_revision", "This project changed since you opened it. Reload before saving.");
    for (const sh of storyboard.scenes.flatMap((s) => s.shots)) {
      if (!Number.isInteger(sh.durationMs) || sh.durationMs <= 0) {
        throw new ApiError(422, "invalid_plan", "1 problem(s) found. Nothing was saved.", [{ path: "scenes[0].shots[0].durationMs", message: "Input should be greater than 0" }]);
      }
    }
    st.sb = structuredClone(storyboard);
    st.revision += 1;
    return this.sbView(id);
  }
  async importScript(id: string, text: string, filename: string, replace: boolean, baseRevision: number) {
    this.rec("importScript", [id, text, filename, replace, baseRevision]);
    const st = this.sbState(id);
    if (st.sb.scenes.some((s) => s.shots.length) && !replace) throw new ApiError(400, "invalid_input", "This project already has shots. Confirm the replacement to continue.");
    const paras = text.split(/\r?\n\s*\n/).filter((p) => p.trim());
    st.sb = { ...st.sb, scenes: paras.map((p, i) => ({ id: `scene-${i + 1}`, title: `Scene ${i + 1}`, text: p.trim(), characterIds: [], shots: [] })) };
    st.revision += 1;
    return this.sbView(id);
  }
  async importPlan(id: string, text: string, replace: boolean, baseRevision: number) {
    this.rec("importPlan", [id, text, replace, baseRevision]);
    const st = this.sbState(id);
    let raw: Storyboard;
    try {
      raw = JSON.parse(text) as Storyboard;
    } catch {
      throw new ApiError(422, "invalid_plan", "1 problem(s) found. Nothing was saved.", [{ path: "line 1, column 2", message: "invalid JSON: Expecting value" }]);
    }
    if (st.sb.scenes.length && !replace) throw new ApiError(400, "invalid_input", "This project already has a storyboard. Confirm the replacement to continue.");
    st.sb = raw;
    st.revision += 1;
    return this.sbView(id);
  }
  mediaUrl(projectId: string, assetId: string, which: "thumbs" | "proxies" | "alpha") {
    return `http://api.test/api/projects/${projectId}/assets/${assetId}/${which}?token=T`;
  }
}
