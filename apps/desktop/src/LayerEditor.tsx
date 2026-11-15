import { useState } from "react";
import type { Api } from "./api";
import { MsField, RangeField } from "./Fields";
import { defaultLayer, layerCss, layerPoseAt } from "./storyboardLogic";
import type { Asset, SbEasing, SbLayer, SbLayerPose, SbShot } from "./types";

const EASINGS: { value: SbEasing; label: string }[] = [
  { value: "easeInOut", label: "Ease in and out" },
  { value: "linear", label: "Steady" },
  { value: "easeIn", label: "Speed up" },
  { value: "easeOut", label: "Slow down" },
];

/**
 * Moving layers for a LAYERED shot: separate pictures with transparency that travel, grow and turn over the
 * background. The stage below shows where a layer is a chosen fraction of the way through the shot; it is a
 * placement aid (the exported video is the reference).
 */
export function LayerEditor(props: {
  shot: SbShot;
  images: Asset[];
  api: Api;
  projectId: string;
  onChange: (layers: SbLayer[]) => void;
}) {
  const { shot, images, api, projectId } = props;
  const [pos, setPos] = useState(0);
  const layers = shot.layers;
  const byId = new Map(images.map((a) => [a.id, a]));
  const set = (i: number, patch: Partial<SbLayer>) => props.onChange(layers.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  const setPose = (i: number, which: "start" | "end", patch: Partial<SbLayerPose>) => set(i, { [which]: { ...layers[i]![which], ...patch } });
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= layers.length) return;
    const out = [...layers];
    [out[i], out[j]] = [out[j] as SbLayer, out[i] as SbLayer];
    props.onChange(out);
  };
  const bg = shot.imageAssetId ? byId.get(shot.imageAssetId) : undefined;

  return (
    <div className="layer-editor">
      <h4>Moving layers (drawn back to front)</h4>
      <p className="muted small">
        Use pictures with a transparent background (PNG). Position is where the layer's turning point (pivot) is in the frame: 0,0 is the top left,
        1,1 the bottom right; values outside 0–1 start or end off-screen. Size is the layer's width as a fraction of the frame width.
      </p>
      <div className="layer-stage" role="img" aria-label="Layer placement preview">
        {bg ? <img className="layer-bg" alt="" src={api.mediaUrl(projectId, bg.id, "proxies")} /> : <div className="layer-bg empty">No background picture chosen</div>}
        {layers.map((l, i) => {
          const a = byId.get(l.assetId);
          const pose = layerPoseAt(l, pos / 100, shot.durationMs);
          return a ? (
            <img key={`${l.assetId}-${i}`} alt="" className="layer-img" style={layerCss(l, pose)} src={api.mediaUrl(projectId, l.assetId, "alpha")} />
          ) : null;
        })}
        {layers.map((l, i) => {
          const pose = layerPoseAt(l, pos / 100, shot.durationMs);
          return <span key={`pin-${i}`} className="layer-pin" style={{ left: `${pose.x * 100}%`, top: `${pose.y * 100}%` }} aria-hidden="true" />;
        })}
      </div>
      <label className="field compact">
        Preview position in the shot: {pos}%
        <input type="range" min={0} max={100} step={1} value={pos} aria-label="Layer preview position" onChange={(e) => setPos(Number(e.target.value))} />
      </label>

      {layers.map((l, i) => (
        <fieldset key={`${l.assetId}-${i}`} className="scene" aria-label={`Layer ${i + 1}`}>
          <div className="row wrap">
            <label className="field compact">
              Layer picture
              <select value={l.assetId} onChange={(e) => set(i, { assetId: e.target.value })}>
                {!byId.has(l.assetId) && <option value={l.assetId}>(not in the library)</option>}
                {images.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.orig_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact">
              Movement
              <select value={l.easing} onChange={(e) => set(i, { easing: e.target.value as SbEasing })}>
                {EASINGS.map((e) => (
                  <option key={e.value} value={e.value}>
                    {e.label}
                  </option>
                ))}
              </select>
            </label>
            <button aria-label={`Move layer ${i + 1} back`} disabled={i === 0} onClick={() => move(i, -1)}>
              ↓ back
            </button>
            <button aria-label={`Move layer ${i + 1} forward`} disabled={i === layers.length - 1} onClick={() => move(i, 1)}>
              ↑ front
            </button>
            <button onClick={() => props.onChange(layers.filter((_, k) => k !== i))}>Remove layer {i + 1}</button>
          </div>
          {(["start", "end"] as const).map((which) => (
            <div className="row wrap" key={which} role="group" aria-label={`Layer ${i + 1} ${which}`}>
              <strong className="pose-label">{which === "start" ? "Start" : "End"}</strong>
              <RangeField label={`${which === "start" ? "Start" : "End"} x`} value={l[which].x} min={-0.5} max={1.5} onCommit={(n) => setPose(i, which, { x: n })} />
              <RangeField label={`${which === "start" ? "Start" : "End"} y`} value={l[which].y} min={-0.5} max={1.5} onCommit={(n) => setPose(i, which, { y: n })} />
              <RangeField label={`${which === "start" ? "Start" : "End"} size`} value={l[which].widthFrac} min={0.01} max={2} onCommit={(n) => setPose(i, which, { widthFrac: n })} />
              <RangeField label={`${which === "start" ? "Start" : "End"} tilt (deg)`} value={l[which].rotateDeg} min={-360} max={360} onCommit={(n) => setPose(i, which, { rotateDeg: n })} />
            </div>
          ))}
          <div className="row wrap">
            <RangeField label="Pivot x (0 = left edge)" value={l.pivotX} min={0} max={1} onCommit={(n) => set(i, { pivotX: n })} />
            <RangeField label="Pivot y (0 = top edge)" value={l.pivotY} min={0} max={1} onCommit={(n) => set(i, { pivotY: n })} />
            <RangeField label="Rocking (deg)" value={l.swayDeg} min={0} max={45} onCommit={(n) => set(i, { swayDeg: n })} />
            <MsField label="Rocking period (ms)" value={l.swayPeriodMs} min={1} onCommit={(n) => set(i, { swayPeriodMs: n })} />
          </div>
        </fieldset>
      ))}
      <button
        disabled={images.length === 0}
        title={images.length === 0 ? "Import a picture with a transparent background on the Media tab first" : undefined}
        onClick={() => props.onChange([...layers, defaultLayer(images.find((a) => a.id !== shot.imageAssetId)?.id ?? images[0]?.id ?? "")])}
      >
        Add layer
      </button>
    </div>
  );
}
