import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { Media } from "./Media";
import { FakeApi, makeAsset, makeJob } from "./testing/fakeApi";

const PID = "p-000000000001";

describe("Media", () => {
  it("shows an empty state that tells you what to do", async () => {
    render(<Media api={new FakeApi()} projectId={PID} />);
    expect(await screen.findByText("No media yet")).toBeInTheDocument();
    expect(screen.getByText(/Your originals are never changed or moved/)).toBeInTheDocument();
  });

  it("lists assets with preview, details and a category you can change", async () => {
    const api = new FakeApi();
    api.assets = [makeAsset({ orig_name: "Scene 1.mp4", kind: "video", width: 1280, height: 720, duration_ms: 10000, fps: 24, size: 2694802 })];
    render(<Media api={api} projectId={PID} />);
    expect(await screen.findByText("Scene 1.mp4")).toBeInTheDocument();
    expect(screen.getByText(/1280×720 · 0:10 · 24 fps · 2\.6 MB/)).toBeInTheDocument();
    expect(screen.getByAltText("Preview of Scene 1.mp4")).toHaveAttribute("src", expect.stringContaining("/thumbs?token="));
    await userEvent.selectOptions(screen.getByLabelText("Category of Scene 1.mp4"), "character");
    await waitFor(() => expect(api.called("setCategory")[0]?.args).toEqual([PID, "a-000000000001", "character"]));
  });

  it("imports the listed paths (one per line, quotes removed) and reports what happened", async () => {
    const api = new FakeApi();
    render(<Media api={api} projectId={PID} />);
    await screen.findByText("No media yet");
    const box = screen.getByLabelText(/Full path of each file/);
    await userEvent.click(screen.getByLabelText("Link to the original"));
    await userEvent.type(box, '"C:\\Videos\\Scene 1.mp4"{Enter}C:\\Pictures\\harbour.png');
    await userEvent.click(screen.getByRole("button", { name: "Import" }));
    await waitFor(() => expect(api.called("startImport")).toHaveLength(1));
    expect(api.called("startImport")[0]?.args).toEqual([PID, ["C:\\Videos\\Scene 1.mp4", "C:\\Pictures\\harbour.png"], "link", undefined]);
    // progress is visible while the job runs
    expect(await screen.findByRole("progressbar", { name: "Import progress" })).toHaveAttribute("aria-valuenow", "20");
    // the job finishes with one added, one duplicate and one damaged file
    const job = api.jobs[0]!;
    api.assets = [makeAsset({ orig_name: "harbour.png" })];
    Object.assign(job, makeJob({
      id: job.id, state: "completed", progress: 1,
      result: {
        imported: [makeAsset()], cancelled: false,
        duplicates: [{ path: "C:\\x.png", existingId: "a-1", existingName: "harbour.png", message: "'x.png' is identical to 'harbour.png' which is already in the project." }],
        errors: [{ path: "C:\\bad.png", code: "corrupt_media", message: "'bad.png' could not be read as an image file. It looks damaged or incomplete." }],
      },
    }));
    expect(await screen.findByText(/could not be imported/, {}, { timeout: 3000 })).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Files that could not be imported" });
    expect(within(list).getByText(/looks damaged or incomplete/)).toBeInTheDocument();
    expect(screen.getByText(/is identical to 'harbour.png'/)).toBeInTheDocument();
    expect(await screen.findByText("harbour.png")).toBeInTheDocument(); // the library refreshed
  });

  it("a running job can be cancelled", async () => {
    const api = new FakeApi();
    api.jobs = [makeJob({ state: "running", progress: 0.4, message: "Importing Scene 2.mp4 (2 of 5)" })];
    render(<Media api={api} projectId={PID} />);
    expect(await screen.findByText(/Importing Scene 2.mp4/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(api.called("cancelJob")).toHaveLength(1));
  });

  it("flags missing files, keeps the rest usable, and relinks with a clear error for a wrong file", async () => {
    const api = new FakeApi();
    api.assets = [
      makeAsset({ id: "a-000000000001", orig_name: "gone.mp4", status: "missing", status_detail: "The file is no longer at C:\\old\\gone.mp4. Use Relink to point to it again." }),
      makeAsset({ id: "a-000000000002", orig_name: "fine.png" }),
    ];
    render(<Media api={api} projectId={PID} />);
    expect(await screen.findByRole("status")).toHaveTextContent("1 file is missing or changed. Your other media is unaffected.");
    expect(screen.getByText("Missing", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Relink…" })).toHaveLength(1); // only the broken one
    await userEvent.click(screen.getByRole("button", { name: "Relink…" }));
    const dlg = screen.getByRole("dialog");
    api.fail.set("relink", new ApiError(400, "invalid_input", "That file is not identical to the original (its contents differ), so it was not linked."));
    await userEvent.type(within(dlg).getByLabelText("New path"), "C:\\new\\other.mp4");
    await userEvent.click(within(dlg).getByRole("button", { name: "Relink" }));
    expect(await within(dlg).findByRole("alert")).toHaveTextContent("not identical to the original");
    await userEvent.click(within(dlg).getByRole("button", { name: "Relink" })); // second try succeeds
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(api.called("relink")).toHaveLength(2);
  });

  it("filters the library and can remove an item", async () => {
    const api = new FakeApi();
    api.assets = [
      makeAsset({ id: "a-000000000001", orig_name: "pic.png", category: "environment" }),
      makeAsset({ id: "a-000000000002", orig_name: "voice.wav", kind: "audio", category: "audio", thumbUrl: null }),
    ];
    render(<Media api={api} projectId={PID} />);
    await screen.findByText("pic.png");
    await userEvent.selectOptions(screen.getByLabelText("Filter media"), "audio");
    expect(screen.queryByText("pic.png")).not.toBeInTheDocument();
    expect(screen.getByText("voice.wav")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove voice.wav" }));
    await waitFor(() => expect(api.called("removeAsset")[0]?.args).toEqual([PID, "a-000000000002"]));
  });

  it("shows API errors instead of failing silently", async () => {
    const api = new FakeApi();
    api.fail.set("listAssets", new ApiError(503, "toolchain_missing", "Required tool(s) not found: ffmpeg. Install FFmpeg (see README 'Setup')."));
    render(<Media api={api} projectId={PID} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Install FFmpeg");
  });
});
