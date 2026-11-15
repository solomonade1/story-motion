import { useCallback, useEffect, useState } from "react";
import type { Api } from "./api";
import { formatBytes } from "./format";
import { ACTIVE, type Job, type RenderInfo, type RenderResult } from "./types";
import { Badge, Banner, Progress } from "./ui";
import { useJobs } from "./useJobs";
import { useLeaveWarning } from "./useLeaveWarning";

/**
 * Render the storyboard. The worker refuses (with reasons) while the storyboard has problems; nothing is
 * rendered from unsaved edits; every render is a new file and is labelled draft or final.
 */
export function RenderPanel(props: { api: Api; projectId: string; ensureSaved: () => Promise<boolean>; onJumpToShot?: (id: string) => void }) {
  const { api, projectId } = props;
  const [renders, setRenders] = useState<RenderInfo[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<RenderResult | null>(null);
  const [starting, setStarting] = useState(false);

  const loadRenders = useCallback(async () => {
    try {
      const list = await api.listRenders(projectId);
      setRenders(list);
      setChosen((c) => c ?? list[0]?.file ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not list the renders.");
    }
  }, [api, projectId]);

  const onFinished = useCallback(
    (job: Job) => {
      if (job.kind !== "render") return;
      if (job.state === "completed" && job.result) {
        const r = job.result as unknown as RenderResult;
        setLastResult(r);
        setChosen(r.file);
      }
      void loadRenders();
    },
    [loadRenders],
  );
  const { jobs, active, cancel, refresh } = useJobs(api, projectId, onFinished);
  const renderJobs = jobs.filter((j) => j.kind === "render");
  const running = renderJobs.find((j) => ACTIVE.includes(j.state));
  useLeaveWarning(Boolean(running));
  const latest = renderJobs[0];

  useEffect(() => {
    void loadRenders();
  }, [loadRenders]);

  const start = async (draft: boolean) => {
    setError(null);
    setStarting(true);
    try {
      if (!(await props.ensureSaved())) {
        setError("Your latest edits could not be saved, so nothing was rendered. Fix the save problem first.");
        return;
      }
      await api.startRender(projectId, draft);
      await refresh(); // show the new job (and start polling) straight away
    } catch (e) {
      setError(e instanceof Error ? e.message : "The render could not start.");
    } finally {
      setStarting(false);
    }
  };

  const current = renders.find((r) => r.file === chosen) ?? null;
  const shown = lastResult && lastResult.file === chosen ? lastResult : null;
  return (
    <section className="panel inner" aria-label="Render">
      <h3>Render</h3>
      <p className="muted small">
        A draft is a quick 640×360 proxy with a "DRAFT" badge, for checking timing and motion. The final render is the full-size export. Both are made on this computer, offline, and each one is a new file: earlier renders are kept.
      </p>
      <div className="row wrap">
        <button className="primary" disabled={starting || Boolean(running)} onClick={() => void start(true)}>
          Render draft
        </button>
        <button disabled={starting || Boolean(running)} onClick={() => void start(false)}>
          Render final (full size)
        </button>
      </div>
      {error && (
        <Banner kind="error" onDismiss={() => setError(null)}>
          {error}
        </Banner>
      )}
      {running && (
        <div role="status" aria-live="polite">
          <p>
            {running.message ?? "Rendering…"} ({Math.round(running.progress * 100)}%)
          </p>
          <Progress value={running.progress} label="Render progress" />
          <button onClick={() => void cancel(running.id)}>Cancel render</button>
          <p className="muted small">Cancel takes effect when the current step finishes. Nothing is published if you cancel.</p>
        </div>
      )}
      {!running && latest?.state === "failed" && (
        <Banner kind="error">The last render failed: {latest.error ?? "unknown error"} Nothing was published.</Banner>
      )}
      {!running && latest?.state === "cancelled" && <Banner kind="info">The last render was cancelled. Nothing was published.</Banner>}
      {!running && latest?.state === "interrupted" && <Banner kind="warn">The last render was interrupted when the app closed. Nothing was published; render again.</Banner>}
      {renders.length > 0 && (
        <>
          <label className="field compact">
            Rendered videos
            <select value={chosen ?? ""} onChange={(e) => setChosen(e.target.value)}>
              {renders.map((r) => (
                <option key={r.file} value={r.file}>
                  {r.draft ? "Draft" : "Final"} · {new Date(r.modified * 1000).toLocaleString()} · {formatBytes(r.sizeBytes)}
                </option>
              ))}
            </select>
          </label>
          {current && (
            <div>
              <p>
                <Badge kind={current.draft ? "warn" : "ok"}>{current.draft ? "Draft proxy: not final quality" : "Final export"}</Badge>
              </p>
              <video className="player" controls preload="metadata" src={api.renderUrl(projectId, current.file)} aria-label={`${current.draft ? "Draft" : "Final"} render`} />
              {shown && (
                <p className="muted small">
                  {shown.width}×{shown.height} at {shown.fps} fps, {shown.frames} frames, checked after rendering (streams, length, no unplanned black frames).
                  {shown.seconds !== null && ` Rendered in ${shown.seconds} s.`}
                </p>
              )}
              {shown && shown.warnings.length > 0 && (
                <ul aria-label="Render warnings">
                  {shown.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
      {renders.length === 0 && !running && !active && <p className="muted">No renders yet.</p>}
    </section>
  );
}
