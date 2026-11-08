import { ApiError, createApiClient } from "./client";

function respondWith(status: number, body?: unknown) {
  const fetchMock = vi.fn<
    (url: string, init: RequestInit) => Promise<Response>
  >(
    async () =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("createApiClient", () => {
  it("sends the current token as a bearer credential", async () => {
    const fetchMock = respondWith(200, { ok: true });
    const api = createApiClient("http://api.test", async () => "token-a");

    await expect(api.request("/api/me")).resolves.toEqual({ ok: true });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/me");
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer token-a",
    );
  });

  it("sends no credential when nobody is signed in", async () => {
    const fetchMock = respondWith(200, {});
    const api = createApiClient("http://api.test", async () => null);

    await api.request("/api/me");

    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.has("Authorization")).toBe(false);
  });

  it("returns nothing for an empty 204 response", async () => {
    respondWith(204);
    const api = createApiClient("http://api.test", async () => "token-a");

    await expect(api.request("/api/auth/logout")).resolves.toBeUndefined();
  });

  it("surfaces the backend's error code and message", async () => {
    respondWith(401, { code: "unauthenticated", message: "Please log in." });
    const api = createApiClient("http://api.test", async () => null);

    await expect(api.request("/api/me")).rejects.toMatchObject({
      status: 401,
      code: "unauthenticated",
      message: "Please log in.",
    });
  });

  it("uses a safe message when the error body isn't ours", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response("<html>Bad Gateway</html>", { status: 502 }),
      ),
    );
    const api = createApiClient("http://api.test", async () => "token-a");

    await expect(api.request("/api/me")).rejects.toMatchObject({
      code: "unexpected",
      message: "Something went wrong on our side. Please try again.",
    });
  });

  it("reports a network failure in user terms", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const api = createApiClient("http://api.test", async () => "token-a");

    const error = await api.request("/api/me").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("network_error");
    expect((error as ApiError).message).not.toContain("Failed to fetch");
  });
});
