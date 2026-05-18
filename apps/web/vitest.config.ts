import { defineConfig } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
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
      thresholds: {
        statements: 20,
        branches: 50,
        functions: 30,
        lines: 20,
      },
    },
  },
});
