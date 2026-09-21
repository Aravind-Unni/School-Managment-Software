import { defineConfig, devices } from "@playwright/test";

/** Which spec file belongs to which standalone module stack. */
const SPEC_BY_MODULE: Record<string, string> = {
  M00: "**/demo.spec.ts",
  M01: "**/access.spec.ts",
  M03: "**/timetable.spec.ts",
  M04: "**/attendance.spec.ts",
  // Integrated profile: real M01 sessions, not the fixed persona the module
  // specs assume. Keep a dedicated smoke file so ALL does not collect them.
  ALL: "**/integrated-smoke.spec.ts",
};

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
  // A standalone stack mounts ONE module's routes, so collecting every spec
  // would fail against paths that stack does not serve. MODULE_ID selects the
  // matching spec; with no selection the default full collection is kept, which
  // is what an integrated run wants. Generalised from the M01 special case as
  // M03 landed -- adding a third `if` would have been the wrong shape.
  ...(SPEC_BY_MODULE[process.env["MODULE_ID"] ?? ""] !== undefined
    ? { testMatch: SPEC_BY_MODULE[process.env["MODULE_ID"] ?? ""] }
    : {}),
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
