import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { Api } from "./api";
import { formatWhen } from "./format";
import type { ProjectSummary, TrashItem } from "./types";
import { Banner, Dialog } from "./ui";

type Modal =
  | { kind: "create" }
  | { kind: "rename"; project: ProjectSummary }
  | { kind: "delete"; project: ProjectSummary }
  | { kind: "purge"; item: TrashItem }
  | null;

export function Projects(props: { api: Api; onOpen: (id: string) => void; onSetup: () => void }) {
  const { api, onOpen } = props;
  const [archived, setArchived] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [trash, setTrash] = useState<TrashItem[]>([]);
  const [showTrash, setShowTrash] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal>(null);

  const load = useCallback(async () => {
    try {
      const [list, tr] = await Promise.all([api.listProjects(archived), api.listTrash()]);
      setProjects(list);
      setTrash(tr);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load your projects.");
    }
  }, [api, archived]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (fn: () => Promise<unknown>, done?: string) => {
    try {
      await fn();
      setModal(null);
      if (done) setNotice(done);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work.");
      setModal(null);
    }
  };

  return (
    <main className="page">
      <header className="bar">
        <h1>Your projects</h1>
        <div className="row">
          <button onClick={props.onSetup}>Setup check</button>
          <button className="primary" onClick={() => setModal({ kind: "create" })}>
            New project
          </button>
        </div>
      </header>
      {error && (
        <Banner kind="error" onDismiss={() => setError(null)} action={<button onClick={() => void load()}>Try again</button>}>
          {error}
        </Banner>
      )}
      {notice && (
        <Banner kind="ok" onDismiss={() => setNotice(null)}>
          {notice}
        </Banner>
      )}
      <div className="row">
        <label className="check">
          <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Show archived projects
        </label>
        <button className="link" onClick={() => setShowTrash((s) => !s)} aria-expanded={showTrash}>
          Trash ({trash.length})
        </button>
      </div>

      {projects === null && !error && <p aria-live="polite">Loading your projects…</p>}
      {projects?.length === 0 && (
        <div className="empty">
          <h2>{archived ? "No archived projects" : "No projects yet"}</h2>
          <p className="muted">
            {archived ? "Projects you archive are kept here." : "A project holds a story's script, pictures, clips and narration."}
          </p>
          {!archived && (
            <button className="primary" onClick={() => setModal({ kind: "create" })}>
              Create your first project
            </button>
          )}
        </div>
      )}
      <ul className="cards" aria-label="Projects">
        {projects?.map((p) => (
          <li key={p.id} className="card">
            <button className="card-title link" onClick={() => onOpen(p.id)}>
              {p.name}
            </button>
            <div className="muted small">Edited {formatWhen(p.updated_at)}</div>
            <div className="row wrap">
              <button onClick={() => onOpen(p.id)}>Open</button>
              <button onClick={() => setModal({ kind: "rename", project: p })}>Rename</button>
              <button onClick={() => void run(() => api.duplicateProject(p.id), `Duplicated "${p.name}".`)}>Duplicate</button>
              <button onClick={() => void run(() => api.setArchived(p.id, !archived), archived ? `Restored "${p.name}".` : `Archived "${p.name}".`)}>
                {archived ? "Unarchive" : "Archive"}
              </button>
              <button className="danger" onClick={() => setModal({ kind: "delete", project: p })}>
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>

      {showTrash && (
        <section aria-label="Trash">
          <h2>Trash</h2>
          {trash.length === 0 && <p className="muted">The trash is empty.</p>}
          <ul className="list">
            {trash.map((t) => (
              <li key={t.trashId} className="row between">
                <span>{t.name}</span>
                <span className="row">
                  <button onClick={() => void run(() => api.restore(t.trashId), `Restored "${t.name}".`)}>Restore</button>
                  <button className="danger" onClick={() => setModal({ kind: "purge", item: t })}>
                    Delete forever…
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {modal?.kind === "create" && (
        <NameDialog title="New project" label="Project name" confirm="Create" onClose={() => setModal(null)}
          onSubmit={(name) => run(async () => onOpen((await api.createProject(name)).projectId))} />
      )}
      {modal?.kind === "rename" && (
        <NameDialog title="Rename project" label="Project name" confirm="Rename" initial={modal.project.name} onClose={() => setModal(null)}
          onSubmit={(name) => run(() => api.renameProject(modal.project.id, name), "Renamed.")} />
      )}
      {modal?.kind === "delete" && (
        <Dialog title={`Delete "${modal.project.name}"?`} onClose={() => setModal(null)}>
          <p>The project moves to the trash. Nothing is erased yet; you can restore it from the trash until you empty it.</p>
          <div className="row end">
            <button onClick={() => setModal(null)}>Keep it</button>
            <button className="danger" onClick={() => void run(() => api.deleteProject(modal.project.id), `Moved "${modal.project.name}" to the trash.`)}>
              Move to trash
            </button>
          </div>
        </Dialog>
      )}
      {modal?.kind === "purge" && (
        <PurgeDialog item={modal.item} onClose={() => setModal(null)} onConfirm={() => run(() => api.purge(modal.item.trashId), `Permanently deleted "${modal.item.name}".`)} />
      )}
    </main>
  );
}

function NameDialog(props: { title: string; label: string; confirm: string; initial?: string; onClose: () => void; onSubmit: (name: string) => void }) {
  const [name, setName] = useState(props.initial ?? "");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (name.trim()) props.onSubmit(name.trim());
  };
  return (
    <Dialog title={props.title} onClose={props.onClose}>
      <form onSubmit={submit}>
        <label className="field">
          {props.label}
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="off" />
        </label>
        <div className="row end">
          <button type="button" onClick={props.onClose}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={!name.trim()}>
            {props.confirm}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function PurgeDialog(props: { item: TrashItem; onClose: () => void; onConfirm: () => void }) {
  const [typed, setTyped] = useState("");
  const ok = typed === props.item.name;
  return (
    <Dialog title="Delete forever?" onClose={props.onClose}>
      <p>
        This permanently erases <strong>{props.item.name}</strong> and all of its imported files. It cannot be undone.
      </p>
      <label className="field">
        Type the project name to confirm
        <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
      </label>
      <div className="row end">
        <button onClick={props.onClose}>Cancel</button>
        <button className="danger" disabled={!ok} onClick={props.onConfirm}>
          Delete forever
        </button>
      </div>
    </Dialog>
  );
}
