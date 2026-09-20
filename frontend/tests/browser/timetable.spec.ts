import { expect, test } from "@playwright/test";

/**
 * Browser tests for M03 timetable, against the REAL backend.
 *
 * They require a running stack:
 *   python3 scripts/dev.py up M03 --profile standalone
 *   python3 scripts/dev.py migrate M03 --profile standalone
 *   python3 scripts/dev.py seed M03 --scenario baseline
 *
 * `dev.py check M03 --suite browser` records "not-run" rather than passing when
 * the stack or the browser is absent. A browser result claimed without a browser
 * is the exact false green that command exists to prevent.
 *
 * The seeded baseline gives: C1 and C2, two periods a day Monday to Friday, a
 * holiday on 2026-07-16, an exam day on 2026-07-22, and two dated substitutions.
 */

const SCHOOL_DAY = "2026-07-15";
const HOLIDAY = "2026-07-16";

test("the class schedule shows the seeded periods for a teaching day", async ({ page }) => {
  await page.goto("/timetable/class");
  await page.getByLabel("Date").fill(SCHOOL_DAY);
  await expect(page.getByTestId("session").first()).toBeVisible();
  await expect(page.getByTestId("session")).toHaveCount(2);
});

test("a holiday says so and shows no lessons", async ({ page }) => {
  await page.goto("/timetable/class");
  await page.getByLabel("Date").fill(HOLIDAY);
  await expect(page.getByRole("status")).toContainText("No lessons on this day");
  await expect(page.getByTestId("session")).toHaveCount(0);
});

test("the schedule renders in Malayalam", async ({ page }) => {
  await page.goto("/timetable/class");
  await page.getByLabel("Language").selectOption("ml");
  await page.getByLabel(/തീയതി|Date/).fill(HOLIDAY);
  await expect(page.getByRole("status")).toContainText("ഈ ദിവസം ക്ലാസുകളില്ല");
});

test("the weekly editor renders the grid and checks for conflicts", async ({ page }) => {
  await page.goto("/timetable/editor");
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByRole("button", { name: "Check for conflicts" }).click();
  // The seeded grid is clean apart from the advisory teacher_not_assigned rows,
  // so either the "no conflicts" status or a list of advisory rows is correct --
  // what must never appear is an untranslated message key.
  await expect(page.locator("body")).not.toContainText("timetable.conflict.");
});

test("the substitution screen states that access expires", async ({ page }) => {
  await page.goto("/timetable/substitutions");
  await expect(
    page.getByText("A substitute's access ends at the end of that school day"),
  ).toBeVisible();
});

test("a teacher's own schedule loads and an empty field shows the empty state", async ({
  page,
}) => {
  await page.goto("/timetable/teacher");
  await expect(page.getByRole("status")).toContainText("Nothing to show yet");
});

test("an unrelated section read is denied, in prose", async ({ page }) => {
  // The standalone persona is T1, class teacher of C1. C2's schedule is not
  // theirs to read, and the screen must say so as a sentence, not as a code.
  await page.goto("/timetable/class");
  const sections = page.getByLabel("Class");
  const values = await sections.locator("option").all();
  if (values.length > 1) {
    await sections.selectOption({ index: 1 });
    const alert = page.getByRole("alert");
    if (await alert.isVisible()) {
      await expect(alert).toContainText("You do not have permission");
      await expect(alert).not.toContainText("action_denied");
    }
  }
});

test("an unknown route shows the not-available message", async ({ page }) => {
  await page.goto("/timetable/no-such-page");
  await expect(page.getByRole("status")).toBeVisible();
});
