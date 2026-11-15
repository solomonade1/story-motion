import type { Asset, Health, Job, ProjectDoc, ProjectSummary, ExportInfo, ProjectView, RenderInfo, Storyboard, StoryboardView, TrashItem } from "./types";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly issues: { path: string; message: string }[];
  constructor(status: number, code: string, message: string, issues: { path: string; message: string }[] = []) {
    super(message);
    this.issues = issues;
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type ClientConfig = { origin: string; token: string };

/** The shell (or the `serve` command) hands over the session token in the URL fragment, which is never sent to a server. */
export function readConfig(loc: Pick<Location, "origin" | "hash">): ClientConfig | null {
  const params = new URLSearchParams(loc.hash.replace(/^#/, ""));
  const token = params.get("token");
  if (!token) return null;
  const api = params.get("api") ?? loc.origin;
  return { origin: api.replace(/\/$/, ""), token };
}

/** The app window starts the worker with its native file chooser on and says so in the URL fragment (`picker=1`). */
export function workerPickerEnabled(loc: Pick<Location, "hash">): boolean {
  return new URLSearchParams(loc.hash.replace(/^#/, "")).get("picker") === "1";
}

export type PickRequest = { kind: "files" | "folder"; multiple?: boolean; extensions?: string[]; filterName?: string };

export interface Api {
  pick(req: PickRequest): Promise<string[]>;
  health(): Promise<Health>;
  listProjects(archived: boolean): Promise<ProjectSummary[]>;
  createProject(name: string): Promise<ProjectDoc>;
  getProject(id: string): Promise<ProjectView>;
  renameProject(id: string, name: string): Promise<ProjectDoc>;
  setArchived(id: string, archived: boolean): Promise<ProjectDoc>;
  duplicateProject(id: string): Promise<ProjectDoc>;
  deleteProject(id: string): Promise<{ trashId: string }>;
  listTrash(): Promise<TrashItem[]>;
  restore(trashId: string): Promise<ProjectDoc>;
  purge(trashId: string): Promise<void>;
  saveDocument(id: string, patch: Partial<Pick<ProjectDoc, "script" | "notes">>, baseRevision: number): Promise<ProjectDoc>;
  listAssets(id: string): Promise<Asset[]>;
  startImport(id: string, paths: string[], mode: "copy" | "link", category?: string): Promise<Job>;
  startCheck(id: string, verifyHash: boolean): Promise<Job>;
  relink(id: string, assetId: string, path: string): Promise<Asset>;
  relinkFolder(id: string, folder: string): Promise<{ relinked: string[]; stillMissing: string[]; scanned: number }>;
  setCategory(id: string, assetId: string, category: string): Promise<Asset>;
  removeAsset(id: string, assetId: string): Promise<void>;
  listJobs(id: string): Promise<Job[]>;
  cancelJob(id: string, jobId: string): Promise<Job>;
  getStoryboard(id: string): Promise<StoryboardView>;
  saveStoryboard(id: string, storyboard: Storyboard, baseRevision: number): Promise<StoryboardView>;
  importScript(id: string, text: string, filename: string, replace: boolean, baseRevision: number): Promise<StoryboardView>;
  importPlan(id: string, text: string, replace: boolean, baseRevision: number): Promise<StoryboardView>;
  startExport(id: string, mode: "full" | "brief" | "assets"): Promise<Job>;
  listExports(id: string): Promise<ExportInfo[]>;
  openExport(id: string, folder: string): Promise<{ opened: boolean; path: string }>;
  startRender(id: string, draft: boolean): Promise<Job>;
  listRenders(id: string): Promise<RenderInfo[]>;
  renderUrl(projectId: string, file: string): string;
  mediaUrl(projectId: string, assetId: string, which: "thumbs" | "proxies" | "alpha"): string;
}

export class ApiClient implements Api {
  constructor(
    private readonly cfg: ClientConfig,
    private readonly fetchImpl: typeof fetch = (...a) => fetch(...a),
  ) {}

  private async req<T>(method: string, path: string, body?: unknown): Promise<T> {
    let res: Response;
    try {
      res = await this.fetchImpl(`${this.cfg.origin}${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${this.cfg.token}`,
          ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError(0, "unreachable", "The StoryMotion worker is not responding. Close and reopen the app.");
    }
    const text = await res.text();
    let data: unknown = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      /* a non-JSON error page */
    }
    if (!res.ok) {
      const e = (data as { error?: { code?: string; message?: string; issues?: { path: string; message: string }[] } } | null)?.error;
      throw new ApiError(res.status, e?.code ?? "http_error", e?.message ?? `The request failed (${res.status}).`, e?.issues ?? []);
    }
    return data as T;
  }

  pick = async (req: PickRequest) => (await this.req<{ paths: string[] }>("POST", "/api/pick", req)).paths;
  health = () => this.req<Health>("GET", "/api/health");
  listProjects = async (archived: boolean) =>
    (await this.req<{ projects: ProjectSummary[] }>("GET", `/api/projects?archived=${archived ? 1 : 0}`)).projects;
  createProject = (name: string) => this.req<ProjectDoc>("POST", "/api/projects", { name });
  getProject = (id: string) => this.req<ProjectView>("GET", `/api/projects/${id}`);
  renameProject = (id: string, name: string) => this.req<ProjectDoc>("PATCH", `/api/projects/${id}`, { name });
  setArchived = (id: string, archived: boolean) => this.req<ProjectDoc>("PATCH", `/api/projects/${id}`, { archived });
  duplicateProject = (id: string) => this.req<ProjectDoc>("POST", `/api/projects/${id}/duplicate`, {});
  deleteProject = (id: string) => this.req<{ trashId: string }>("DELETE", `/api/projects/${id}`);
  listTrash = async () => (await this.req<{ trash: TrashItem[] }>("GET", "/api/trash")).trash;
  restore = (trashId: string) => this.req<ProjectDoc>("POST", `/api/trash/${trashId}/restore`, {});
  purge = async (trashId: string) => {
    await this.req("POST", `/api/trash/${trashId}/purge`, { confirm: true });
  };
  saveDocument = (id: string, patch: Partial<Pick<ProjectDoc, "script" | "notes">>, baseRevision: number) =>
    this.req<ProjectDoc>("PUT", `/api/projects/${id}/document`, { ...patch, baseRevision });
  listAssets = async (id: string) => (await this.req<{ assets: Asset[] }>("GET", `/api/projects/${id}/assets`)).assets;
  startImport = (id: string, paths: string[], mode: "copy" | "link", category?: string) =>
    this.req<Job>("POST", `/api/projects/${id}/assets/import`, { paths, mode, ...(category ? { category } : {}) });
  startCheck = (id: string, verifyHash: boolean) => this.req<Job>("POST", `/api/projects/${id}/assets/check`, { verifyHash });
  relink = (id: string, assetId: string, path: string) =>
    this.req<Asset>("POST", `/api/projects/${id}/assets/${assetId}/relink`, { path });
  relinkFolder = (id: string, folder: string) =>
    this.req<{ relinked: string[]; stillMissing: string[]; scanned: number }>("POST", `/api/projects/${id}/assets/relink-folder`, { folder });
  setCategory = (id: string, assetId: string, category: string) =>
    this.req<Asset>("PATCH", `/api/projects/${id}/assets/${assetId}`, { category });
  removeAsset = async (id: string, assetId: string) => {
    await this.req("DELETE", `/api/projects/${id}/assets/${assetId}`);
  };
  listJobs = async (id: string) => (await this.req<{ jobs: Job[] }>("GET", `/api/projects/${id}/jobs`)).jobs;
  cancelJob = (id: string, jobId: string) => this.req<Job>("POST", `/api/projects/${id}/jobs/${jobId}/cancel`, {});
  getStoryboard = (id: string) => this.req<StoryboardView>("GET", `/api/projects/${id}/storyboard`);
  saveStoryboard = (id: string, storyboard: Storyboard, baseRevision: number) =>
    this.req<StoryboardView>("PUT", `/api/projects/${id}/storyboard`, { storyboard, baseRevision });
  importScript = (id: string, text: string, filename: string, replace: boolean, baseRevision: number) =>
    this.req<StoryboardView>("POST", `/api/projects/${id}/storyboard/import-script`, { text, filename, replace, baseRevision });
  importPlan = (id: string, text: string, replace: boolean, baseRevision: number) =>
    this.req<StoryboardView>("POST", `/api/projects/${id}/storyboard/import-plan`, { text, replace, baseRevision });
  startExport = (id: string, mode: "full" | "brief" | "assets") => this.req<Job>("POST", `/api/projects/${id}/storyboard/export`, { mode });
  listExports = async (id: string) => (await this.req<{ exports: ExportInfo[] }>("GET", `/api/projects/${id}/exports`)).exports;
  openExport = (id: string, folder: string) => this.req<{ opened: boolean; path: string }>("POST", `/api/projects/${id}/exports/${folder}/open`, {});
  startRender = (id: string, draft: boolean) => this.req<Job>("POST", `/api/projects/${id}/storyboard/render`, { draft });
  listRenders = async (id: string) => (await this.req<{ renders: RenderInfo[] }>("GET", `/api/projects/${id}/renders`)).renders;
  renderUrl = (projectId: string, file: string) =>
    `${this.cfg.origin}/api/projects/${projectId}/renders/${file}?token=${encodeURIComponent(this.cfg.token)}`;
  mediaUrl = (projectId: string, assetId: string, which: "thumbs" | "proxies" | "alpha") =>
    `${this.cfg.origin}/api/projects/${projectId}/assets/${assetId}/${which}?token=${encodeURIComponent(this.cfg.token)}`;
}
