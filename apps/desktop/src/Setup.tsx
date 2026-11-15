import { useCallback, useEffect, useState } from "react";
import type { Api } from "./api";
import type { Health } from "./types";
import { Badge, Banner } from "./ui";

export function Setup(props: { api: Api; onContinue: () => void }) {
  const { api, onContinue } = props;
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const check = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setHealth(await api.health());
    } catch (e) {
      setHealth(null);
      setError(e instanceof Error ? e.message : "The worker did not answer.");
    } finally {
      setBusy(false);
    }
  }, [api]);

  useEffect(() => {
    void check();
  }, [check]);

  const failing = health?.checks.filter((c) => c.status === "fail") ?? [];
  return (
    <main className="page narrow">
      <h1>Welcome to StoryMotion Studio</h1>
      <p className="muted">Everything runs on this computer. No account, no internet connection and no cloud service is needed.</p>
      <h2>Setup check</h2>
      {busy && <p aria-live="polite">Checking this computer…</p>}
      {error && (
        <Banner kind="error" action={<button onClick={() => void check()}>Try again</button>}>
          {error}
        </Banner>
      )}
      {health && (
        <ul className="checks" aria-label="Setup checks">
          {health.checks.map((c) => (
            <li key={c.id}>
              <div className="check-head">
                <Badge kind={c.status}>{c.status === "ok" ? "Ready" : c.status === "warn" ? "Optional" : "Needs attention"}</Badge>
                <strong>{c.label}</strong>
              </div>
              <div className="muted">{c.detail}</div>
              {c.status !== "ok" && c.fix && <div className="fix">How to fix: {c.fix}</div>}
            </li>
          ))}
        </ul>
      )}
      {health && failing.length > 0 && (
        <Banner kind="warn">
          Some things need attention. You can still create and organise projects, but importing and previews will not work until they are fixed.
        </Banner>
      )}
      <div className="row">
        <button className="primary" onClick={onContinue} disabled={!health}>
          {failing.length > 0 ? "Continue anyway" : "Continue"}
        </button>
        <button onClick={() => void check()} disabled={busy}>
          Check again
        </button>
      </div>
      {health && <p className="muted small">Workspace: {health.workspace}</p>}
    </main>
  );
}
