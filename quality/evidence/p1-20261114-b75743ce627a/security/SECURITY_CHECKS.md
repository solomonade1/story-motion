# Security checks — Phase 1 local API (build `p1-20261114-b75743ce627a`)

All checks are automated in `tests/integration/test_studio_api.py` unless noted. "Mutation-checked" = the protection was deliberately disabled and the test **failed**, so it is a real guard.

| Control | Test | Mutation-checked |
|---|---|---|
| Binds to loopback only (0.0.0.0 refused) | `test_only_loopback_is_allowed` | — |
| Token required on every `/api` route; wrong/short/long/empty tokens → 401 | `test_token_is_required_and_checked` | **yes** (token check → always true fails the test) |
| Spoofed `Host` header → 403 even with a valid token (DNS-rebinding) | `test_spoofed_host_header_is_rejected…` | **yes** |
| Foreign browser `Origin` → 403, no CORS headers; allowed origin gets CORS; preflight checked | `test_foreign_browser_origin_is_rejected…` | **yes** |
| Query-string token accepted **only** for preview images, never for normal endpoints; token not written to logs | `test_media_token_in_the_query_never_reaches_the_log` | **yes** (query token accepted everywhere fails) |
| Body ≤ 1 MB (413), JSON only (415), malformed JSON (400), non-object (400) | `test_body_limits_and_content_type` | — |
| Path traversal / backslash / encoded dots cannot read files outside the UI folder; unknown routes 404, wrong methods 405; malformed ids never reach the filesystem layer | `test_unknown_routes_methods_and_traversal` | **yes** (both independent layers must be disabled to leak; either alone holds) |
| Unexpected errors return a generic message — no stack trace, path, exception name or token | `test_internal_errors_do_not_leak_details_or_the_token` | — |
| Previews served by asset id from the database, never a client path | `test_preview_files_are_served_only_via_database_lookup` (`test_studio_assets.py`) | — |
| Hostile file names are inert (shell characters, traversal) | `test_hostile_file_name_is_inert`, `test_hostile_names_are_plain_text_never_paths` | — |
| Missing FFmpeg → clear 503 with the fix; health still answers | `test_missing_ffmpeg_is_a_clear_503…` | — |
| Worker exits when the parent closes stdin; nothing listens afterwards; second worker refused; lock released after a crash | `test_serve_prints_ready_and_exits…`, `test_a_second_worker…` (`test_studio_crash.py`) | — |

## Not covered (stated plainly)
- **No network-monitor verification** (TRUST-03): "no network connections" is true by construction (no networking code except the loopback server) but was **not measured**.
- **Tauri CSP/capabilities** do not exist yet (no shell). A browser tab holding the `#token=` URL keeps it in local history.
- No fuzzing; no third-party penetration test; the HTTP server is Python's standard `http.server` (adequate for a loopback-only, token-protected local API; not for exposure beyond localhost).
- No secrets exist in this phase to leak; provider credential handling is Phase 4.
