import { useEffect, useState } from "react";
import { parseDb, parseNum, parseWholeMs } from "./storyboardLogic";

/** A numeric field: only a valid value ever reaches the storyboard, applied when the field is left or Enter is pressed. */
export function NumField(props: {
  label: string;
  value: number;
  parse: (text: string) => number | null;
  rule: string;
  unit: string;
  onCommit: (n: number) => void;
}) {
  const [draft, setDraft] = useState(String(props.value));
  const [bad, setBad] = useState(false);
  useEffect(() => {
    setDraft(String(props.value));
    setBad(false);
  }, [props.value]);
  const commit = () => {
    const n = props.parse(draft);
    if (n !== null && n !== props.value) props.onCommit(n);
  };
  return (
    <label className="field compact">
      {props.label}
      <input
        inputMode="decimal"
        value={draft}
        aria-invalid={bad}
        onChange={(e) => {
          setDraft(e.target.value);
          setBad(props.parse(e.target.value) === null);
        }}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
      />
      {bad && (
        <span className="field-error" role="alert">
          Not applied: {props.rule}. It keeps {props.value} {props.unit}.
        </span>
      )}
    </label>
  );
}

/** Whole milliseconds. */
export function MsField(props: { label: string; value: number; min: number; onCommit: (n: number) => void }) {
  return (
    <NumField
      label={props.label}
      value={props.value}
      parse={(t) => parseWholeMs(t, props.min)}
      rule={`use whole milliseconds, ${props.min === 0 ? "0 or more" : `${props.min} or more`}`}
      unit="ms"
      onCommit={props.onCommit}
    />
  );
}

/** Decibels, to two decimals, within a range. */
export function DbField(props: { label: string; value: number; min: number; max: number; onCommit: (n: number) => void }) {
  return (
    <NumField
      label={props.label}
      value={props.value}
      parse={(t) => parseDb(t, props.min, props.max)}
      rule={`use a number from ${props.min} to ${props.max}`}
      unit="dB"
      onCommit={props.onCommit}
    />
  );
}

/** A plain number in a range, up to three decimals (positions, sizes, angles). */
export function RangeField(props: { label: string; value: number; min: number; max: number; unit?: string; onCommit: (n: number) => void }) {
  return (
    <NumField
      label={props.label}
      value={props.value}
      parse={(t) => parseNum(t, props.min, props.max)}
      rule={`use a number from ${props.min} to ${props.max}`}
      unit={props.unit ?? ""}
      onCommit={props.onCommit}
    />
  );
}
