import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Storyboard } from "./Storyboard";
import { addShot, fitLastToNarration, moveShot, parseWholeMs, reflow } from "./storyboardLogic";
import { FakeApi, makeAsset } from "./testing/fakeApi";
import type { Storyboard as Board } from "./types";

const IMG = "a-000000000001";
const DEFAULTS = { transition: { type: "cut" as const, durationMs: 0 }, trimStartMs: 0, speed: 1, fitSpeed: false, layers: [] };
const NAR = "a-0000000000aa";

function setup(extra?: (api: FakeApi, pid: string) => void) {
  const api = new FakeApi();
  const doc = api.addProject("Jonah");
  api.assets = [makeAsset({ id: IMG, orig_name: "harbour.png" }), makeAsset({ id: NAR, kind: "audio", category: "audio", orig_name: "voice.wav", duration_ms: 20000, thumbUrl: null, proxyUrl: null })];
  extra?.(api, doc.projectId);
  return { api, pid: doc.projectId };
}

function board(): Board {
  return {
    storyboardVersion: "1.0.0",
    narrationAssetId: NAR,
    fadeInMs: 0,
    fadeOutMs: 0,
    audioTracks: [],
    characters: [{ id: "jonah", name: "Jonah" }],
    scenes: [
      {
        id: "s1", title: "The call", text: "", characterIds: [],
        shots: [
          { id: "a", startMs: 0, durationMs: 5000, mode: "STATIC", imageAssetId: IMG, clipAssetId: null, characterIds: [], action: "", mustShow: [], avoid: [], preset: null, ...DEFAULTS },
          { id: "b", startMs: 6000, durationMs: 4000, mode: "STATIC", imageAssetId: IMG, clipAssetId: null, characterIds: [], action: "", mustShow: [], avoid: [], preset: null, ...DEFAULTS },
        ],
      },
    ],
  };
}

describe("storyboard logic", () => {
  it("reflow closes gaps and overlaps, keeping order and durations", () => {
    const b = board();
    b.scenes[0]!.shots[1]!.startMs = 3000; // overlap
    const out = reflow(b).scenes[0]!.shots;
    expect(out.map((s) => [s.startMs, s.durationMs])).toEqual([[0, 5000], [5000, 4000]]);
    expect(b.scenes[0]!.shots[1]!.startMs).toBe(3000); // input untouched
  });
  it("moving a shot never silently changes times", () => {
    const out = moveShot(board(), "a", 1).scenes[0]!.shots;
    expect(out.map((s) => s.id)).toEqual(["b", "a"]);
    expect(out.map((s) => s.startMs)).toEqual([6000, 0]);
    expect(moveShot(board(), "a", -1).scenes[0]!.shots.map((s) => s.id)).toEqual(["a", "b"]);
  });
  it("a new shot starts where the timeline ends and stops at the narration", () => {
    const r = addShot(board(), "s1", 11000);
    const added = r.sb.scenes[0]!.shots.at(-1)!;
    expect([added.id, added.startMs, added.durationMs]).toEqual(["shot-1", 10000, 1000]);
  });
  it("fits the last shot to the narration end", () => {
    expect(fitLastToNarration(board(), 12000).scenes[0]!.shots[1]!.durationMs).toBe(6000);
  });
  it("accepts only whole milliseconds", () => {
    expect(parseWholeMs("1500", 1)).toBe(1500);
    for (const bad of ["", "1.5", "-3", "0", "abc", "1e3", " "]) expect(parseWholeMs(bad, 1)).toBeNull();
    expect(parseWholeMs("0", 0)).toBe(0);
  });
});

