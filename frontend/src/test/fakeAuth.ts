import type { ApiClient } from "../api/client";
import type { AuthClient, AuthUser } from "../auth/authClient";

export const USER_A: AuthUser = { uid: "uid-a", email: "a@example.com" };

/** Pass undefined to stay in the initial "still checking" state. */
export function createFakeAuth(initial: AuthUser | null | undefined) {
  const listeners = new Set<(user: AuthUser | null) => void>();
  const emit = (user: AuthUser | null) => listeners.forEach((l) => l(user));

  const client = {
    subscribe(listener: (user: AuthUser | null) => void) {
      listeners.add(listener);
      if (initial !== undefined) listener(initial);
      return () => listeners.delete(listener);
    },
    signIn: vi.fn(async () => emit(USER_A)),
    register: vi.fn(async () => emit(USER_A)),
    resetPassword: vi.fn(async () => {}),
    getToken: vi.fn(async () => (initial ? "token-a" : null)),
    signOut: vi.fn(async () => emit(null)),
  } satisfies AuthClient;

  return client;
}

/** By default every request returns an empty list (no targets). */
export function createFakeApi() {
  return {
    request: vi.fn(async () => []),
  } as unknown as ApiClient & { request: ReturnType<typeof vi.fn> };
}
