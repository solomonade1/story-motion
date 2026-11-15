import { useEffect, useId, useRef, type ReactNode } from "react";

/** A modal dialog: focus moves into it, Escape closes it, and focus returns to where it came from. */
export function Dialog(props: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const { onClose } = props;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const first = ref.current?.querySelector<HTMLElement>("input, select, textarea, button");
    first?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {
        const items = [...ref.current.querySelectorAll<HTMLElement>("input, select, textarea, button, [href]")].filter((el) => !el.hasAttribute("disabled"));
        const firstEl = items[0];
        const lastEl = items[items.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) {
          e.preventDefault();
          lastEl?.focus();
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          e.preventDefault();
          firstEl?.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} className={`dialog${props.wide ? " wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <h2 id={titleId}>{props.title}</h2>
        {props.children}
      </div>
    </div>
  );
}

export function Banner(props: { kind: "error" | "warn" | "info" | "ok"; children: ReactNode; onDismiss?: () => void; action?: ReactNode }) {
  return (
    <div className={`banner ${props.kind}`} role={props.kind === "error" ? "alert" : "status"}>
      <div>{props.children}</div>
      <div className="banner-actions">
        {props.action}
        {props.onDismiss && (
          <button className="link" onClick={props.onDismiss} aria-label="Dismiss message">
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}

export function Badge(props: { kind: "ok" | "warn" | "fail" | "info"; children: ReactNode }) {
  return <span className={`badge ${props.kind}`}>{props.children}</span>;
}

export function Progress(props: { value: number; label: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, props.value)) * 100);
  return (
    <div className="progress" role="progressbar" aria-label={props.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
      <div style={{ width: `${pct}%` }} />
    </div>
  );
}
