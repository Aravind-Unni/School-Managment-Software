import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

/**
 * Vitest configuration, kept separate from vite.config.ts.
 *
 * Vitest 5 types its own options, so declaring `test` inside a Vite
 * `defineConfig` no longer type-checks. Merging keeps the path aliases in one
 * place rather than duplicating them.
 */
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/unit/**/*.test.ts", "tests/unit/**/*.test.tsx"],
      exclude: ["tests/browser/**", "node_modules/**"],
    },
  }),
);
