import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ConfigurationError, loadConfig, type AppEnv } from "./config/env";

export default function Root({ env }: { env: AppEnv }) {
  try {
    loadConfig(env);
  } catch (error) {
    if (!(error instanceof ConfigurationError)) throw error;
    return (
      <main role="alert" className="mx-auto max-w-xl p-8">
        <h1 className="text-xl font-semibold">ReviewLens cannot start</h1>
        <p className="mt-2">{error.message}</p>
      </main>
    );
  }

  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}
