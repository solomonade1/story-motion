import { useCallback, useEffect, useState } from "react";
import type { Api } from "./api";
import { formatBytes } from "./format";
import { ACTIVE, type ExportInfo, type ExportResult, type Job } from "./types";
import { Banner, Progress } from "./ui";
import { useJobs } from "./useJobs";
import { useLeaveWarning } from "./useLeaveWarning";

/**
 * Take the storyboard elsewhere: a package for video editors (shot clips, audio, EDL + OpenTimelineIO timeline) and/or a brief
 * for AI models (structured description, keyframes, instructions) whose revised storyboard can be imported back.
 * Nothing is uploaded; this only writes a folder on this computer.
 */
const MODE_LABEL = { full: "For editing", brief: "AI brief", assets: "Independent assets" } as const;

export function ExportPanel(props: { api: Api; projectId: string; ensureSaved: () => Promise<boolean> }) {
  const { api, projectId } = props;
  const [exports, setExports] = useState<ExportInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [last, setLast] = useState<ExportResult | null>(null);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    try {
      setExports(await api.listExports(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not list the exports.");
    }
  }, [api, projectId]);

  const onFinished = useCallback(
    (job: Job) => {
      if (job.kind !== "export") return;
      if (job.state === "completed" && job.result) setLast(job.result as unknown as ExportResult);
      void load();
    },
    [load],
  );
  const { jobs, refresh, cancel } = useJobs(api, projectId, onFinished);
  const exportJobs = jobs.filter((j) => j.kind === "export");
  const running = exportJobs.find((j) => ACTIVE.includes(j.state));
  const latest = exportJobs[0];
  useLeaveWarning(Boolean(running));

  useEffect(() => {
    void load();
  }, [load]);

  const start = async (mode: "full" | "brief" | "assets") => {
    setError(null);
    setNotice(null);
    setStarting(true);
    try {
      if (!(await props.ensureSaved())) {
        setError("Your latest edits could not be saved, so nothing was exported. Fix the save problem first.");
        return;
      }
      await api.startExport(projectId, mode);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The export could not start.");
    } finally {
      setStarting(false);
    }
  };

  const open = async (folder: string) => {
    try {
      const r = await api.openExport(projectId, folder);
      setNotice(r.opened ? `Opened ${r.path}` : `This export is in: ${r.path}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the folder.");
    }
  };

  const busy = starting || Boolean(running);
  return (
    <section className="panel inner" aria-label="Export">
      <h3>Export</h3>
      <p className="muted small">
        Nothing is uploaded: an export is a folder on this computer. <strong>Independent assets</strong> are plain files that need no editor and no StoryMotion: every shot as its own
        exact-length clip with a small JSON file describing it, the narration and music as audio files, your original pictures and clips unchanged, an index, and checksums to prove nothing was altered.{" "}
        <strong>For editing</strong> saves each shot as a clip, the narration and music as audio files, and a
        timeline (OpenTimelineIO for DaVinci Resolve, EDL for Premiere and others) so you can fine-tune in a video editor. <strong>For AI models</strong> is a light
        brief: a structured description of every scene, shot, time and setting, still frames of each shot, and instructions, so a model can review the video or propose a
        better storyboard that you import back with "Import scene plan".
      </p>
      <div className="row wrap">
        <button className="primary" disabled={busy} onClick={() => void start("assets")}>
          Export independent assets
        </button>
        <button disabled={busy} onClick={() => void start("full")}>
          Export for editing
        </button>
        <button disabled={busy} onClick={() => void start("brief")}>
          Export brief for AI models
        </button>
      </div>
      <p className="muted small">
        The timeline files follow the formats' published structure but have not been tested in any editor yet. Check the first import, and tell us what does not work. Anything you give to an outside service is your choice:
        the brief contains your script text and still frames of your pictures.
      </p>
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
      {running && (
        <div role="status" aria-live="polite">
          <p>
            {running.message ?? "Exporting…"} ({Math.round(running.progress * 100)}%)
          </p>
          <Progress value={running.progress} label="Export progress" />
          <button onClick={() => void cancel(running.id)}>Cancel export</button>
        </div>
      )}
      {!running && latest?.state === "failed" && <Banner kind="error">The last export failed: {latest.error ?? "unknown error"} Nothing was published.</Banner>}
      {!running && latest?.state === "cancelled" && <Banner kind="info">The last export was cancelled. Nothing was published.</Banner>}
      {!running && last && (
        <Banner kind="ok">
          Export finished: {last.shots} shots, {last.files} files, {formatBytes(last.totalBytes)} in {last.seconds} s ({MODE_LABEL[last.mode]}).
        </Banner>
      )}
      {exports.length > 0 && (
        <ul className="export-list" aria-label="Exports">
          {exports.map((x) => (
            <li key={x.folder}>
              <strong>{MODE_LABEL[x.mode]}</strong> · {new Date(x.modified * 1000).toLocaleString()} · {formatBytes(x.sizeBytes)}{" "}
              <button onClick={() => void open(x.folder)} aria-label={`Show ${MODE_LABEL[x.mode].toLowerCase()} export from ${new Date(x.modified * 1000).toLocaleString()}`}>
                Show folder
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
