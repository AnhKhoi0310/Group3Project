import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Docker on Windows and macOS doesn't pass file-change events into the
    // container, so docker-compose.yml turns on polling to pick up edits.
    watch:
      process.env.VITE_WATCH_POLLING === "true"
        ? { usePolling: true, interval: 500 }
        : undefined,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    coverage: {
      provider: "v8",
      reporter: ["text", "cobertura"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/test/**",
        "src/**/*.d.ts",
      ],
      reportsDirectory: "./coverage",
    },
  },
});
