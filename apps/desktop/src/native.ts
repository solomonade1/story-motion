/** Native file/folder pickers, available only inside the desktop window. In a plain browser the UI falls back to typed paths. */

type PickOptions = { multiple?: boolean; directory?: boolean; filterName?: string; extensions?: string[] };
type WorkerPicker = (opts: PickOptions) => Promise<string[]>;
let workerPicker: WorkerPicker | null = null;

/** In the app window the worker opens the chooser (see studio/picker.py); in a plain browser this stays off. */
export function enableWorkerPicker(fn: WorkerPicker | null): void {
  workerPicker = fn;
}

function inTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function hasNativePicker(): boolean {
  return inTauri() || workerPicker !== null;
}

export async function pickPaths(opts: PickOptions): Promise<string[]> {
  if (!inTauri()) {
    if (!workerPicker) throw new Error("The file chooser is only available in the app window. Type the path instead.");
    return workerPicker(opts);
  }
  const { open } = await import("@tauri-apps/plugin-dialog");
  const result = await open({
    multiple: opts.multiple ?? false,
    directory: opts.directory ?? false,
    ...(opts.extensions ? { filters: [{ name: opts.filterName ?? "Files", extensions: opts.extensions }] } : {}),
  });
  if (result === null) return [];
  return Array.isArray(result) ? result : [result];
}

export const MEDIA_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "wav", "mp3", "aac", "mp4", "mov"];
