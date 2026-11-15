import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import type { Api } from "./api";
import { formatBytes, formatDuration } from "./format";
import { MEDIA_EXTENSIONS, hasNativePicker, pickPaths } from "./native";
import { ACTIVE, CATEGORIES, type Asset, type ImportResult, type Job } from "./types";
import { Badge, Banner, Dialog, Progress } from "./ui";
import { useJobs } from "./useJobs";
import { useLeaveWarning } from "./useLeaveWarning";

const NEWLINE = String.fromCharCode(10);
const KIND_ICON: Record<Asset["kind"], string> = { image: "🖼", audio: "🎵", video: "🎞" };

export function Media(props: { api: Api; projectId: string }) {
  const { api, projectId } = props;
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [paths, setPaths] = useState("");
  const [mode, setMode] = useState<"copy" | "link">("copy");
  const [relinking, setRelinking] = useState<Asset | null>(null);
  const [findFolder, setFindFolder] = useState(false);
  const [lastImport, setLastImport] = useState<ImportResult | null>(null);

  const load = useCallback(async () => {
    try {
      setAssets(await api.listAssets(projectId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the media.");
    }
  }, [api, projectId]);

  const onFinished = useCallback(
    (job: Job) => {
      void load();
      if (job.kind === "import" && job.result) setLastImport(job.result as ImportResult);
      if (job.kind === "check" && job.result?.counts) {
        const c = job.result.counts;
        setNotice(`Checked: ${c.ok ?? 0} fine, ${c.missing ?? 0} missing, ${c.changed ?? 0} changed.`);
      }
    },
    [load],
  );
  const { jobs, active, error: jobsError, refresh, cancel } = useJobs(api, projectId, onFinished);
  useLeaveWarning(active);

  useEffect(() => {
    void load();
  }, [load]);

  const guard = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work.");
    }
  };

  const browse = () =>
    void guard(async () => {
      const picked = await pickPaths({ multiple: true, filterName: "Media", extensions: MEDIA_EXTENSIONS });
      if (picked.length > 0) setPaths((p) => (p.trim() ? p.trimEnd() + NEWLINE : "") + picked.join(NEWLINE));
    });

  const startImport = (e: FormEvent) => {
    e.preventDefault();
    const list = paths.split("\n").map((p) => p.trim().replace(/^"(.*)"$/, "$1")).filter(Boolean);
    if (list.length === 0) return;
    setLastImport(null);
    void guard(async () => {
      await api.startImport(projectId, list, mode);
      setPaths("");
      await refresh();
    });
  };

  const shown = useMemo(() => (assets ?? []).filter((a) => filter === "all" || a.category === filter || a.status === filter), [assets, filter]);
  const missing = (assets ?? []).filter((a) => a.status !== "ok");

  return (
    <div>
      {error && (
        <Banner kind="error" onDismiss={() => setError(null)}>
          {error}
        </Banner>
      )}
      {notice && (
        <Banner kind="info" onDismiss={() => setNotice(null)}>
          {notice}
        </Banner>
      )}
      {missing.length > 0 && (
        <Banner
          kind="warn"
          action={
            <button onClick={() => setFindFolder(true)}>Find moved files in a folder…</button>
          }
        >
          {missing.length} file{missing.length === 1 ? " is" : "s are"} missing or changed. Your other media is unaffected. Use Relink on each one, or search a folder for them.
        </Banner>
      )}

      <section className="panel" aria-label="Import media">
        <h2>Add media</h2>
        <form onSubmit={startImport}>
          <label className="field">
            Full path of each file, one per line
            <textarea
              value={paths}
              onChange={(e) => setPaths(e.target.value)}
              rows={3}
              placeholder={"C:\\Users\\You\\Videos\\Scene 1.mp4\nC:\\Users\\You\\Pictures\\harbour.png"}
              spellCheck={false}
            />
          </label>
          <div className="row wrap">
            <fieldset className="inline">
              <legend className="sr-only">How to add the files</legend>
              <label className="check">
                <input type="radio" name="mode" checked={mode === "copy"} onChange={() => setMode("copy")} /> Copy into the project
              </label>
              <label className="check">
                <input type="radio" name="mode" checked={mode === "link"} onChange={() => setMode("link")} /> Link to the original
              </label>
            </fieldset>
            {hasNativePicker() && (
              <button type="button" onClick={browse}>
                Browse…
              </button>
            )}
            <button type="submit" className="primary" disabled={!paths.trim()}>
              Import
            </button>
          </div>
          <p className="muted small">
            Pictures (PNG, JPG, WebP), audio (WAV, MP3, AAC) and video (MP4, MOV). Your originals are never changed or moved.
            {mode === "link" ? " Linked files stay where they are; if you move them later, use Relink." : " Copies make the project self-contained."}
          </p>
        </form>
      </section>

      <Activity jobs={jobs} active={active} error={jobsError} onCancel={(id) => void guard(() => cancel(id))} lastImport={lastImport} />

      <section aria-label="Media library">
        <div className="bar">
          <h2>Library {assets && <span className="muted">({assets.length})</span>}</h2>
          <div className="row">
            <label className="row">
              <span className="sr-only">Filter</span>
              <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter media">
                <option value="all">Everything</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c.replace("_", " ")}
                  </option>
                ))}
                <option value="missing">Missing</option>
                <option value="changed">Changed</option>
              </select>
            </label>
            <button onClick={() => void guard(async () => { await api.startCheck(projectId, false); await refresh(); })} disabled={!assets?.length}>
              Check files
            </button>
          </div>
        </div>
        {assets === null && !error && <p aria-live="polite">Loading media…</p>}
        {assets?.length === 0 && (
          <div className="empty">
            <h3>No media yet</h3>
            <p className="muted">Add pictures, clips and narration above. Each one gets a preview so you can check it.</p>
          </div>
        )}
        <ul className="grid" aria-label="Media items">
          {shown.map((a) => (
            <AssetCard
              key={a.id}
              asset={a}
              thumb={a.thumbUrl ? api.mediaUrl(projectId, a.id, "thumbs") : null}
              onCategory={(c) => void guard(async () => { await api.setCategory(projectId, a.id, c); await load(); })}
              onRelink={() => setRelinking(a)}
              onRemove={() => void guard(async () => { await api.removeAsset(projectId, a.id); await load(); })}
            />
          ))}
        </ul>
      </section>

      {relinking && (
        <PathDialog
          title={`Relink "${relinking.orig_name}"`}
          help="Give the full path of the same file in its new location. It must be identical to the original."
          label="New path"
          confirm="Relink"
          browse={() => pickPaths({ multiple: false })}
          onClose={() => setRelinking(null)}
          onSubmit={async (p) => {
            await api.relink(projectId, relinking.id, p);
            setRelinking(null);
            setNotice(`Relinked "${relinking.orig_name}".`);
            await load();
          }}
        />
      )}
      {findFolder && (
        <PathDialog
          title="Find moved files"
          help="Choose a folder. StoryMotion searches it (and the folders inside) for files that match your missing media."
          label="Folder path"
          confirm="Search"
          browse={() => pickPaths({ directory: true })}
          onClose={() => setFindFolder(false)}
          onSubmit={async (p) => {
            const r = await api.relinkFolder(projectId, p);
            setFindFolder(false);
            setNotice(`Relinked ${r.relinked.length}; ${r.stillMissing.length} still missing (searched ${r.scanned} files).`);
            await load();
          }}
        />
      )}
    </div>
  );
}

