import { ConfigurationError, loadConfig } from "./env";

const VALID_ENV = {
  VITE_API_BASE_URL: "http://localhost:8000",
  VITE_FIREBASE_API_KEY: "web-key",
  VITE_FIREBASE_AUTH_DOMAIN: "demo.firebaseapp.com",
  VITE_FIREBASE_PROJECT_ID: "demo",
  VITE_FIREBASE_APP_ID: "app-id",
};

describe("loadConfig", () => {
  it("returns typed configuration for valid input", () => {
    const config = loadConfig(VALID_ENV);

    expect(config.apiBaseUrl).toBe("http://localhost:8000");
    expect(config.firebase.projectId).toBe("demo");
  });

  it.each(Object.keys(VALID_ENV))("names %s when it is missing", (name) => {
    const env = { ...VALID_ENV, [name]: undefined };

    expect(() => loadConfig(env)).toThrow(ConfigurationError);
    expect(() => loadConfig(env)).toThrow(name);
  });

  it("treats blank values as missing", () => {
    expect(() => loadConfig({ ...VALID_ENV, VITE_API_BASE_URL: "  " })).toThrow(
      "VITE_API_BASE_URL",
    );
  });
});
