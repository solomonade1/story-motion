import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient, workerPickerEnabled } from "./api";
import { enableWorkerPicker, hasNativePicker, pickPaths } from "./native";
import { useLeaveWarning } from "./useLeaveWarning";

afterEach(() => enableWorkerPicker(null));

describe("the app window's file chooser", () => {
  it("is on only when the worker says so in the URL", () => {
    expect(workerPickerEnabled({ hash: "#token=t&picker=1" })).toBe(true);
    expect(workerPickerEnabled({ hash: "#token=t&picker=0" })).toBe(false);
    expect(workerPickerEnabled({ hash: "#token=t" })).toBe(false);
  });

  it("goes through the worker when enabled, and says why when it is not", async () => {
    expect(hasNativePicker()).toBe(false);
    await expect(pickPaths({ multiple: true })).rejects.toThrow(/only available in the app window/);
    const fn = vi.fn(async () => ["C:\\a\\one.png"]);
    enableWorkerPicker(fn);
    expect(hasNativePicker()).toBe(true);
    await expect(pickPaths({ multiple: true, extensions: ["png"] })).resolves.toEqual(["C:\\a\\one.png"]);
    expect(fn).toHaveBeenCalledWith({ multiple: true, extensions: ["png"] });
    enableWorkerPicker(null);
    expect(hasNativePicker()).toBe(false);
  });

  it("the client asks the worker with the session token and returns only the paths", async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ paths: ["D:\\x\\y.wav"] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const c = new ApiClient({ origin: "http://api.test", token: "T0K" }, f as unknown as typeof fetch);
    await expect(c.pick({ kind: "files", multiple: false, extensions: ["wav"] })).resolves.toEqual(["D:\\x\\y.wav"]);
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/api/pick");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer T0K");
    expect(init.body).toBe('{"kind":"files","multiple":false,"extensions":["wav"]}');
  });
});

function Probe(props: { active: boolean }) {
  useLeaveWarning(props.active);
  return null;
}

describe("closing the window while work is running", () => {
  const leave = () => {
    const e = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(e);
    return e.defaultPrevented;
  };

  it("asks first only while a job is active, and stops asking when it ends", () => {
    const { rerender, unmount } = render(<Probe active={false} />);
    expect(leave()).toBe(false);
    rerender(<Probe active />);
    expect(leave()).toBe(true);
    rerender(<Probe active={false} />);
    expect(leave()).toBe(false);
    rerender(<Probe active />);
    unmount();
    expect(leave()).toBe(false); // no listener left behind
  });
});