function AssetCard(props: { asset: Asset; thumb: string | null; onCategory: (c: string) => void; onRelink: () => void; onRemove: () => void }) {
  const a = props.asset;
  const meta = [
    a.width && a.height ? `${a.width}×${a.height}` : "",
    a.duration_ms ? formatDuration(a.duration_ms) : "",
    a.fps ? `${Math.round(a.fps)} fps` : "",
    formatBytes(a.size),
  ].filter(Boolean);
  return (
    <li className={`asset ${a.status !== "ok" ? "problem" : ""}`}>
      <div className="thumb">
        {props.thumb ? <img src={props.thumb} alt={`Preview of ${a.orig_name}`} loading="lazy" /> : <span aria-hidden="true">{KIND_ICON[a.kind]}</span>}
      </div>
      <div className="asset-body">
        <div className="asset-name" title={a.orig_name}>
          {a.orig_name}
        </div>
        <div className="muted small">{meta.join(" · ")}</div>
        <div className="row wrap">
          {a.status === "ok" ? <Badge kind="ok">OK</Badge> : <Badge kind="fail">{a.status === "missing" ? "Missing" : "Changed"}</Badge>}
          <Badge kind="info">{a.mode === "copy" ? "Copied" : "Linked"}</Badge>
        </div>
        {a.status_detail && <div className={`small ${a.status === "ok" ? "muted" : "fix"}`}>{a.status_detail}</div>}
        <label className="field compact">
          <span className="sr-only">Category of {a.orig_name}</span>
          <select value={a.category} onChange={(e) => props.onCategory(e.target.value)} aria-label={`Category of ${a.orig_name}`}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <div className="row wrap">
          {a.status !== "ok" && <button onClick={props.onRelink}>Relink…</button>}
          <button className="link danger" onClick={props.onRemove} aria-label={`Remove ${a.orig_name}`}>
            Remove
          </button>
        </div>
      </div>
    </li>
  );
}

