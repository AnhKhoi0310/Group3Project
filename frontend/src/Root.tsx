import { useMemo } from "react";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { createApiClient } from "./api/client";
import { AuthProvider } from "./auth/AuthContext";
import { createFirebaseAuthClient, type AuthClient } from "./auth/authClient";
import {
  ConfigurationError,
  loadConfig,
  type AppConfig,
  type AppEnv,
} from "./config/env";

interface RootProps {
  env: AppEnv;
  createAuthClient?: (config: AppConfig["firebase"]) => AuthClient;
}

function start(
  env: AppEnv,
  createAuthClient: NonNullable<RootProps["createAuthClient"]>,
) {
  try {
    const config = loadConfig(env);
    const client = createAuthClient(config.firebase);
    const api = createApiClient(config.apiBaseUrl, () => client.getToken());
    return { client, api, problem: null };
  } catch (error) {
    if (!(error instanceof ConfigurationError)) throw error;
    return { client: null, api: null, problem: error.message };
  }
}

export default function Root({
  env,
  createAuthClient = createFirebaseAuthClient,
}: RootProps) {
  const { client, api, problem } = useMemo(
    () => start(env, createAuthClient),
    [env, createAuthClient],
  );

  if (!client) {
    return (
      <main role="alert" className="mx-auto max-w-xl p-8">
        <h1 className="text-xl font-semibold">ReviewLens cannot start</h1>
        <p className="mt-2">{problem}</p>
      </main>
    );
  }

  return (
    <BrowserRouter>
      <AuthProvider client={client} api={api}>
        <App />
      </AuthProvider>
    </BrowserRouter>
  );
}
