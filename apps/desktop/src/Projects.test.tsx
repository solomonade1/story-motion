import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { Projects } from "./Projects";
import { FakeApi } from "./testing/fakeApi";

function setup(api = new FakeApi()) {
  const onOpen = vi.fn();
  render(<Projects api={api} onOpen={onOpen} onSetup={() => undefined} />);
  return { api, onOpen };
}

describe("Projects", () => {
  it("shows a helpful empty state with a way to start", async () => {
    setup();
    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create your first project" })).toBeInTheDocument();
  });

  it("creates a project and opens it", async () => {
    const { api, onOpen } = setup();
    await userEvent.click(await screen.findByRole("button", { name: "New project" }));
    const dialog = screen.getByRole("dialog", { name: "New project" });
    expect(within(dialog).getByRole("button", { name: "Create" })).toBeDisabled(); // a name is required
    await userEvent.type(within(dialog).getByLabelText("Project name"), "  Hezekiah  ");
    await userEvent.click(within(dialog).getByRole("button", { name: "Create" }));
    await waitFor(() => expect(onOpen).toHaveBeenCalledWith("p-000000000001"));
    expect(api.called("createProject")[0]?.args).toEqual(["Hezekiah"]); // trimmed
  });

  it("lists, renames and duplicates projects", async () => {
    const api = new FakeApi();
    api.addProject("Jonah");
    setup(api);
    expect(await screen.findByRole("button", { name: "Jonah" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Rename" }));
    const field = screen.getByLabelText("Project name");
    expect(field).toHaveValue("Jonah");
    await userEvent.clear(field);
    await userEvent.type(field, "Jonah and the fish");
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Rename" }));
    expect(await screen.findByRole("button", { name: "Jonah and the fish" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Duplicate" }));
    expect(await screen.findByRole("button", { name: "Jonah and the fish (copy)" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Duplicated");
  });

  it("deleting needs confirmation, explains the trash, and can be restored", async () => {
    const api = new FakeApi();
    api.addProject("Doomed");
    setup(api);
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    const dlg = screen.getByRole("dialog");
    expect(dlg).toHaveTextContent("moves to the trash");
    await userEvent.click(within(dlg).getByRole("button", { name: "Keep it" }));
    expect(api.called("deleteProject")).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Move to trash" }));
    await waitFor(() => expect(screen.getByText("No projects yet")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /Trash \(1\)/ }));
    await userEvent.click(screen.getByRole("button", { name: "Restore" }));
    expect(await screen.findByRole("button", { name: "Doomed" })).toBeInTheDocument();
  });

  it("deleting forever requires typing the project's name", async () => {
    const api = new FakeApi();
    const d = api.addProject("Precious");
    await api.deleteProject(d.projectId);
    api.calls.length = 0;
    setup(api);
    await userEvent.click(await screen.findByRole("button", { name: /Trash \(1\)/ }));
    await userEvent.click(screen.getByRole("button", { name: "Delete forever…" }));
    const dlg = screen.getByRole("dialog", { name: "Delete forever?" });
    const confirm = within(dlg).getByRole("button", { name: "Delete forever" });
    expect(confirm).toBeDisabled();
    await userEvent.type(within(dlg).getByLabelText(/Type the project name/), "Precio");
    expect(confirm).toBeDisabled();
    await userEvent.type(within(dlg).getByLabelText(/Type the project name/), "us");
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    await waitFor(() => expect(api.called("purge")).toHaveLength(1));
  });

  it("archives a project and shows it under 'Show archived'", async () => {
    const api = new FakeApi();
    api.addProject("Old story");
    setup(api);
    await userEvent.click(await screen.findByRole("button", { name: "Archive" }));
    await waitFor(() => expect(screen.getByText("No projects yet")).toBeInTheDocument());
    await userEvent.click(screen.getByLabelText("Show archived projects"));
    expect(await screen.findByRole("button", { name: "Old story" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unarchive" })).toBeInTheDocument();
  });

  it("shows a readable error with Try again when loading fails", async () => {
    const api = new FakeApi();
    api.fail.set("listProjects", new ApiError(500, "internal_error", "Something went wrong inside the app. Your project files were not changed."));
    setup(api);
    expect(await screen.findByRole("alert")).toHaveTextContent("Your project files were not changed");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
  });

  it("Escape closes a dialog and returns focus to the button that opened it", async () => {
    setup();
    const open = await screen.findByRole("button", { name: "New project" });
    await userEvent.click(open);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(open).toHaveFocus();
  });
});
