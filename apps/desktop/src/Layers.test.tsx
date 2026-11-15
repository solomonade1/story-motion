import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Storyboard } from "./Storyboard";
import { defaultLayer, ease, layerCss, layerPoseAt, parseNum } from "./storyboardLogic";
import { FakeApi, makeAsset } from "./testing/fakeApi";
import type { SbLayer, SbShot, Storyboard as Board } from "./types";

const NAR = "a-0000000000aa";
const BG = "a-0000000000b1";
const DOT = "a-0000000000b2";

function shot(extra: Partial<SbShot> = {}): SbShot {
  return {
    id: "a", startMs: 0, durationMs: 4000, mode: "LAYERED", imageAssetId: BG, clipAssetId: null, characterIds: [], action: "", mustShow: [], avoid: [],
    preset: null, transition: { type: "cut", durationMs: 0 }, trimStartMs: 0, speed: 1, fitSpeed: false, layers: [], ...extra,
  };
}
function setup(layers: SbLayer[] = []) {
  const api = new FakeApi();
  const doc = api.addProject("Jonah");
  api.assets = [
    makeAsset({ id: NAR, kind: "audio", category: "audio", orig_name: "voice.wav", duration_ms: 4000, thumbUrl: null, proxyUrl: null }),
    makeAsset({ id: BG, orig_name: "harbour.png" }),
    makeAsset({ id: DOT, orig_name: "jonah.png", category: "character" }),
  ];
  const sb: Board = {
    storyboardVersion: "1.1.0", narrationAssetId: NAR, fadeInMs: 0, fadeOutMs: 0, audioTracks: [], characters: [],
    scenes: [{ id: "s1", title: "One", text: "", characterIds: [], shots: [shot({ layers })] }],
  };
  api.storyboards.set(doc.projectId, { sb, revision: 0 });
  return { api, pid: doc.projectId };
}

describe("layer logic", () => {
  it("interpolates position, size and tilt with the renderer's easing", () => {
    const l: SbLayer = { ...defaultLayer(DOT), easing: "linear", end: { x: 0.75, y: 0.5, widthFrac: 0.35, rotateDeg: 90 } };
    expect(layerPoseAt(l, 0, 4000)).toEqual({ x: 0.25, y: 0.5, widthFrac: 0.25, rotateDeg: 0 });
    expect(layerPoseAt(l, 0.5, 4000)).toMatchObject({ x: 0.5, widthFrac: 0.3, rotateDeg: 45 });
    expect(layerPoseAt(l, 2, 4000).x).toBe(0.75); // clamped
    expect(ease("easeInOut", 0.5)).toBe(0.5);
    expect(ease("easeIn", 0.5)).toBe(0.25);
    expect(ease("easeOut", 0.5)).toBe(0.75);
  });
  it("adds a sinusoidal rocking on top of the tilt", () => {
    const l: SbLayer = { ...defaultLayer(DOT), easing: "linear", swayDeg: 10, swayPeriodMs: 4000 };
    expect(layerPoseAt(l, 0.25, 4000).rotateDeg).toBeCloseTo(10, 6); // a quarter period in: peak of the sine
    expect(layerPoseAt(l, 0.5, 4000).rotateDeg).toBeCloseTo(0, 6);
  });
  it("turns the layer about its pivot, which is placed at (x, y)", () => {
    const l: SbLayer = { ...defaultLayer(DOT), pivotX: 0, pivotY: 0.5 };
    const css = layerCss(l, { x: 0.5, y: 0.4, widthFrac: 0.2, rotateDeg: 90 });
    expect(css).toMatchObject({ left: "50%", top: "40%", width: "20%", transformOrigin: "0% 50%", transform: "translate(-0%, -50%) rotate(90deg)" });
  });
  it("parses numbers with up to three decimals inside a range only", () => {
    expect(parseNum("0.125", 0, 1)).toBe(0.125);
    expect(parseNum("-0.5", -0.5, 1.5)).toBe(-0.5);
    for (const bad of ["", "abc", "1.2345", "2", "-1", "1e2"]) expect(parseNum(bad, 0, 1)).toBeNull();
  });
});

