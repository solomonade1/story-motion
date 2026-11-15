import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { Setup } from "./Setup";
import { FakeApi } from "./testing/fakeApi";

describe("Setup", () => {
  it("shows every check and lets you continue when all is well", async () => {
    const api = new FakeApi();
    const onContinue = vi.fn();
    render(<Setup api={api} onContinue={onContinue} />);
    expect(await screen.findByText("FFmpeg + ffprobe")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(onContinue).toHaveBeenCalled();
  });

  it("explains how to fix a failing check and still allows continuing", async () => {
    const api = new FakeApi();
    api.health_ = {
      ...api.health_, ok: false,
      checks: [{ id: "ffmpeg", label: "FFmpeg + ffprobe", status: "fail", detail: "Required tool(s) not found: ffmpeg.", fix: "Install FFmpeg and restart the app." }],
    };
    render(<Setup api={api} onContinue={() => undefined} />);
    expect(await screen.findByText(/How to fix: Install FFmpeg/)).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/importing and previews will not work/);
    expect(screen.getByRole("button", { name: "Continue anyway" })).toBeEnabled();
  });

  it("shows a clear message with a retry when the worker does not answer", async () => {
    const api = new FakeApi();
    api.fail.set("health", new ApiError(0, "unreachable", "The StoryMotion worker is not responding. Close and reopen the app."));
    render(<Setup api={api} onContinue={() => undefined} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("not responding");
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByText("FFmpeg + ffprobe")).toBeInTheDocument());
  });

  it("states that the app works offline", async () => {
    render(<Setup api={new FakeApi()} onContinue={() => undefined} />);
    expect(await screen.findByText(/No account, no internet connection/)).toBeInTheDocument();
  });
});
