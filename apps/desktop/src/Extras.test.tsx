import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Storyboard } from "./Storyboard";
import { leadTransition, parseDb } from "./storyboardLogic";
import { FakeApi, makeAsset } from "./testing/fakeApi";
import type { SbShot, Storyboard as Board } from "./types";

const NAR = "a-0000000000aa";
const BED = "a-0000000000bb";
const CLIP = "a-0000000000cc";

function shot(id: string, start: number, dur: number, extra: Partial<SbShot> = {}): SbShot {
  return {
    id, startMs: start, durationMs: dur, mode: "RENDERED", imageAssetId: null, clipAssetId: CLIP, characterIds: [], action: "", mustShow: [], avoid: [],
    preset: null, transition: { type: "cut", durationMs: 0 }, trimStartMs: 0, speed: 1, fitSpeed: false, layers: [], ...extra,
  };
}
function board(shots: SbShot[]): Board {
  return {
    storyboardVersion: "1.1.0", narrationAssetId: NAR, fadeInMs: 0, fadeOutMs: 0, audioTracks: [], characters: [],
    scenes: [{ id: "s1", title: "One", text: "", characterIds: [], shots }],
  };
}
function setup(sb: Board) {
  const api = new FakeApi();
  const doc = api.addProject("Hezekiah");
  api.assets = [
    makeAsset({ id: NAR, kind: "audio", category: "audio", orig_name: "narration.wav", duration_ms: 20000, thumbUrl: null, proxyUrl: null }),
    makeAsset({ id: BED, kind: "audio", category: "audio", orig_name: "ambience.wav", duration_ms: 30000, thumbUrl: null, proxyUrl: null }),
    makeAsset({ id: CLIP, kind: "video", category: "rendered_video", orig_name: "scene1.mp4", duration_ms: 8000 }),
  ];
  api.storyboards.set(doc.projectId, { sb, revision: 0 });
  return { api, pid: doc.projectId };
}

describe("leadTransition / parseDb", () => {
  it("moves only the cut: the dissolve then finishes where the shot used to start", () => {
    const b = board([shot("a", 0, 5000), shot("b", 5000, 5000, { transition: { type: "crossfade", durationMs: 500 } })]);
    const out = leadTransition(b, "b").scenes[0]!.shots;
    expect(out.map((s) => [s.startMs, s.durationMs])).toEqual([[0, 4500], [4500, 5500]]);
    expect(out[1]!.startMs + out[1]!.durationMs).toBe(10000); // the end of the timeline is unchanged
  });
  it("does nothing when there is no room, no transition, or it is the first shot", () => {
    const fade = { type: "crossfade" as const, durationMs: 500 };
    const tooShort = board([shot("a", 0, 400), shot("b", 400, 5000, { transition: fade })]);
    expect(leadTransition(tooShort, "b")).toBe(tooShort);
    const cut = board([shot("a", 0, 5000), shot("b", 5000, 5000)]);
    expect(leadTransition(cut, "b")).toBe(cut);
    const first = board([shot("a", 0, 5000, { transition: fade })]);
    expect(leadTransition(first, "a")).toBe(first);
    const gap = board([shot("a", 0, 4000), shot("b", 5000, 5000, { transition: fade })]);
    expect(leadTransition(gap, "b")).toBe(gap); // a gap is reported, never papered over
  });
  it("accepts decibel values only inside the range", () => {
    expect(parseDb("-18", -60, 12)).toBe(-18);
    expect(parseDb("-18.5", -60, 12)).toBe(-18.5);
    for (const bad of ["", "abc", "13", "-61", "1.234", "--3"]) expect(parseDb(bad, -60, 12)).toBeNull();
  });
});

