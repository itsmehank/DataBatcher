import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

describe("api error handling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses JSON detail message when present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Invalid region" }), { status: 400 }))
    );

    await expect(api.getDates("US")).rejects.toThrow("Invalid region");
  });

  it("falls back to plain text error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("Something failed", { status: 500 }))
    );

    await expect(api.getMarkets("US")).rejects.toThrow("Something failed");
  });

  it("falls back to status message when body is empty", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));

    await expect(api.getMarkets("US")).rejects.toThrow("Request failed: 503");
  });
});