export function Activity(props: { jobs: Job[]; active: boolean; error: string | null; onCancel: (id: string) => void; lastImport: ImportResult | null }) {
  const recent = props.jobs.slice(0, 4);
  if (recent.length === 0 && !props.lastImport) return null;
  const label: Record<string, string> = { import: "Import", check: "File check" };
  return (
    <section className="panel" aria-label="Activity" aria-live="polite">
      <h2>Activity</h2>
      {props.error && <Banner kind="warn">{props.error}</Banner>}
      <ul className="list">
        {recent.map((j) => (
          <li key={j.id}>
            <div className="row between">
              <span>
                <strong>{label[j.kind] ?? j.kind}</strong> · {j.message}
              </span>
              {ACTIVE.includes(j.state) ? (
                <button onClick={() => props.onCancel(j.id)}>Cancel</button>
              ) : (
                <Badge kind={j.state === "completed" ? "ok" : j.state === "failed" ? "fail" : "warn"}>{j.state}</Badge>
              )}
            </div>
            {ACTIVE.includes(j.state) && <Progress value={j.progress} label={`${label[j.kind] ?? j.kind} progress`} />}
            {j.error && <div className="fix small">{j.error}</div>}
          </li>
        ))}
      </ul>
      {props.lastImport && <ImportSummary result={props.lastImport} />}
    </section>
  );
}

function ImportSummary({ result }: { result: ImportResult }) {
  return (
    <div className="summary">
      <p>
        <strong>{result.imported.length}</strong> added
        {result.duplicates.length > 0 && <>, <strong>{result.duplicates.length}</strong> already in the project</>}
        {result.errors.length > 0 && <>, <strong>{result.errors.length}</strong> could not be imported</>}
        {result.cancelled && " (cancelled)"}.
      </p>
      {result.duplicates.map((d) => (
        <p key={d.path} className="muted small">
          {d.message}
        </p>
      ))}
      {result.errors.length > 0 && (
        <ul className="errors" aria-label="Files that could not be imported">
          {result.errors.map((e) => (
            <li key={e.path}>{e.message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PathDialog(props: {
  title: string;
  help: string;
  label: string;
  confirm: string;
  onClose: () => void;
  onSubmit: (path: string) => Promise<void>;
  browse?: () => Promise<string[]>;
}) {
  const [value, setValue] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await props.onSubmit(value.trim().replace(/^"(.*)"$/, "$1"));
    } catch (x) {
      setErr(x instanceof Error ? x.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title={props.title} onClose={props.onClose} wide>
      <form onSubmit={(e) => void submit(e)}>
        <p className="muted">{props.help}</p>
        <label className="field">
          {props.label}
          <input value={value} onChange={(e) => setValue(e.target.value)} spellCheck={false} />
        </label>
        {props.browse && hasNativePicker() && (
          <button
            type="button"
            onClick={() =>
              void props.browse?.().then(
                (picked) => picked[0] && setValue(picked[0]),
                (x: unknown) => setErr(x instanceof Error ? x.message : "Could not open the file chooser."),
              )
            }
          >
            Browse…
          </button>
        )}
        {err && <Banner kind="error">{err}</Banner>}
        <div className="row end">
          <button type="button" onClick={props.onClose}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={!value.trim() || busy}>
            {busy ? "Working…" : props.confirm}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
