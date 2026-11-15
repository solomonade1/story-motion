import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";
import type { ProjectDoc } from "./types";

export type SaveState = "saved" | "dirty" | "saving" | "error" | "conflict";
type Fields = Pick<ProjectDoc, "script" | "notes">;
type Saver = (patch: Partial<Fields>, baseRevision: number) => Promise<ProjectDoc>;

/**
 * Debounced autosave for the project document.
 * - edits are saved after `delayMs` of quiet and when the panel closes;
 * - only one save is in flight at a time, and the latest text always wins;
 * - if a save fails the text stays on screen and can be retried (nothing is silently dropped);
 * - a revision conflict (the project changed elsewhere) stops saving and asks the user to reload.
 */
export function useAutosave(initial: ProjectDoc, save: Saver, delayMs = 800) {
  const [values, setValues] = useState<Fields>({ script: initial.script, notes: initial.notes });
  const [state, setState] = useState<SaveState>("saved");
  const [message, setMessage] = useState("");
  const revision = useRef(initial.revision);
  const pending = useRef<Partial<Fields> | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saving = useRef(false);
  const conflict = useRef(false);
  const saveRef = useRef(save);
  saveRef.current = save;

  const flush = useCallback(async (): Promise<void> => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (saving.current || !pending.current || conflict.current) return;
    const patch = pending.current;
    pending.current = null;
    saving.current = true;
    setState("saving");
    try {
      const doc = await saveRef.current(patch, revision.current);
      revision.current = doc.revision;
      setMessage("");
      if (pending.current) {
        setState("dirty");
        timer.current = setTimeout(() => void flush(), 0);
      } else {
        setState("saved");
      }
    } catch (e) {
      pending.current = { ...patch, ...(pending.current ?? {}) }; // keep the text; never drop an edit
      if (e instanceof ApiError && e.code === "stale_revision") {
        conflict.current = true;
        setState("conflict");
      } else {
        setState("error");
      }
      setMessage(e instanceof Error ? e.message : "Could not save.");
    } finally {
      saving.current = false;
    }
  }, []);

  const update = useCallback(
    (field: keyof Fields, value: string) => {
      setValues((v) => ({ ...v, [field]: value }));
      pending.current = { ...(pending.current ?? {}), [field]: value };
      if (!conflict.current) {
        setState((s) => (s === "saving" ? s : "dirty"));
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(() => void flush(), delayMs);
      }
    },
    [delayMs, flush],
  );

  const retry = useCallback(() => {
    conflict.current = false;
    void flush();
  }, [flush]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      void flush(); // best effort: save whatever is still pending when the panel closes
    },
    [flush],
  );

  return { values, update, state, message, retry, flush };
}