describe("transitions, clip speed and audio beds in the editor", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());
  const quiet = () => act(async () => { await vi.advanceTimersByTimeAsync(900); });
  const saved = (api: FakeApi, pid: string) => api.storyboards.get(pid)!.sb;

  it("sets a transition, trim and slow-to-fit on a clip shot, and saves them", async () => {
    const { api, pid } = setup(board([shot("a", 0, 5000), shot("b", 5000, 5000)]));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot b,/ }));
    const ed = within(screen.getByRole("region", { name: "Edit shot b" }));
    await user.selectOptions(ed.getByLabelText("Transition into this shot"), "crossfade");
    const len = ed.getByLabelText("Transition length (ms)");
    expect(len).toHaveValue("500");
    await user.clear(len);
    await user.type(len, "700");
    await user.tab();
    await user.selectOptions(ed.getByLabelText("Clip speed"), "fit");
    const trim = ed.getByLabelText("Trim start of clip (ms)");
    await user.clear(trim);
    await user.type(trim, "1200{Enter}");
    await quiet();
    await waitFor(() => expect(saved(api, pid).scenes[0]!.shots[1]).toMatchObject({ transition: { type: "crossfade", durationMs: 700 }, fitSpeed: true, trimStartMs: 1200 }));
    await user.click(ed.getByRole("button", { name: "Finish the transition where this shot starts" }));
    await quiet();
    await waitFor(() => expect(saved(api, pid).scenes[0]!.shots.map((s) => s.startMs)).toEqual([0, 4300]));
    expect(screen.getByText(/The cut was moved earlier/)).toBeInTheDocument();
    await user.selectOptions(ed.getByLabelText("Transition into this shot"), "cut");
    await quiet();
    await waitFor(() => expect(saved(api, pid).scenes[0]!.shots[1]!.transition).toEqual({ type: "cut", durationMs: 0 }));
  });

  it("explains that the first shot cannot have a transition", async () => {
    const { api, pid } = setup(board([shot("a", 0, 5000), shot("b", 5000, 5000)]));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    const ed = within(screen.getByRole("region", { name: "Edit shot a" }));
    expect(ed.getByLabelText("Transition into this shot")).toBeDisabled();
    expect(ed.getByText(/Use the video fade-in/)).toBeInTheDocument();
    expect(ed.queryByLabelText("Transition length (ms)")).not.toBeInTheDocument();
  });

  it("adds, edits and removes a music bed, with validated numbers", async () => {
    const { api, pid } = setup(board([shot("a", 0, 20000)]));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: "Add music or ambience" }));
    const track = within(screen.getByRole("group", { name: "Audio track 1" }));
    // the narration is not offered as a bed
    expect(track.getByLabelText("File")).toHaveDisplayValue("ambience.wav");
    expect(within(track.getByLabelText("File")).queryByText("narration.wav")).not.toBeInTheDocument();
    await user.selectOptions(track.getByLabelText("Kind"), "ambience");
    const level = track.getByLabelText("Level (dB)");
    await user.clear(level);
    await user.type(level, "-18.5{Enter}");
    const duck = track.getByLabelText("Lower under narration by (dB)");
    await user.clear(duck);
    await user.type(duck, "45");
    expect(await screen.findByRole("alert")).toHaveTextContent("use a number from 0 to 30");
    await user.tab(); // invalid: not applied
    await user.clear(duck);
    await user.type(duck, "12{Enter}");
    const fadeOut = track.getByLabelText("Fade out (ms)");
    await user.clear(fadeOut);
    await user.type(fadeOut, "800{Enter}");
    await user.click(track.getByRole("checkbox"));
    await quiet();
    await waitFor(() => expect(saved(api, pid).audioTracks[0]).toMatchObject({ assetId: BED, role: "ambience", gainDb: -18.5, duckDb: 12, fadeOutMs: 800, loop: false }));
    await user.click(track.getByRole("button", { name: "Remove track 1" }));
    await quiet();
    await waitFor(() => expect(saved(api, pid).audioTracks).toEqual([]));
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("group", { name: "Audio track 1" })).toBeInTheDocument();
  });

  it("sets the video fade-in and fade-out", async () => {
    const { api, pid } = setup(board([shot("a", 0, 20000)]));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    const fin = await screen.findByLabelText("Video fade-in (ms)");
    await user.clear(fin);
    await user.type(fin, "600{Enter}");
    const fout = screen.getByLabelText("Video fade-out (ms)");
    await user.clear(fout);
    await user.type(fout, "1500{Enter}");
    await quiet();
    await waitFor(() => expect([saved(api, pid).fadeInMs, saved(api, pid).fadeOutMs]).toEqual([600, 1500]));
  });

  it("disables 'add music' with a hint when the library has no other audio", async () => {
    const { api, pid } = setup(board([shot("a", 0, 20000)]));
    api.assets = api.assets.filter((a) => a.id !== BED);
    render(<Storyboard api={api} projectId={pid} />);
    const btn = await screen.findByRole("button", { name: "Add music or ambience" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("title", expect.stringContaining("Import a music or ambience file"));
  });
});
