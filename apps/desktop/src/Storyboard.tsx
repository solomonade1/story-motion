import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type Api } from "./api";
import {
  addScene, addShot, allShots, clock, endMs, fitLastToNarration, leadTransition, lines, moveScene, moveShot, reflow, removeScene,
  removeShot, shotAt, slugify, updateScene, updateShot,
} from "./storyboardLogic";
import { MODES, PRESETS, type Asset, type Diagnostic, type SbMode, type SbShot, type Storyboard as Board } from "./types";
import { AudioPanel } from "./AudioPanel";
import { MsField } from "./Fields";
import { LayerEditor } from "./LayerEditor";
import { ExportPanel } from "./ExportPanel";
import { RenderPanel } from "./RenderPanel";
import { Badge, Banner, Dialog } from "./ui";

type SaveState = "saved" | "dirty" | "saving" | "error" | "conflict";
const STATE_TEXT: Record<SaveState, string> = {
  saved: "All changes saved",
  dirty: "Unsaved changes…",
  saving: "Saving…",
  error: "Could not save",
  conflict: "This project was changed somewhere else",
};
const EMPTY: Board = { storyboardVersion: "1.1.0", narrationAssetId: null, fadeInMs: 0, fadeOutMs: 0, audioTracks: [], characters: [], scenes: [] };

function readText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result ?? ""));
    r.onerror = () => reject(r.error ?? new Error("read failed"));
    r.readAsText(file);
  });
}

type Pending = { kind: "script" | "plan"; text: string; filename: string };

