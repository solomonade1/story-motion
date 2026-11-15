import { DbField, MsField } from "./Fields";
import type { Asset, SbAudioTrack, Storyboard } from "./types";

type Edit = (fn: (b: Storyboard) => Storyboard, label?: string) => void;

/** Music and ambience beds under the narration. They are lowered ("ducked") while the narrator speaks. */
export function AudioPanel(props: { sb: Storyboard; audio: Asset[]; edit: Edit }) {
  const { sb, audio, edit } = props;
  const set = (i: number, patch: Partial<SbAudioTrack>) =>
    edit((b) => ({ ...b, audioTracks: b.audioTracks.map((t, k) => (k === i ? { ...t, ...patch } : t)) }));
  return (
    <div className="audio-tracks">
      <h3>Music and ambience</h3>
      <p className="muted small">
        Beds play under the narration and are lowered while the narrator speaks. The final mix is checked for clipping after rendering.
      </p>
      {sb.audioTracks.map((t, i) => (
        <fieldset key={`${t.assetId}-${i}`} className="scene" aria-label={`Audio track ${i + 1}`}>
          <div className="row wrap">
            <label className="field compact">
              File
              <select value={t.assetId} onChange={(e) => set(i, { assetId: e.target.value })}>
                {!audio.some((a) => a.id === t.assetId) && <option value={t.assetId}>(not in the library)</option>}
                {audio.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.orig_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact">
              Kind
              <select value={t.role} onChange={(e) => set(i, { role: e.target.value as SbAudioTrack["role"] })}>
                <option value="music">Music</option>
                <option value="ambience">Ambience</option>
              </select>
            </label>
            <DbField label="Level (dB)" value={t.gainDb} min={-60} max={12} onCommit={(n) => set(i, { gainDb: n })} />
            <DbField label="Lower under narration by (dB)" value={t.duckDb} min={0} max={30} onCommit={(n) => set(i, { duckDb: n })} />
          </div>
          <div className="row wrap">
            <MsField label="Starts at (ms)" value={t.startMs} min={0} onCommit={(n) => set(i, { startMs: n })} />
            <MsField label="Fade in (ms)" value={t.fadeInMs} min={0} onCommit={(n) => set(i, { fadeInMs: n })} />
            <MsField label="Fade out (ms)" value={t.fadeOutMs} min={0} onCommit={(n) => set(i, { fadeOutMs: n })} />
            <label className="inline">
              <input type="checkbox" checked={t.loop} onChange={(e) => set(i, { loop: e.target.checked })} /> Repeat if shorter than the video
            </label>
            <button onClick={() => edit((b) => ({ ...b, audioTracks: b.audioTracks.filter((_, k) => k !== i) }), `Audio track ${i + 1} was removed.`)}>
              Remove track {i + 1}
            </button>
          </div>
        </fieldset>
      ))}
      <button
        disabled={audio.length === 0}
        title={audio.length === 0 ? "Import a music or ambience file on the Media tab first" : undefined}
        onClick={() =>
          edit((b) => ({
            ...b,
            audioTracks: [...b.audioTracks, { assetId: audio[0]?.id ?? "", role: "music", gainDb: -20, startMs: 0, fadeInMs: 0, fadeOutMs: 0, loop: true, duckDb: 10 }],
          }))
        }
      >
        Add music or ambience
      </button>
    </div>
  );
}
