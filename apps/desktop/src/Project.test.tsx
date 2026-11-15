import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { ProjectScreen } from "./Project";
import { FakeApi } from "./testing/fakeApi";

async function openScriptTab(api: FakeApi, id: string, user: ReturnType<typeof userEvent.setup>) {
  render(<ProjectScreen api={api} projectId={id} onBack={() => undefined} />);
  await screen.findByRole("heading", { level: 1 });
  await user.click(screen.getByRole("tab", { name: "Script & notes" }));
  return screen.getByLabelText(/Script \(one narration paragraph per line\)/);
}

describe("autosave", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("saves once, with the latest text, after typing stops", async () => {
    const api = new FakeApi();
    const doc = api.addProject("Hezekiah");
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const box = await openScriptTab(api, doc.projectId, user);
    await user.type(box, "Hezekiah was dying.");
    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("Unsaved changes");
    expect(api.called("saveDocument")).toHaveLength(0); // still debouncing: no request per keystroke
    await act(async () => {
      await vi.advanceTimersByTimeAsync(900);
    });
    await waitFor(() => expect(api.called("saveDocument")).toHaveLength(1));
    expect(api.called("saveDocument")[0]?.args).toEqual([doc.projectId, { script: "Hezekiah was dying." }, 0]);
    expect(await screen.findByText("All changes saved")).toBeInTheDocument();
    expect(api.docs.get(doc.projectId)?.revision).toBe(1);
  });

  it("keeps the text on screen when a save fails, and the retry saves it", async () => {
    const api = new FakeApi();
    const doc = api.addProject("P");
    api.fail.set("saveDocument", new ApiError(507, "storage_error", "Could not save project.json: No space left on device. Your previous version is untouched."));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const box = await openScriptTab(api, doc.projectId, user);
    await user.type(box, "Precious words");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(900);
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("No space left on device");
    expect(screen.getByRole("alert")).toHaveTextContent("has not been lost");
    expect(box).toHaveValue("Precious words"); // never dropped
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(api.docs.get(doc.projectId)?.script).toBe("Precious words"));
    expect(await screen.findByText("All changes saved")).toBeInTheDocument();
  });

  it("stops and asks for a reload when the project changed elsewhere (never overwrites)", async () => {
    const api = new FakeApi();
    const doc = api.addProject("P");
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const box = await openScriptTab(api, doc.projectId, user);
    api.docs.get(doc.projectId)!.revision = 5; // someone else saved meanwhile
    await user.type(box, "mine");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(900);
    });
    expect(await screen.findByText("This project was changed somewhere else")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload project" })).toBeInTheDocument();
    const attempts = api.called("saveDocument").length;
    await user.type(box, " more");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(api.called("saveDocument")).toHaveLength(attempts); // no more attempts while in conflict
    expect(api.docs.get(doc.projectId)?.script).toBe(""); // and nothing was overwritten
    await user.click(screen.getByRole("button", { name: "Reload project" }));
    await waitFor(() => expect(api.called("getProject").length).toBeGreaterThan(1));
  });

  it("saves pending edits when the panel closes", async () => {
    const api = new FakeApi();
    const doc = api.addProject("P");
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const box = await openScriptTab(api, doc.projectId, user);
    await user.type(box, "quick");
    await user.click(screen.getByRole("tab", { name: "Media" })); // leaves the editor before the debounce fires
    await waitFor(() => expect(api.docs.get(doc.projectId)?.script).toBe("quick"));
  });
});

describe("project screen", () => {
  it("shows recovery warnings from a restored backup", async () => {
    const api = new FakeApi();
    const doc = api.addProject("Recovered");
    api.warnings = ["The latest project file was damaged, so the previous saved version was restored. The damaged file was kept next to it."];
    render(<ProjectScreen api={api} projectId={doc.projectId} onBack={() => undefined} />);
    expect(await screen.findByRole("status")).toHaveTextContent("previous saved version was restored");
  });

  it("shows a clear message when the project cannot be opened", async () => {
    const api = new FakeApi();
    render(<ProjectScreen api={api} projectId="p-999999999999" onBack={() => undefined} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("no longer exists");
  });
});
