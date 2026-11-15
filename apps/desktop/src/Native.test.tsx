import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Media } from "./Media";
import * as native from "./native";
import { FakeApi, makeAsset } from "./testing/fakeApi";

const PID = "p-000000000001";
const BS = String.fromCharCode(92); // a backslash, so Windows-style paths are written without escape noise
const winPath = (...parts: string[]) => parts.join(BS);
const LF = String.fromCharCode(10);

describe("native pickers", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows no Browse button in a plain browser (typed paths remain)", async () => {
    render(<Media api={new FakeApi()} projectId={PID} />);
    await screen.findByText("No media yet");
    expect(screen.queryByRole("button", { name: "Browse…" })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Full path of each file/)).toBeInTheDocument();
  });

  it("inside the desktop window, Browse adds the chosen files to the list and keeps earlier ones", async () => {
    vi.spyOn(native, "hasNativePicker").mockReturnValue(true);
    const one = winPath("C:", "a", "one.png");
    const two = winPath("C:", "b", "two.mp4");
    const three = winPath("C:", "b", "three.wav");
    const pick = vi.spyOn(native, "pickPaths").mockResolvedValueOnce([one]).mockResolvedValueOnce([two, three]);
    render(<Media api={new FakeApi()} projectId={PID} />);
    await screen.findByText("No media yet");
    await userEvent.click(screen.getByRole("button", { name: "Browse…" }));
    await userEvent.click(screen.getByRole("button", { name: "Browse…" }));
    expect(pick).toHaveBeenCalledWith(expect.objectContaining({ multiple: true, extensions: expect.arrayContaining(["png", "mp4", "wav"]) }));
    expect(screen.getByLabelText(/Full path of each file/)).toHaveValue([one, two, three].join(LF));
  });

  it("cancelling the chooser changes nothing, and a chooser failure is shown", async () => {
    vi.spyOn(native, "hasNativePicker").mockReturnValue(true);
    const pick = vi.spyOn(native, "pickPaths").mockResolvedValueOnce([]).mockRejectedValueOnce(new Error("The file chooser could not open."));
    render(<Media api={new FakeApi()} projectId={PID} />);
    await screen.findByText("No media yet");
    await userEvent.click(screen.getByRole("button", { name: "Browse…" }));
    expect(screen.getByLabelText(/Full path of each file/)).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: "Browse…" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not open");
    expect(pick).toHaveBeenCalledTimes(2);
  });

  it("relink offers Browse for a single file and fills the path", async () => {
    vi.spyOn(native, "hasNativePicker").mockReturnValue(true);
    const moved = winPath("D:", "moved", "clip.mp4");
    vi.spyOn(native, "pickPaths").mockResolvedValue([moved]);
    const api = new FakeApi();
    api.assets = [makeAsset({ status: "missing", status_detail: "The file is no longer there. Use Relink to point to it again." })];
    render(<Media api={api} projectId={PID} />);
    await userEvent.click(await screen.findByRole("button", { name: "Relink…" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Browse…" }));
    await waitFor(() => expect(screen.getByLabelText("New path")).toHaveValue(moved));
  });
});
