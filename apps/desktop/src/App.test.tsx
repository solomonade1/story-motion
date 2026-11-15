import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { FakeApi } from "./testing/fakeApi";

describe("App", () => {
  it("asks to be opened from the app when there is no session key", () => {
    window.location.hash = "";
    render(<App />);
    expect(screen.getByRole("alert")).toHaveTextContent("opened from the StoryMotion app");
  });

  it("goes from the setup check to the projects and into a project", async () => {
    const api = new FakeApi();
    api.addProject("Hezekiah");
    render(<App api={api} />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Hezekiah" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Media", selected: true })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to all projects" }));
    expect(await screen.findByRole("heading", { name: "Your projects" })).toBeInTheDocument();
  });
});