describe("layer editor", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());
  const quiet = () => act(async () => { await vi.advanceTimersByTimeAsync(900); });
  const layersOf = (api: FakeApi, pid: string) => api.storyboards.get(pid)!.sb.scenes[0]!.shots[0]!.layers;

  it("adds a layer on the other picture, and saves it", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    await user.click(screen.getByRole("button", { name: "Add layer" }));
    await quiet();
    await waitFor(() => expect(layersOf(api, pid)).toHaveLength(1));
    expect(layersOf(api, pid)[0]).toMatchObject({ assetId: DOT, pivotX: 0.5, easing: "easeInOut" }); // not the background itself
    expect(screen.getByRole("group", { name: "Layer 1" })).toBeInTheDocument();
    const stage = screen.getByRole("img", { name: "Layer placement preview" });
    expect(stage.querySelector("img.layer-img")?.getAttribute("src")).toContain(`/assets/${DOT}/alpha`); // keeps transparency
  });

  it("edits pose, pivot and rocking with validation, and previews at a position in the shot", async () => {
    const { api, pid } = setup([{ ...defaultLayer(DOT), easing: "linear" }]);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    const end = within(screen.getByRole("group", { name: "Layer 1 end" }));
    const x = end.getByLabelText("End x");
    await user.clear(x);
    await user.type(x, "1.2{Enter}");
    const tilt = end.getByLabelText("End tilt (deg)");
    await user.clear(tilt);
    await user.type(tilt, "400");
    expect(await screen.findByRole("alert")).toHaveTextContent("use a number from -360 to 360");
    await user.clear(tilt);
    await user.type(tilt, "90{Enter}");
    const layer = within(screen.getByRole("group", { name: "Layer 1" }));
    const px = layer.getByLabelText(/Pivot x/);
    await user.clear(px);
    await user.type(px, "0{Enter}");
    await user.selectOptions(layer.getByLabelText("Movement"), "linear");
    await quiet();
    await waitFor(() => expect(layersOf(api, pid)[0]).toMatchObject({ pivotX: 0, easing: "linear", end: { x: 1.2, rotateDeg: 90 } }));

    const img = screen.getByRole("img", { name: "Layer placement preview" }).querySelector("img.layer-img") as HTMLImageElement;
    expect(img.style.left).toBe("25%"); // at 0% of the shot: start pose
    const slider = screen.getByLabelText("Layer preview position");
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    act(() => {
      setter.call(slider, "100");
      slider.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(img.style.left).toBe("120%"); // at 100%: the end pose, off-screen to the right as allowed
    expect(img.style.transform).toBe("translate(-0%, -50%) rotate(90deg)");
  });

  it("reorders and removes layers", async () => {
    const { api, pid } = setup([defaultLayer(DOT), { ...defaultLayer(BG), end: { x: 0.9, y: 0.5, widthFrac: 0.25, rotateDeg: 0 } }]);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    await user.click(screen.getByRole("button", { name: "Move layer 1 forward" }));
    await quiet();
    await waitFor(() => expect(layersOf(api, pid).map((l) => l.assetId)).toEqual([BG, DOT]));
    expect(screen.getByRole("button", { name: "Move layer 2 forward" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Remove layer 1" }));
    await quiet();
    await waitFor(() => expect(layersOf(api, pid).map((l) => l.assetId)).toEqual([DOT]));
  });

  it("only appears for LAYERED shots and explains what a layer needs", async () => {
    const { api, pid } = setup();
    api.storyboards.get(pid)!.sb.scenes[0]!.shots[0]!.mode = "STATIC";
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: /Shot a,/ }));
    expect(screen.queryByRole("button", { name: "Add layer" })).not.toBeInTheDocument();
    await user.selectOptions(within(screen.getByRole("region", { name: "Edit shot a" })).getByLabelText("Animation mode"), "LAYERED");
    expect(screen.getByRole("button", { name: "Add layer" })).toBeInTheDocument();
    expect(screen.getByText(/transparent background/)).toBeInTheDocument();
  });
});
