import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { Storyboard } from "./Storyboard";
import { FakeApi, makeAsset, makeJob } from "./testing/fakeApi";

function setup() {
  const api = new FakeApi();
  const doc = api.addProject("Jonah");
  api.assets = [makeAsset({ id: "a-000000000001" })];
  return { api, pid: doc.projectId };
}

describe("render panel", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("saves pending edits before it starts a render, and labels drafts honestly", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    expect(screen.getByText(/No renders yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add scene" })); // an unsaved edit
    await user.click(screen.getByRole("button", { name: "Render draft" }));
    await waitFor(() => expect(api.called("startRender")).toHaveLength(1));
    expect(api.called("startRender")[0]?.args).toEqual([pid, true]);
    const order = api.calls.map((c) => c.method);
    expect(order.indexOf("saveStoryboard")).toBeGreaterThan(-1);
    expect(order.indexOf("saveStoryboard")).toBeLessThan(order.indexOf("startRender")); // never render stale data
    expect(await screen.findByRole("progressbar", { name: "Render progress" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Render draft" })).toBeDisabled(); // one render at a time
  });

  it("shows the worker's reasons when the storyboard is not ready, without starting a job", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    api.fail.set("startRender", new ApiError(409, "not_render_ready", "The storyboard is not ready to render: Gap of 500 ms before this shot."));
    await user.click(screen.getByRole("button", { name: "Render draft" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Gap of 500 ms");
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("does not render when the latest edits could not be saved", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    api.fail.set("saveStoryboard", new ApiError(507, "storage_error", "No space left on device."));
    await user.click(screen.getByRole("button", { name: "Add scene" }));
    await user.click(screen.getByRole("button", { name: "Render draft" }));
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(api.called("startRender")).toHaveLength(0);
    expect(screen.getByText(/nothing was rendered/)).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(1); // the edit is still on screen
  });

  it("lists finished renders with draft/final labels, a player, warnings, and cancel", async () => {
    const { api, pid } = setup();
    api.renders = [
      { file: "r-000000000002-final.mp4", draft: false, sizeBytes: 5_000_000, modified: 1_800_000_100 },
      { file: "r-000000000001-draft.mp4", draft: true, sizeBytes: 400_000, modified: 1_800_000_000 },
    ];
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Storyboard api={api} projectId={pid} />);
    expect(await screen.findByText("Final export")).toBeInTheDocument();
    const video = screen.getByLabelText("Final render") as HTMLVideoElement;
    expect(video.getAttribute("src")).toContain("/renders/r-000000000002-final.mp4");
    await user.selectOptions(screen.getByLabelText("Rendered videos"), "r-000000000001-draft.mp4");
    expect(screen.getByText("Draft proxy: not final quality")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Render draft" }));
    expect(await screen.findByText(/Encoding shot 1 of 2 \(30%\)/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel render" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });
    expect(await screen.findByText(/cancelled\. Nothing was published/)).toBeInTheDocument();
  });

  it("reports a failed render in plain words", async () => {
    const { api, pid } = setup();
    api.jobs = [makeJob({ id: "j-0000000000f2", kind: "render", state: "failed", error: "FFmpeg failed while encoding shot 'a'." })];
    render(<Storyboard api={api} projectId={pid} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The last render failed: FFmpeg failed while encoding shot 'a'. Nothing was published.");
  });
});
