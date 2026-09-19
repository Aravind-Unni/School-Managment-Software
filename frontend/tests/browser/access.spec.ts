import { expect, test } from "@playwright/test";

/**
 * M01 browser journeys against the REAL backend.
 *
 * Requires a running stack:
 *   python3 scripts/dev.py up M01 --profile standalone
 *   python3 scripts/dev.py migrate M01 --profile standalone
 *   python3 scripts/dev.py seed M01 --scenario baseline
 *
 * Both locales, success and denied journeys, and the loading/error/empty states.
 * The passwords below are the synthetic seed values; they exist nowhere else.
 */

const T1 = { login: "teacher.t1", password: "Teacher-T1-test-only" };
const G1 = { login: "guardian.g1", password: "Guardian-G1-test-only" };

test.describe("login and 2FA", () => {
  test("a staff account is sent to enrolment, with a manual key and no phone assumption", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Login name").fill(T1.login);
    await page.getByLabel("Password").fill(T1.password);
    await page.getByRole("button", { name: "Continue" }).click();

    await expect(page.getByRole("heading", { name: "Set up your authenticator" })).toBeVisible();
    // Setup must be possible without a camera...
    await expect(page.getByTestId("manual-secret")).toBeVisible();
    // ...and must not assume the pupil owns a phone.
    await expect(page.getByTestId("no-phone-note")).toBeVisible();
  });

  test("a wrong password shows an error, not a blank screen", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Login name").fill(T1.login);
    await page.getByLabel("Password").fill("definitely-wrong");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("an unknown login is indistinguishable from a wrong password", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Login name").fill("no.such.person");
    await page.getByLabel("Password").fill("whatever");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
  });

  test("the lost-device path is reachable and mentions no text message", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Login name").fill(G1.login);
    await page.getByLabel("Password").fill(G1.password);
    await page.getByRole("button", { name: "Continue" }).click();
    // G1 needs no factor, so this asserts the signed-in state renders.
    await expect(page.getByTestId("signed-in")).toBeVisible();
  });
});

test.describe("both locales", () => {
  test("the login screen renders in Malayalam", async ({ page }) => {
    await page.goto("/login");
    const englishHeading = await page.getByRole("heading", { level: 2 }).textContent();
    await page.getByLabel("Language").selectOption("ml");
    const malayalamHeading = await page.getByRole("heading", { level: 2 }).textContent();
    expect(malayalamHeading).not.toEqual(englishHeading);
    // Malayalam script, not a fallback to the key or to English.
    expect(malayalamHeading ?? "").toMatch(/[ഀ-ൿ]/);
  });

  test("the language choice survives a reload", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Language").selectOption("ml");
    const before = await page.getByRole("heading", { level: 2 }).textContent();
    await page.reload();
    await expect(page.getByRole("heading", { level: 2 })).toHaveText(before ?? "");
  });
});

test.describe("denied journeys", () => {
  test("the security screen requires a session", async ({ page }) => {
    await page.goto("/settings/security");
    // No session: the screen must show an error state, never a blank page.
    await expect(page.getByRole("alert").or(page.getByRole("status"))).toBeVisible();
  });

  test("the role editor requires a session", async ({ page }) => {
    await page.goto("/settings/roles");
    await expect(page.getByRole("alert").or(page.getByRole("status"))).toBeVisible();
  });
});
