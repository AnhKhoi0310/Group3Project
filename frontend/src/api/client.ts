export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
  }
}

export interface ApiClient {
  request<T>(path: string, init?: RequestInit): Promise<T>;
}

const NETWORK_MESSAGE =
  "We couldn't reach ReviewLens. Check your connection and try again.";
const UNEXPECTED_MESSAGE =
  "Something went wrong on our side. Please try again.";

export function createApiClient(
  baseUrl: string,
  getToken: () => Promise<string | null>,
): ApiClient {
  return {
    async request<T>(path: string, init: RequestInit = {}): Promise<T> {
      const token = await getToken();
      const headers = new Headers(init.headers);
      if (token) headers.set("Authorization", `Bearer ${token}`);

      let response: Response;
      try {
        response = await fetch(`${baseUrl}${path}`, { ...init, headers });
      } catch {
        throw new ApiError(0, "network_error", NETWORK_MESSAGE);
      }

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new ApiError(
          response.status,
          body?.code ?? "unexpected",
          body?.message ?? UNEXPECTED_MESSAGE,
          body?.fieldErrors ?? {},
        );
      }

      return (response.status === 204 ? undefined : await response.json()) as T;
    },
  };
}
