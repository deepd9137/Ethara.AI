import { defineConfig } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules/**", "dist/**", "e2e/**"],
    alias: {
      "@": resolve(__dirname, "./src"),
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/index.ts",
        "src/main.tsx",
        "src/vite-env.d.ts",
        "src/tests/**",
        "src/app/router.tsx",
        "src/app/providers.tsx",
      ],
      // Initial gate set to current baseline. Ratchet up in follow-up PRs
      // as feature-level component tests land; the point right now is that
      // the gate exists and runs on every PR.
      thresholds: {
        statements: 5,
        branches: 7,
        functions: 5,
        lines: 5,
      },
    },
  },
});