export function Storyboard(props: { api: Api; projectId: string }) {
  const { api, projectId } = props;
  const [sb, setSb] = useState<Board | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);
  const [narrationMs, setNarrationMs] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [state, setState] = useState<SaveState>("saved");
  const [message, setMessage] = useState("");
  const [issues, setIssues] = useState<{ path: string; message: string }[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [scrub, setScrub] = useState(0);
  const [undo, setUndo] = useState<{ label: string; sb: Board } | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [confirmScene, setConfirmScene] = useState<string | null>(null);

  const revision = useRef(0);
  const latest = useRef<Board | null>(null);
  const dirty = useRef(false);
  const saving = useRef(false);
  const conflict = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const [view, list] = await Promise.all([api.getStoryboard(projectId), api.listAssets(projectId)]);
      revision.current = view.revision;
      latest.current = view.storyboard;
      dirty.current = false;
      conflict.current = false;
      setSb(view.storyboard);
      setAssets(list);
      setDiagnostics(view.diagnostics);
      setNarrationMs(view.narrationMs);
      setState("saved");
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Could not open the storyboard.");
    }
  }, [api, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const flush = useCallback(async (): Promise<void> => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (saving.current || !dirty.current || conflict.current || !latest.current) return;
    const snapshot = latest.current;
    dirty.current = false;
    saving.current = true;
    setState("saving");
    try {
      const view = await api.saveStoryboard(projectId, snapshot, revision.current);
      revision.current = view.revision;
      setDiagnostics(view.diagnostics);
      setNarrationMs(view.narrationMs);
      setIssues([]);
      setMessage("");
      if (dirty.current) {
        setState("dirty");
        timer.current = setTimeout(() => void flush(), 0);
      } else {
        setState("saved");
      }
    } catch (e) {
      dirty.current = true; // never drop an edit
      if (e instanceof ApiError && e.code === "stale_revision") {
        conflict.current = true;
        setState("conflict");
      } else {
        setState("error");
        if (e instanceof ApiError) setIssues(e.issues);
      }
      setMessage(e instanceof Error ? e.message : "Could not save.");
    } finally {
      saving.current = false;
    }
  }, [api, projectId]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      void flush();
    },
    [flush],
  );

  /** Save pending edits and report whether everything is on disk (a render must never use stale or unsaved data). */
  const ensureSaved = useCallback(async (): Promise<boolean> => {
    for (let i = 0; i < 100; i++) {
      if (conflict.current) return false;
      if (saving.current) {
        await new Promise((r) => setTimeout(r, 50));
        continue;
      }
      if (!dirty.current) return true;
      await flush();
      if (dirty.current && !saving.current) return false; // the save failed: the edits stay on screen, nothing renders
    }
    return false;
  }, [flush]);

  /** Every edit goes through here: remember the previous version for Undo, then autosave after a quiet moment. */
  const edit = useCallback(
    (fn: (b: Board) => Board, label?: string) => {
      const cur = latest.current ?? EMPTY;
      const next = fn(cur);
      if (next === cur) return;
      if (label) setUndo({ label, sb: cur });
      latest.current = next;
      dirty.current = true;
      setSb(next);
      if (!conflict.current) {
        setState((s) => (s === "saving" ? s : "dirty"));
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(() => void flush(), 800);
      }
    },
    [flush],
  );

  const runImport = useCallback(
    async (p: Pending, replace: boolean) => {
      try {
        const view =
          p.kind === "script"
            ? await api.importScript(projectId, p.text, p.filename, replace, revision.current)
            : await api.importPlan(projectId, p.text, replace, revision.current);
        revision.current = view.revision;
        latest.current = view.storyboard;
        dirty.current = false;
        setSb(view.storyboard);
        setDiagnostics(view.diagnostics);
        setNarrationMs(view.narrationMs);
        setIssues([]);
        setMessage("");
        setPending(null);
        setSelected(null);
        setState("saved");
      } catch (e) {
        if (e instanceof ApiError && e.code === "invalid_input" && /replace/i.test(e.message)) {
          setPending(p); // ask first; never replace silently
          return;
        }
        setPending(null);
        setIssues(e instanceof ApiError ? e.issues : []);
        setMessage(e instanceof Error ? e.message : "The import failed.");
        setState(e instanceof ApiError && e.code === "stale_revision" ? "conflict" : "error");
        if (e instanceof ApiError && e.code === "stale_revision") conflict.current = true;
      }
    },
    [api, projectId],
  );

  const onFile = async (kind: "script" | "plan", file: File | undefined) => {
    if (!file) return;
    if (dirty.current) await flush();
    let text: string;
    try {
      text = await readText(file);
    } catch {
      setIssues([]);
      setMessage(`${file.name} could not be read. Check that the file still exists and try again.`);
      setState("error");
      return;
    }
    await runImport({ kind, text, filename: file.name }, false);
  };

  const byId = useMemo(() => new Map(assets.map((a) => [a.id, a])), [assets]);
  const images = assets.filter((a) => a.kind === "image");
  const clips = assets.filter((a) => a.kind === "video");
  const audio = assets.filter((a) => a.kind === "audio");

  if (loadError && !sb) {
    return (
      <Banner kind="error" action={<button onClick={() => void load()}>Try again</button>}>
        {loadError}
      </Banner>
    );
  }
  if (!sb) return <p aria-live="polite">Opening the storyboard…</p>;

  const shots = allShots(sb);
  const total = Math.max(narrationMs ?? 0, endMs(sb), 1000);
  const sel = shots.find((s) => s.id === selected) ?? null;
  const atScrub = shotAt(sb, scrub);
  const flagged = new Map<string, Diagnostic["severity"]>();
  for (const d of diagnostics) {
    if (!d.shotId) continue;
    if (d.severity === "error" || !flagged.has(d.shotId)) flagged.set(d.shotId, d.severity);
  }

  return (
    <section className="panel" aria-label="Storyboard">
      <div className="bar">
        <h2>Storyboard</h2>
        <div className={`save-state ${state}`} role="status" aria-live="polite">
          {STATE_TEXT[state]}
        </div>
      </div>
      {state === "error" && (
        <Banner kind="error" action={<button onClick={() => void flush()}>Try again</button>}>
          {message} Your edits are still here and have not been lost.
          {issues.length > 0 && (
            <ul>
              {issues.slice(0, 8).map((i) => (
                <li key={`${i.path}-${i.message}`}>
                  <code>{i.path}</code> {i.message}
                </li>
              ))}
            </ul>
          )}
        </Banner>
      )}
      {state === "conflict" && (
        <Banner kind="warn" action={<button onClick={() => void load()}>Reload storyboard</button>}>
          {message}
        </Banner>
      )}
      {undo && (
        <Banner
          kind="info"
          onDismiss={() => setUndo(null)}
          action={
            <button
              onClick={() => {
                const prev = undo.sb;
                setUndo(null);
                edit(() => prev);
              }}
            >
              Undo
            </button>
          }
        >
          {undo.label}
        </Banner>
      )}

      <div className="row wrap">
        <label className="field compact">
          Narration (the clock for every shot)
          <select value={sb.narrationAssetId ?? ""} onChange={(e) => edit((b) => ({ ...b, narrationAssetId: e.target.value || null }))}>
            <option value="">— choose the narration —</option>
            {audio.map((a) => (
              <option key={a.id} value={a.id}>
                {a.orig_name}
                {a.duration_ms ? ` (${clock(a.duration_ms)})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="button-like">
          Import script (.txt, .md)
          <input type="file" accept=".txt,.md,.markdown,text/plain,text/markdown" hidden onChange={(e) => { void onFile("script", e.target.files?.[0]); e.target.value = ""; }} />
        </label>
        <label className="button-like">
          Import scene plan (.json)
          <input type="file" accept=".json,application/json" hidden onChange={(e) => { void onFile("plan", e.target.files?.[0]); e.target.value = ""; }} />
        </label>
      </div>
      {narrationMs !== null && <p className="muted small">Narration length: {clock(narrationMs)}. Shot times are whole milliseconds on this clock.</p>}

      <Characters sb={sb} edit={edit} />

      <div className="row wrap">
        <MsField label="Video fade-in (ms)" value={sb.fadeInMs} min={0} onCommit={(n) => edit((b) => ({ ...b, fadeInMs: n }))} />
        <MsField label="Video fade-out (ms)" value={sb.fadeOutMs} min={0} onCommit={(n) => edit((b) => ({ ...b, fadeOutMs: n }))} />
      </div>
      <AudioPanel sb={sb} audio={audio.filter((a) => a.id !== sb.narrationAssetId)} edit={edit} />

      <h3>Timeline</h3>
      {shots.length === 0 ? (
        <p className="muted">No shots yet. Add a scene, then add shots to it, or import a script or plan.</p>
      ) : (
        <>
          <div className="timeline" role="group" aria-label="Timeline">
            {shots.map((s) => (
              <button
                key={s.id}
                className={`tl-shot ${flagged.get(s.id) ?? ""} ${s.id === selected ? "active" : ""}`}
                style={{ left: `${(s.startMs / total) * 100}%`, width: `${Math.max(0.6, (s.durationMs / total) * 100)}%` }}
                aria-label={`Shot ${s.id}, ${clock(s.startMs)} to ${clock(s.startMs + s.durationMs)}${flagged.has(s.id) ? ", has a problem" : ""}`}
                aria-pressed={s.id === selected}
                onClick={() => setSelected(s.id)}
                title={`${s.id}: ${s.startMs}–${s.startMs + s.durationMs} ms`}
              >
                {s.id}
              </button>
            ))}
            {narrationMs !== null && <div className="tl-end" style={{ left: `${(narrationMs / total) * 100}%` }} title="End of narration" />}
          </div>
          <label className="field compact">
            Scrub: {clock(scrub)} / {clock(total)}
            <input type="range" min={0} max={total} step={10} value={Math.min(scrub, total)} aria-label="Scrub position" onChange={(e) => setScrub(Number(e.target.value))} />
          </label>
          <div className="scrub-preview" aria-live="polite">
            <p className="muted small">Draft preview: a still of the shot at this moment. Motion, transitions and audio are not shown; the final export is the reference.</p>
            {atScrub ? (
              <p>
                <strong>{atScrub.id}</strong> ({atScrub.mode}){atScrub.action ? ` — ${atScrub.action}` : ""}
              </p>
            ) : (
              <p className="muted">No shot at this moment (gap or past the last shot).</p>
            )}
            {atScrub?.imageAssetId && byId.get(atScrub.imageAssetId)?.proxyUrl ? (
              <img className="still" alt={`Draft still for ${atScrub.id}`} src={api.mediaUrl(projectId, atScrub.imageAssetId, "proxies")} />
            ) : atScrub?.mode === "RENDERED" && atScrub.clipAssetId && byId.get(atScrub.clipAssetId)?.thumbUrl ? (
              <img className="still" alt={`Clip poster for ${atScrub.id} (first frame, not the frame at this moment)`} src={api.mediaUrl(projectId, atScrub.clipAssetId, "thumbs")} />
            ) : null}
          </div>
          <div className="row wrap">
            <button onClick={() => edit(reflow, "Shot times were re-flowed back to back.")} title="Keep order and durations; each shot starts when the previous one ends">
              Close gaps and overlaps
            </button>
            <button disabled={narrationMs === null} onClick={() => narrationMs !== null && edit((b) => fitLastToNarration(b, narrationMs), "The last shot was fitted to the narration.")}>
              Fit last shot to narration end
            </button>
          </div>
        </>
      )}

      <Diagnostics items={diagnostics} onPick={(id) => setSelected(id)} />

      <h3>Scenes and shots</h3>
      {sb.scenes.map((sc, si) => (
        <article key={sc.id} className="scene" aria-label={`Scene ${sc.title || sc.id}`}>
          <div className="row wrap between">
            <label className="field compact grow">
              Scene title
              <input value={sc.title} maxLength={200} onChange={(e) => edit((b) => updateScene(b, sc.id, { title: e.target.value }))} />
            </label>
            <div className="row">
              <button aria-label={`Move scene ${sc.title || sc.id} up`} disabled={si === 0} onClick={() => edit((b) => moveScene(b, sc.id, -1))}>↑</button>
              <button aria-label={`Move scene ${sc.title || sc.id} down`} disabled={si === sb.scenes.length - 1} onClick={() => edit((b) => moveScene(b, sc.id, 1))}>↓</button>
              <button onClick={() => (sc.shots.length ? setConfirmScene(sc.id) : edit((b) => removeScene(b, sc.id), `Scene "${sc.title || sc.id}" was removed.`))}>Remove scene</button>
            </div>
          </div>
          {sc.text && <p className="muted small passage">{sc.text}</p>}
          <ul className="shot-list">
            {sc.shots.map((h, hi) => (
              <li key={h.id} className={h.id === selected ? "active" : ""}>
                <button className="link" onClick={() => setSelected(h.id)} aria-pressed={h.id === selected}>
                  {h.id}
                </button>
                <span className="muted small">
                  {clock(h.startMs)} · {(h.durationMs / 1000).toFixed(2)} s · {h.mode}
                </span>
                {flagged.has(h.id) && <Badge kind={flagged.get(h.id) === "error" ? "fail" : "warn"}>{flagged.get(h.id) === "error" ? "problem" : "check"}</Badge>}
                <span className="row">
                  <button aria-label={`Move shot ${h.id} up`} disabled={hi === 0} onClick={() => edit((b) => moveShot(b, h.id, -1))}>↑</button>
                  <button aria-label={`Move shot ${h.id} down`} disabled={hi === sc.shots.length - 1} onClick={() => edit((b) => moveShot(b, h.id, 1))}>↓</button>
                </span>
              </li>
            ))}
          </ul>
          <button
            onClick={() => {
              const r = addShot(latest.current ?? sb, sc.id, narrationMs);
              edit(() => r.sb);
              setSelected(r.shotId);
            }}
          >
            Add shot to this scene
          </button>
        </article>
      ))}
      <button onClick={() => edit(addScene)}>Add scene</button>

      <RenderPanel api={api} projectId={projectId} ensureSaved={ensureSaved} />
      <ExportPanel api={api} projectId={projectId} ensureSaved={ensureSaved} />

      {sel && (
        <ShotEditor
          key={sel.id}
          shot={sel}
          board={sb}
          images={images}
          clips={clips}
          api={api}
          projectId={projectId}
          isFirst={shots[0]?.id === sel.id}
          canLead={leadTransition(sb, sel.id) !== sb}
          onLead={() => edit((b) => leadTransition(b, sel.id), "The cut was moved earlier so the transition finishes where the shot started.")}
          onChange={(patch) => edit((b) => updateShot(b, sel.id, patch))}
          onRemove={() => {
            edit((b) => removeShot(b, sel.id), `Shot ${sel.id} was removed.`);
            setSelected(null);
          }}
        />
      )}

      {pending && (
        <Dialog title="Replace the current storyboard?" onClose={() => setPending(null)}>
          <p>
            This project already has {pending.kind === "script" ? "shots" : "a storyboard"}. Importing <strong>{pending.filename}</strong> replaces the scenes{pending.kind === "script" ? " and their shots" : ""}. The narration choice and characters are kept for scripts.
          </p>
          <div className="row end">
            <button onClick={() => setPending(null)}>Keep what I have</button>
            <button className="primary" onClick={() => void runImport(pending, true)}>
              Replace it
            </button>
          </div>
        </Dialog>
      )}
      {confirmScene && (
        <Dialog title="Remove this scene and its shots?" onClose={() => setConfirmScene(null)}>
          <p>The scene and all of its shots are removed from the storyboard. You can undo this right afterwards.</p>
          <div className="row end">
            <button onClick={() => setConfirmScene(null)}>Cancel</button>
            <button
              className="primary"
              onClick={() => {
                const id = confirmScene;
                setConfirmScene(null);
                edit((b) => removeScene(b, id), "The scene was removed.");
              }}
            >
              Remove scene
            </button>
          </div>
        </Dialog>
      )}
    </section>
  );
}

function Characters(props: { sb: Board; edit: (fn: (b: Board) => Board, label?: string) => void }) {
  const { sb, edit } = props;
  const [name, setName] = useState("");
  const add = () => {
    const n = name.trim();
    if (!n) return;
    edit((b) => ({ ...b, characters: [...b.characters, { id: slugify(n, b.characters.map((c) => c.id)), name: n }] }));
    setName("");
  };
  return (
    <div className="characters">
      <div className="row wrap">
        <label className="field compact">
          Add a character
          <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} />
        </label>
        <button onClick={add} disabled={!name.trim()}>
          Add character
        </button>
      </div>
      {sb.characters.length > 0 && (
        <ul className="chips" aria-label="Characters">
          {sb.characters.map((c) => (
            <li key={c.id}>
              {c.name}{" "}
              <button
                className="link"
                aria-label={`Remove character ${c.name}`}
                onClick={() =>
                  edit(
                    (b) => ({
                      ...b,
                      characters: b.characters.filter((x) => x.id !== c.id),
                      scenes: b.scenes.map((s) => ({ ...s, characterIds: s.characterIds.filter((x) => x !== c.id), shots: s.shots.map((h) => ({ ...h, characterIds: h.characterIds.filter((x) => x !== c.id) })) })),
                    }),
                    `Character ${c.name} was removed from the cast and from every shot.`,
                  )
                }
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Diagnostics(props: { items: Diagnostic[]; onPick: (shotId: string) => void }) {
  if (props.items.length === 0) return <p className="muted small" role="status">No timing problems found.</p>;
  return (
    <div className="diagnostics" role="region" aria-label="Timeline problems">
      <h3>Timeline checks ({props.items.length})</h3>
      <ul>
        {props.items.map((d, i) => (
          <li key={`${d.code}-${d.where}-${i}`} className={d.severity}>
            <Badge kind={d.severity === "error" ? "fail" : d.severity === "warning" ? "warn" : "info"}>{d.severity === "error" ? "Problem" : d.severity === "warning" ? "Check" : "Note"}</Badge>{" "}
            {d.message}{" "}
            {d.shotId && (
              <button className="link" onClick={() => props.onPick(d.shotId as string)}>
                Show {d.shotId}
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ShotEditor(props: {
  shot: SbShot;
  board: Board;
  images: Asset[];
  clips: Asset[];
  api: Api;
  projectId: string;
  isFirst: boolean;
  canLead: boolean;
  onLead: () => void;
  onChange: (patch: Partial<SbShot>) => void;
  onRemove: () => void;
}) {
  const { shot, board, images, clips } = props;
  const [must, setMust] = useState(shot.mustShow.join("\n"));
  const [avoid, setAvoid] = useState(shot.avoid.join("\n"));
  const isImageMode = shot.mode === "STATIC" || shot.mode === "CINEMATIC" || shot.mode === "LAYERED";
  const chosen = images.find((a) => a.id === shot.imageAssetId);
  return (
    <section className="panel inner" aria-label={`Edit shot ${shot.id}`}>
      <div className="row between">
        <h3>Shot {shot.id}</h3>
        <button onClick={props.onRemove}>Remove shot</button>
      </div>
      <div className="row wrap">
        <MsField label="Start (ms)" value={shot.startMs} min={0} onCommit={(n) => props.onChange({ startMs: n })} />
        <MsField label="Duration (ms)" value={shot.durationMs} min={1} onCommit={(n) => props.onChange({ durationMs: n })} />
        <label className="field compact">
          Animation mode
          <select value={shot.mode} onChange={(e) => props.onChange({ mode: e.target.value as SbMode })}>
            {MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="field compact">
          Motion preset
          <select value={shot.preset ?? ""} onChange={(e) => props.onChange({ preset: e.target.value || null })}>
            <option value="">none</option>
            {PRESETS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="muted small">The preset is saved with the shot. Applying it to the rendered motion arrives in the next step of this phase.</p>
      <div className="row wrap">
        <label className="field compact">
          Transition into this shot
          <select
            value={shot.transition.type}
            disabled={props.isFirst}
            onChange={(e) => {
              const type = e.target.value as SbShot["transition"]["type"];
              const keep = shot.transition.durationMs >= 100 ? shot.transition.durationMs : 500;
              props.onChange({ transition: type === "cut" ? { type, durationMs: 0 } : { type, durationMs: keep } });
            }}
          >
            <option value="cut">Cut</option>
            <option value="crossfade">Crossfade (dissolve)</option>
            <option value="fadeblack">Dip to black</option>
          </select>
        </label>
        {shot.transition.type !== "cut" && (
          <MsField label="Transition length (ms)" value={shot.transition.durationMs} min={100} onCommit={(n) => props.onChange({ transition: { ...shot.transition, durationMs: n } })} />
        )}
        {shot.transition.type !== "cut" && (
          <button disabled={!props.canLead} onClick={props.onLead} title="Moves the cut earlier by the transition length, so it finishes where this shot starts now">
            Finish the transition where this shot starts
          </button>
        )}
      </div>
      {props.isFirst && <p className="muted small">The first shot starts with a cut. Use the video fade-in (above the timeline) instead.</p>}
      {shot.transition.type !== "cut" && <p className="muted small">A transition starts when this shot starts and lasts the length above.</p>}
      {shot.mode === "RENDERED" && (
        <div className="row wrap">
          <MsField label="Trim start of clip (ms)" value={shot.trimStartMs} min={0} onCommit={(n) => props.onChange({ trimStartMs: n })} />
          <label className="field compact">
            Clip speed
            <select
              value={shot.fitSpeed ? "fit" : String(shot.speed)}
              onChange={(e) => (e.target.value === "fit" ? props.onChange({ fitSpeed: true }) : props.onChange({ fitSpeed: false, speed: Number(e.target.value) }))}
            >
              <option value="1">Normal (1×)</option>
              <option value="0.9">Slower (0.9×)</option>
              <option value="0.8">Slower (0.8×)</option>
              <option value="0.7">Slower (0.7×)</option>
              <option value="0.6">Slower (0.6×)</option>
              <option value="fit">Slow to fit the shot</option>
            </select>
          </label>
        </div>
      )}
      {shot.mode === "LAYERED" && (
        <LayerEditor shot={shot} images={images} api={props.api} projectId={props.projectId} onChange={(layers) => props.onChange({ layers })} />
      )}
      {shot.mode === "GENERATIVE" && <Banner kind="warn">AI-generated motion is not available in this version. This shot would use a local fallback.</Banner>}
      {isImageMode && (
        <label className="field compact">
          Picture
          <select value={shot.imageAssetId ?? ""} onChange={(e) => props.onChange({ imageAssetId: e.target.value || null })}>
            <option value="">— choose a picture —</option>
            {images.map((a) => (
              <option key={a.id} value={a.id}>
                {a.orig_name}
                {a.status !== "ok" ? ` (${a.status})` : ""}
              </option>
            ))}
          </select>
        </label>
      )}
      {shot.mode === "RENDERED" && (
        <label className="field compact">
          Video clip
          <select value={shot.clipAssetId ?? ""} onChange={(e) => props.onChange({ clipAssetId: e.target.value || null })}>
            <option value="">— choose a clip —</option>
            {clips.map((a) => (
              <option key={a.id} value={a.id}>
                {a.orig_name}
              </option>
            ))}
          </select>
        </label>
      )}
      {chosen?.thumbUrl && <img className="chosen-thumb" alt={`Chosen picture: ${chosen.orig_name}`} src={props.api.mediaUrl(props.projectId, chosen.id, "thumbs")} />}
      <label className="field compact">
        Action (what happens in this shot)
        <input value={shot.action} maxLength={2000} onChange={(e) => props.onChange({ action: e.target.value })} />
      </label>
      <div className="row wrap">
        <label className="field compact grow">
          Must show (one per line)
          <textarea rows={3} value={must} onChange={(e) => { setMust(e.target.value); props.onChange({ mustShow: lines(e.target.value) }); }} />
        </label>
        <label className="field compact grow">
          Avoid (one per line)
          <textarea rows={3} value={avoid} onChange={(e) => { setAvoid(e.target.value); props.onChange({ avoid: lines(e.target.value) }); }} />
        </label>
      </div>
      {board.characters.length > 0 && (
        <fieldset className="field compact">
          <legend>Characters in this shot</legend>
          {board.characters.map((c) => (
            <label key={c.id} className="inline">
              <input
                type="checkbox"
                checked={shot.characterIds.includes(c.id)}
                onChange={(e) => props.onChange({ characterIds: e.target.checked ? [...shot.characterIds, c.id] : shot.characterIds.filter((x) => x !== c.id) })}
              />{" "}
              {c.name}
            </label>
          ))}
        </fieldset>
      )}
    </section>
  );
}
