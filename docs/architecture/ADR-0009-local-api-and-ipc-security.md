# ADR-0009 — Local API between the UI and the worker (loopback + session token)

- **Status:** Accepted (Phase 1). **Source:** PRD §10.1 implementation note ("a loopback-only API is acceptable... with a random session token and
  strict local binding"), §13.3; Charter C3 invariants 9–10; QG TRUST-01..03.

## Decision
The Python worker serves a small HTTP API; the React UI is a client of it. The same API will back the Tauri shell (the shell starts the worker,
reads its one-line JSON `ready` message, and loads the UI with the token). Chosen over Tauri IPC commands calling Python directly because it keeps
one tested contract for browser-dev, tests and the shell.

Controls (each has a test; the first five were **mutation-checked** — disabling the check makes a test fail):
1. **Loopback only.** Binding to anything but 127.0.0.1/localhost is refused at construction.
2. **Session token.** 256-bit random per process, compared in constant time; required on every `/api` route. `?token=` is accepted **only** for
   preview images (an `<img>` cannot send headers) and is scrubbed from logs.
3. **Host header** must be the loopback origin (defeats DNS-rebinding). 4. **Origin** must be on an allow-list (the app itself + explicit extras);
   CORS headers are returned only for allowed origins. 5. **Path safety:** `..`, backslashes and NULs are rejected; static files are re-checked to
   stay inside the UI folder (two independent layers).
6. **Narrow commands only.** A fixed route table (projects, trash, document, assets, jobs, health). No shell, no raw SQL, no arbitrary file
   read/write. The only client-supplied paths are files the user explicitly chose to **import or relink**; previews are served by asset id from
   the database. 7. JSON only, ≤ 1 MB bodies; imports ≤ 500 files and validated **before** a job starts.
8. **Errors** are `{code, message}` in plain language; unexpected errors return a generic message (no stack, no paths, no token).
9. **Process lifetime.** `serve --exit-on-stdin-close` exits when the parent goes away; a second worker on the workspace is refused. Jobs run on a
   small pool owned by the server; nothing runs in the background that the UI cannot list and cancel.
10. **No secrets exist** in this phase (no provider keys); the design keeps them out of the renderer for Phase 4 (OS credential store).

## Limits / follow-ups
- The token is in the URL fragment (never sent to a server) but a browser-dev tab keeps it in history; inside the packaged app there is no URL bar.
- A **Tauri CSP, capability allow-list and Windows packaging are not built yet** (needs the Rust toolchain). Until then the "desktop" claim is limited
  to the browser-hosted UI served by the worker.
- On Windows a venv's `python.exe` is a launcher with a child process; the shell must start the real interpreter directly (or kill the process tree).
- Provider/cloud endpoints do not exist; no network connection is made by any code path in this phase.