describe("storyboard editor", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());
  const quiet = () => act(async () => { await vi.advanceTimersByTimeAsync(900); });

  it("shows an empty state, lets you add a scene and a shot, and autosaves once", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    expect(await screen.findByText(/No shots yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add scene" }));
    await user.click(screen.getByRole("button", { name: "Add shot to this scene" }));
    expect(api.called("saveStoryboard")).toHaveLength(0); // debounced
    await quiet();
    await waitFor(() => expect(api.called("saveStoryboard")).toHaveLength(1));
    const saved = api.storyboards.get(pid)!.sb;
    expect(saved.scenes[0]!.shots[0]).toMatchObject({ id: "shot-1", startMs: 0, durationMs: 3000, mode: "STATIC" });
    expect(await screen.findByText("All changes saved")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Edit shot shot-1" })).toBeInTheDocument();
  });

  it("edits a shot's fields and saves them (narration, picture, mode, action, must show, avoid, characters)", async () => {
    const { api, pid } = setup((a, p) => {
      a.storyboards.set(p, { sb: { ...board(), narrationAssetId: null }, revision: 0 });
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.selectOptions(await screen.findByLabelText(/Narration/), NAR);
    await user.click(screen.getByRole("button", { name: /Shot a, 0:00.000 to 0:05.000/ }));
    const editor = within(screen.getByRole("region", { name: "Edit shot a" }));
    await user.selectOptions(editor.getByLabelText("Animation mode"), "CINEMATIC");
    await user.selectOptions(editor.getByLabelText("Motion preset"), "slow-push-in");
    await user.type(editor.getByLabelText(/Action/), "Jonah listens");
    await user.type(editor.getByLabelText(/Must show/), "Jonah{Enter}the storm");
    await user.type(editor.getByLabelText(/Avoid/), "fish");
    await user.click(editor.getByRole("checkbox", { name: "Jonah" }));
    await quiet();
    await waitFor(() => expect(api.called("saveStoryboard").length).toBeGreaterThan(0));
    const a = api.storyboards.get(pid)!.sb.scenes[0]!.shots[0]!;
    expect(a).toMatchObject({ mode: "CINEMATIC", preset: "slow-push-in", action: "Jonah listens", mustShow: ["Jonah", "the storm"], avoid: ["fish"], characterIds: ["jonah"] });
    expect(api.storyboards.get(pid)!.sb.narrationAssetId).toBe(NAR);
  });

  it("rejects non-integer or non-positive times next to the field and never sends them", async () => {
    const { api, pid } = setup((a, p) => a.storyboards.set(p, { sb: board(), revision: 0 }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    const dur = within(screen.getByRole("region", { name: "Edit shot a" })).getByLabelText("Duration (ms)");
    await user.clear(dur);
    await user.type(dur, "0");
    expect(await screen.findByRole("alert")).toHaveTextContent("whole milliseconds, 1 or more");
    await user.clear(dur);
    await user.type(dur, "12.5");
    expect(screen.getByRole("alert")).toHaveTextContent("keeps 5000 ms");
    await user.tab(); // leaving the field must not apply an invalid value
    await quiet();
    expect(api.called("saveStoryboard")).toHaveLength(0);
    expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots[0]!.durationMs).toBe(5000);
    await user.clear(dur);
    await user.type(dur, "4500");
    await user.tab();
    await quiet();
    await waitFor(() => expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots[0]!.durationMs).toBe(4500));
  });

  it("lists timing problems from the worker, flags the shot on the timeline and jumps to it", async () => {
    const { api, pid } = setup((a, p) => {
      a.storyboards.set(p, { sb: board(), revision: 0 });
      a.diagnostics = [{ severity: "warning", code: "gap", where: "shot b", message: "Gap of 1000 ms before this shot (expected start 5000 ms).", shotId: "b" }];
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    expect(await screen.findByText(/Gap of 1000 ms/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Shot b, .*has a problem/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show b" }));
    expect(screen.getByRole("region", { name: "Edit shot b" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close gaps and overlaps" }));
    await quiet();
    await waitFor(() => expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots[1]!.startMs).toBe(5000));
    expect(screen.getByText("Shot times were re-flowed back to back.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" })); // the repair is reversible
    await quiet();
    await waitFor(() => expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots[1]!.startMs).toBe(6000));
  });

  it("scrubbing shows which shot is on screen, and says so when there is a gap", async () => {
    const { api, pid } = setup((a, p) => a.storyboards.set(p, { sb: board(), revision: 0 }));
    render(<Storyboard api={api} projectId={pid} />);
    const slider = await screen.findByLabelText("Scrub position");
    const set = (v: number) => {
      // range inputs are controlled by React: use the native setter so onChange fires
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      act(() => {
        setter.call(slider, String(v));
        slider.dispatchEvent(new Event("input", { bubbles: true }));
      });
    };
    set(1000);
    expect(screen.getByText("a", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByAltText("Draft still for a")).toHaveAttribute("src", expect.stringContaining("/proxies?token"));
    expect(screen.getByText(/not shown; the final export is the reference/)).toBeInTheDocument();
    set(5500);
    expect(screen.getByText(/No shot at this moment/)).toBeInTheDocument();
  });

  it("imports a script, but asks before replacing existing shots", async () => {
    const { api, pid } = setup((a, p) => a.storyboards.set(p, { sb: board(), revision: 0 }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = render(<Storyboard api={api} projectId={pid} />);
    await screen.findByLabelText("Scrub position");
    const input = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0]!;
    await user.upload(input, new File(["First part.\n\nSecond part."], "jonah.txt", { type: "text/plain" }));
    expect(await screen.findByRole("dialog", { name: "Replace the current storyboard?" })).toBeInTheDocument();
    expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots).toHaveLength(2); // nothing replaced yet
    await user.click(screen.getByRole("button", { name: "Keep what I have" }));
    expect(api.storyboards.get(pid)!.sb.scenes[0]!.shots).toHaveLength(2);
    await user.upload(input, new File(["First part.\n\nSecond part."], "jonah.txt", { type: "text/plain" }));
    await user.click(await screen.findByRole("button", { name: "Replace it" }));
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(2));
    expect(screen.getByText("First part.")).toBeInTheDocument();
  });

  it("shows field-located problems for a bad plan and keeps the existing storyboard", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    const input = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[1]!;
    await user.upload(input, new File(["{ not json"], "plan.json", { type: "application/json" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Nothing was saved");
    expect(alert).toHaveTextContent("line 1, column 2");
    expect(api.storyboards.get(pid)?.sb.scenes ?? []).toHaveLength(0);
  });

  it("keeps edits on screen when saving fails, and a conflict asks for a reload", async () => {
    const { api, pid } = setup();
    const { ApiError } = await import("./api");
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    api.fail.set("saveStoryboard", new ApiError(507, "storage_error", "No space left on device."));
    await user.click(screen.getByRole("button", { name: "Add scene" }));
    await quiet();
    expect(await screen.findByRole("alert")).toHaveTextContent("No space left on device");
    expect(screen.getByRole("alert")).toHaveTextContent("have not been lost");
    expect(screen.getAllByRole("article")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(api.storyboards.get(pid)!.sb.scenes).toHaveLength(1));
    api.fail.set("saveStoryboard", new ApiError(409, "stale_revision", "This project changed since you opened it."));
    await user.click(screen.getByRole("button", { name: "Add scene" }));
    await quiet();
    expect(await screen.findByRole("button", { name: "Reload storyboard" })).toBeInTheDocument();
  });

  it("removing a scene with shots asks first, and can be undone", async () => {
    const { api, pid } = setup((a, p) => a.storyboards.set(p, { sb: board(), revision: 0 }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: "Remove scene" }));
    const dlg = screen.getByRole("dialog");
    await user.click(within(dlg).getByRole("button", { name: "Remove scene" }));
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("article")).toBeInTheDocument();
  });
});
