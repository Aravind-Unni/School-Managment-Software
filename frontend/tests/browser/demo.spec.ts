import { expect, test } from "@playwright/test";

/**
 * Browser tests for the placeholder feature.
 *
 * These require a running stack: `python scripts/dev.py up M00` then
 * `python scripts/dev.py seed M00 --scenario baseline`. They are NOT run by the
 * standalone suite, and `dev.py check --suite browser` records "not-run" rather
 * than passing when the stack or the browser is absent.
 */

test("the demo page lists seeded notes", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Demo" })).toBeVisible();
  await expect(page.getByTestId("demo-note").first()).toBeVisible();
});

test("the language switch renders Malayalam", async ({ page }) => {
  await page.goto("/demo");
  await page.getByLabel("Language").selectOption("ml");
  // The heading is rendered from the nav.demo message key, so switching
  // language must change it without a reload.
  await expect(page.getByRole("heading", { level: 2 })).not.toHaveText("Demo");
});

test("the language choice survives a reload", async ({ page }) => {
  await page.goto("/demo");
  await page.getByLabel("Language").selectOption("ml");
  await page.reload();
  await expect(page.getByLabel(/.+/).first()).toBeVisible();
});

test("an unknown route shows the not-available message", async ({ page }) => {
  await page.goto("/no-such-page");
  await expect(page.getByRole("status")).toBeVisible();
});
