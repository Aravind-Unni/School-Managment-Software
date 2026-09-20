import { expect, test } from "@playwright/test";

/**
 * Browser tests for M04 attendance against the real standalone stack.
 *
 * Requires:
 *   python3 scripts/dev.py up M04 --profile standalone
 *   python3 scripts/dev.py migrate M04 --profile standalone
 *   python3 scripts/dev.py seed M04 --scenario baseline
 */

const SCHOOL_DAY = "2026-07-15";

test("today's periods list loads for the teacher", async ({ page }) => {
  await page.goto("/attendance");
  await page.getByLabel(/Date|തീയതി/).fill(SCHOOL_DAY);
  await expect(page.getByTestId("open-P1")).toBeVisible();
});

test("open P1, mark all present, save and submit", async ({ page }) => {
  await page.goto("/attendance");
  await page.getByLabel(/Date|തീയതി/).fill(SCHOOL_DAY);
  await page.getByTestId("open-P1").click();
  await expect(page.getByTestId("session-state")).toBeVisible();
  await page.getByRole("button", { name: /Mark all present|എല്ലാവരെയും/ }).click();
  await page.getByRole("button", { name: /Save|സേവ്/ }).click();
  await page.getByRole("button", { name: /Submit|സമർപ്പിക്കുക/ }).click();
  await expect(page.getByTestId("submit-complete")).toBeVisible();
});

test("Malayalam title renders", async ({ page }) => {
  await page.goto("/attendance");
  await page.getByLabel("Language").selectOption("ml");
  await expect(page.getByRole("heading", { name: "ഇന്നത്തെ പീരീഡുകൾ" })).toBeVisible();
});
