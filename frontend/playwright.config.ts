import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for the browser suite.
 *
 * The base URL comes from the environment because `scripts/dev.py up` allocates
 * the frontend port dynamically. There is deliberately no `webServer` block: the
 * stack is started by dev.py, and having Playwright start a second one would
 * mean the browser tests ran against a different database than the API tests.
 */
export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  forbidOnly: !!process.env["CI"],
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "../dev/state/frontend-playwright.json" }],
  ],
  use: {
    baseURL: process.env["SCHOOL_FRONTEND_URL"] ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
