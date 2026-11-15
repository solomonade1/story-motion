import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { Storyboard } from "./Storyboard";
import { FakeApi, makeAsset, makeJob } from "./testing/fakeApi";

function setup() {
  const api = new FakeApi();
  const doc = api.addProject("Jonah");
  api.assets = [makeAsset({ id: "a-000000000001" })];
  return { api, pid: doc.projectId };
}

describe("export panel", () => {
  it("explains what each export is, that nothing is uploaded, and that the timelines are untested in editors", async () => {
    const { api, pid } = setup();
    render(<Storyboard api={api} projectId={pid} />);
    const panel = within(await screen.findByRole("region", { name: "Export" }));
    expect(panel.getByText(/Nothing is uploaded/)).toBeInTheDocument();
    expect(panel.getByText(/OpenTimelineIO for DaVinci Resolve, EDL for Premiere/)).toBeInTheDocument();
    expect(panel.getByText(/have not been tested in any editor yet/)).toBeInTheDocument();
    expect(panel.getByText(/script text and still frames/)).toBeInTheDocument();
  });

  it("saves pending edits first, then starts the chosen kind of export and shows progress and cancel", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup();
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    await user.click(screen.getByRole("button", { name: "Add scene" })); // an unsaved edit
    await user.click(screen.getByRole("button", { name: "Export for editing" }));
    await waitFor(() => expect(api.called("startExport")).toHaveLength(1));
    expect(api.called("startExport")[0]?.args).toEqual([pid, "full"]);
    const order = api.calls.map((c) => c.method);
    expect(order.indexOf("saveStoryboard")).toBeLessThan(order.indexOf("startExport")); // never export stale data
    expect(await screen.findByRole("progressbar", { name: "Export progress" })).toBeInTheDocument();
    expect(screen.getByText(/Encoding shot 2 of 5 \(40%\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export for editing" })).toBeDisabled(); // one at a time
    expect(screen.getByRole("button", { name: "Export brief for AI models" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Cancel export" }));
    expect(api.called("cancelJob")).toHaveLength(1);
  });

  it("starts the independent assets export with mode 'assets'", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup();
    render(<Storyboard api={api} projectId={pid} />);
    const panel = within(await screen.findByRole("region", { name: "Export" }));
    expect(panel.getByText(/plain files that need no editor and no StoryMotion/i)).toBeInTheDocument();
    expect(panel.getByText(/checksums to prove nothing was altered/)).toBeInTheDocument();
    await user.click(panel.getByRole("button", { name: "Export independent assets" }));
    await waitFor(() => expect(api.called("startExport")[0]?.args).toEqual([pid, "assets"]));
  });

  it("starts the light AI brief with mode 'brief'", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup();
    render(<Storyboard api={api} projectId={pid} />);
    await user.click(await screen.findByRole("button", { name: "Export brief for AI models" }));
    await waitFor(() => expect(api.called("startExport")[0]?.args).toEqual([pid, "brief"]));
  });

  it("shows the worker's reasons when the storyboard is not ready, and starts no job", async () => {
    const { api, pid } = setup();
    const user = userEvent.setup();
    render(<Storyboard api={api} projectId={pid} />);
    await screen.findByText(/No shots yet/);
    api.fail.set("startExport", new ApiError(409, "not_render_ready", "The storyboard is not ready to render: Gap of 600 ms before this shot."));
    await user.click(screen.getByRole("button", { name: "Export for editing" }));
    expect(await screen.findByText(/Gap of 600 ms/)).toBeInTheDocument();
    expect(screen.queryByRole("progressbar", { name: "Export progress" })).not.toBeInTheDocument();
  });

  it("lists exports and shows the folder, or says where it is when the window cannot open it", async () => {
    const { api, pid } = setup();
    api.exports = [
      { folder: "x-000000000002-full", mode: "full", sizeBytes: 250_000_000, modified: 1_800_000_100 },
      { folder: "x-000000000001-brief", mode: "brief", sizeBytes: 900_000, modified: 1_800_000_000 },
      { folder: "x-000000000003-assets", mode: "assets", sizeBytes: 400_000_000, modified: 1_800_000_200 },
    ];
    const user = userEvent.setup();
    render(<Storyboard api={api} projectId={pid} />);
    const list = within(await screen.findByRole("list", { name: "Exports" }));
    expect(list.getAllByRole("listitem")).toHaveLength(3);
    expect(list.getByText("Independent assets")).toBeInTheDocument();
    await user.click(list.getAllByRole("button", { name: /Show for editing export/ })[0]!);
    expect(await screen.findByText(/Opened C:\/Workspace\/exports\/x-000000000001-full/)).toBeInTheDocument();
    expect(api.called("openExport")[0]?.args).toEqual([pid, "x-000000000002-full"]);
    api.openedPath = { opened: false, path: "C:/Workspace/exports/x-000000000001-brief" };
    await user.click(list.getByRole("button", { name: /Show ai brief export/ }));
    expect(await screen.findByText(/This export is in: C:\/Workspace\/exports\/x-000000000001-brief/)).toBeInTheDocument();
  });

  it("reports a failed export in plain words and a finished one with its numbers", async () => {
    const { api, pid } = setup();
    api.jobs = [makeJob({ id: "j-0000000000e1", kind: "export", state: "failed", error: "FFmpeg failed while encoding shot 'a'." })];
    const { unmount } = render(<Storyboard api={api} projectId={pid} />);
    expect(await screen.findByText(/The last export failed: FFmpeg failed while encoding shot 'a'\. Nothing was published\./)).toBeInTheDocument();
    unmount();
  });
});
