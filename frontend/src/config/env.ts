export type AppEnv = Record<string, string | undefined>;

export interface AppConfig {
  apiBaseUrl: string;
  firebase: {
    apiKey: string;
    authDomain: string;
    projectId: string;
    appId: string;
  };
}

export class ConfigurationError extends Error {}

const REQUIRED = [
  "VITE_API_BASE_URL",
  "VITE_FIREBASE_API_KEY",
  "VITE_FIREBASE_AUTH_DOMAIN",
  "VITE_FIREBASE_PROJECT_ID",
  "VITE_FIREBASE_APP_ID",
];

export function loadConfig(env: AppEnv): AppConfig {
  const missing = REQUIRED.filter((name) => !env[name]?.trim());
  if (missing.length > 0) {
    throw new ConfigurationError(
      `Missing configuration: ${missing.join(", ")}. ` +
        "Set these in frontend/.env (see frontend/.env.example) and restart.",
    );
  }

  return {
    apiBaseUrl: env.VITE_API_BASE_URL!,
    firebase: {
      apiKey: env.VITE_FIREBASE_API_KEY!,
      authDomain: env.VITE_FIREBASE_AUTH_DOMAIN!,
      projectId: env.VITE_FIREBASE_PROJECT_ID!,
      appId: env.VITE_FIREBASE_APP_ID!,
    },
  };
}
