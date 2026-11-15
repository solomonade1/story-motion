import { describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError, readConfig } from "./api";

describe("readConfig", () => {
  it("reads the session token from the URL fragment", () => {
    expect(readConfig({ origin: "http://127.0.0.1:5000", hash: "#token=abc123" })).toEqual({ origin: "http://127.0.0.1:5000", token: "abc123" });
  });
  it("lets the fragment name a different API origin (dev server) and trims a trailing slash", () => {
    expect(readConfig({ origin: "http://127.0.0.1:5173", hash: "#token=t&api=http://127.0.0.1:9000/" })).toEqual({
      origin: "http://127.0.0.1:9000",
      token: "t",
    });
  });
  it("returns null without a token", () => {
    expect(readConfig({ origin: "http://x", hash: "" })).toBeNull();
    expect(readConfig({ origin: "http://x", hash: "#api=http://y" })).toBeNull();
  });
});

function client(res: () => Response | Promise<Response>) {
  const f = vi.fn(async () => res());
  return { c: new ApiClient({ origin: "http://api.test", token: "SECRET/+=" }, f as unknown as typeof fetch), f };
}
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("ApiClient", () => {
  it("sends the bearer token and JSON body, and returns the parsed result", async () => {
    const { c, f } = client(() => json(201, { projectId: "p-1", name: "X" }));
    const doc = await c.createProject("X");
    expect(doc.name).toBe("X");
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/api/projects");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer SECRET/+=");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"name":"X"}');
  });

  it("turns the server's error body into an ApiError with code and the readable message", async () => {
    const { c } = client(() => json(409, { error: { code: "stale_revision", message: "Reload before saving." } }));
    await expect(c.saveDocument("p-1", { script: "x" }, 0)).rejects.toMatchObject({ status: 409, code: "stale_revision", message: "Reload before saving." });
  });

  it("copes with a non-JSON error page", async () => {
    const { c } = client(() => new Response("<html>oops</html>", { status: 502 }));
    const err = await c.health().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toContain("502");
  });

  it("reports an unreachable worker in plain words", async () => {
    const c = new ApiClient({ origin: "http://api.test", token: "t" }, (() => Promise.reject(new TypeError("fetch failed"))) as unknown as typeof fetch);
    await expect(c.health()).rejects.toMatchObject({ code: "unreachable", message: expect.stringContaining("not responding") });
  });

  it("puts the token (URL-encoded) only on media URLs", () => {
    const { c } = client(() => json(200, {}));
    expect(c.mediaUrl("p-1", "a-1", "thumbs")).toBe("http://api.test/api/projects/p-1/assets/a-1/thumbs?token=SECRET%2F%2B%3D");
  });

  it("builds the narrow routes it uses", async () => {
    const { c, f } = client(() => json(200, { projects: [], assets: [], jobs: [], trash: [] }));
    await c.listProjects(true);
    await c.listAssets("p-1");
    await c.listJobs("p-1");
    await c.purge("t-1").catch(() => undefined);
    const urls = f.mock.calls.map((x) => (x as unknown as [string, RequestInit])[0]);
    expect(urls).toEqual([
      "http://api.test/api/projects?archived=1",
      "http://api.test/api/projects/p-1/assets",
      "http://api.test/api/projects/p-1/jobs",
      "http://api.test/api/trash/t-1/purge",
    ]);
    expect((f.mock.calls[3] as unknown as [string, RequestInit])[1].body).toBe('{"confirm":true}'); // permanent deletion is always explicit
  });
});
