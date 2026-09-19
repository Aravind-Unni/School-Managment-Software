/**
 * ESLint configuration for the frontend.
 *
 * Type-aware rules are enabled for .ts/.tsx only: most mistakes worth catching
 * in a TypeScript React app (a floating promise, an unsafe any) are invisible to
 * a syntax-only linter. They are scoped by `files` because this config file
 * itself is plain JavaScript and is not part of the TypeScript project -- an
 * unscoped type-checked preset tries to lint it and fails.
 */

import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "src/features/*/generated/**", "node_modules"] },

  // Plain JS (this config file): syntax rules only, no type information.
  {
    files: ["**/*.js"],
    ...js.configs.recommended,
    languageOptions: { globals: { ...globals.node } },
  },

  // TypeScript sources: type-aware linting.
  ...tseslint.configs.recommendedTypeChecked.map((configuration) => ({
    ...configuration,
    files: ["**/*.{ts,tsx}"],
  })),
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // A dropped promise in a handler silently swallows an API failure.
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },

  // Tests mock fetch and poke at internals; the strictest any-rules get in the
  // way there without catching real defects.
  {
    files: ["tests/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-unsafe-assignment": "off",
      "@typescript-eslint/no-unsafe-member-access": "off",
      "@typescript-eslint/no-unsafe-argument": "off",
      "@typescript-eslint/no-unsafe-call": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
);
