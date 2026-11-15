# Decision record — Phase 1 — build `p1-20261114-b75743ce627a`

Date: 2026-11-14 · Approver: project owner (written instructions in this session).

## DR-101 — Phase 1 started
Owner: "Yes, start Phase 1". Scope: desktop foundation, durable projects, media intake (phased prompt Phase 1). No timeline, no cloud provider.

## DR-102 — Toolchain installs for the desktop shell
Owner: "Yes, install them". Outcome (facts, not claims):
- Rust 1.100.0 installed by the agent (winget/rustup, per-user, hash-verified).
- Microsoft C++ Build Tools: two agent attempts exited **1602 (cancelled)** — the administrator prompt was not granted. The owner then installed **Visual Studio Community 2026** himself/herself; it lacked the C++ workload, which the agent
  added through the Visual Studio installer (administrator prompt granted that time). MSVC 14.50 and `link.exe` are present. Microsoft's licence terms were accepted as part of these installs, at the owner's instruction.
- First build attempt: **blocked by Windows Smart App Control (state 1)** — "An Application Control policy has blocked this file (os error 4551)" for every crate build helper; Code Integrity log events 3077/3118 name `cargo.exe`.
  The agent did **not** change this Windows security setting (it is not re-enableable once off).

## DR-103 — Desktop shell DEFERRED (owner decision: "Defer desktop shell")
| Item | Decision / consequence |
|---|---|
| Tauri shell + installer | **Deferred.** `apps/desktop/src-tauri/` stays in the repository as **unverified, never-compiled source**. No claim is made about it |
| Partial build output | removed (`src-tauri/target`, `gen`) |
| What the product is until then | the **browser-hosted Studio**: `serve` starts the local worker and prints a private URL; the UI runs in any browser (README "The Studio") |
| Phase 1 verdict | **PARTIAL — owner-accepted deferral of one deliverable.** Everything else in Phase 1 is done and tested. This is not recorded as a Phase 1 PASS; the owner has not been asked to sign one |
| G2 | not claimed (needs Phase 2 and a desktop install test) |
| Installed toolchains | Rust and Visual Studio C++ remain installed (disk use) and are harmless; uninstall instructions on request |

## Open exceptions carried forward
E-1 Hezekiah clip + Windows-voice licences unverified · E-2 provider behaviour unverified (Phase 4) · E-3 no git repository · **E-5 desktop shell deferred (Smart App Control)** · typed paths in browser mode (native picker exists in code, untested in a real window).
