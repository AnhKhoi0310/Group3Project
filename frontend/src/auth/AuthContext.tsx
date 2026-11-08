import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ApiClient } from "../api/client";
import type { AuthClient, AuthUser } from "./authClient";

type Session =
  | { status: "loading"; user: null }
  | { status: "signedOut"; user: null }
  | { status: "signedIn"; user: AuthUser };

interface AuthContextValue {
  session: Session;
  client: AuthClient;
  api: ApiClient;
  logout(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  client,
  api,
  children,
}: {
  client: AuthClient;
  api: ApiClient;
  children: ReactNode;
}) {
  const [session, setSession] = useState<Session>({
    status: "loading",
    user: null,
  });

  useEffect(
    () =>
      client.subscribe((user) =>
        setSession(
          user
            ? { status: "signedIn", user }
            : { status: "signedOut", user: null },
        ),
      ),
    [client],
  );

  const value = useMemo(
    () => ({
      session,
      client,
      api,
      async logout() {
        try {
          // Revoke on the server so a copied token stops working too.
          await api.request("/api/auth/logout", { method: "POST" });
        } catch {
          // The user must still be signed out here if revocation fails.
        } finally {
          await client.signOut();
        }
      },
    }),
    [session, client, api],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
