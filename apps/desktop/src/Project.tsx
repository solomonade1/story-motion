import { useCallback, useEffect, useState } from "react";
import type { Api } from "./api";
import { Media } from "./Media";
import { Storyboard } from "./Storyboard";
import type { ProjectView } from "./types";
import { Banner } from "./ui";
import { useAutosave, type SaveState } from "./useAutosave";

type Tab = "media" | "storyboard" | "script";

export function ProjectScreen(props: { api: Api; projectId: string; onBack: () => void }) {
  const { api, projectId } = props;
  const [view, setView] = useState<ProjectView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("media");
  const [generation, setGeneration] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  const load = useCallback(async () => {
    try {
      setView(await api.getProject(projectId));
      setError(null);
      setGeneration((g) => g + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the project.");
    }
  }, [api, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error && !view) {
    return (
      <main className="page">
        <Banner kind="error" action={<button onClick={() => void load()}>Try again</button>}>
          {error}
        </Banner>
        <button onClick={props.onBack}>← All projects</button>
      </main>
    );
  }
  if (!view) {
    return (
      <main className="page">
        <p aria-live="polite">Opening the project…</p>
      </main>
    );
  }
  const doc = view.document;
  return (
    <main className="page">
      <header className="bar">
        <div className="row">
          <button onClick={props.onBack} aria-label="Back to all projects">
            ← Projects
          </button>
          <h1>{doc.name}</h1>
        </div>
      </header>
      {!dismissed && view.warnings.map((w) => (
        <Banner key={w} kind="warn" onDismiss={() => setDismissed(true)}>
          {w}
        </Banner>
      ))}
      {!dismissed && view.migrated.length > 0 && (
        <Banner kind="info" onDismiss={() => setDismissed(true)}>
          This project was saved by an older version and has been updated. The original file was kept next to it.
        </Banner>
      )}
      <div role="tablist" aria-label="Project sections" className="tabs">
        {(["media", "storyboard", "script"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {t === "media" ? "Media" : t === "storyboard" ? "Storyboard" : "Script & notes"}
          </button>
        ))}
      </div>
      {tab === "media" && <Media api={api} projectId={projectId} />}
      {tab === "storyboard" && <Storyboard api={api} projectId={projectId} />}
      {tab === "script" && (
        <ScriptEditor key={generation} doc={doc} save={(patch, rev) => api.saveDocument(projectId, patch, rev)} onReload={() => void load()} />
      )}
    </main>
  );
}

const STATE_TEXT: Record<SaveState, string> = {
  saved: "All changes saved",
  dirty: "Unsaved changes…",
  saving: "Saving…",
  error: "Could not save",
  conflict: "This project was changed somewhere else",
};

function ScriptEditor(props: { doc: ProjectView["document"]; save: Parameters<typeof useAutosave>[1]; onReload: () => void }) {
  const { values, update, state, message, retry } = useAutosave(props.doc, props.save);
  return (
    <section className="panel" aria-label="Script and notes">
      <div className="bar">
        <h2>Script &amp; notes</h2>
        <div className={`save-state ${state}`} role="status" aria-live="polite">
          {STATE_TEXT[state]}
        </div>
      </div>
      {state === "error" && (
        <Banner kind="error" action={<button onClick={retry}>Try again</button>}>
          {message} Your text is still here and has not been lost.
        </Banner>
      )}
      {state === "conflict" && (
        <Banner kind="warn" action={<button onClick={props.onReload}>Reload project</button>}>
          {message}
        </Banner>
      )}
      <label className="field">
        Script (one narration paragraph per line)
        <textarea value={values.script} onChange={(e) => update("script", e.target.value)} rows={10} />
      </label>
      <label className="field">
        Notes
        <textarea value={values.notes} onChange={(e) => update("notes", e.target.value)} rows={4} />
      </label>
      <p className="muted small">Changes are saved automatically a moment after you stop typing.</p>
    </section>
  );
}
