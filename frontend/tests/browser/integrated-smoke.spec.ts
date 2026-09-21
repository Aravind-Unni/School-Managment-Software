import { expect, test } from "@playwright/test";

/**
 * Integrated-profile smoke (MODULE_ID=ALL).
 *
 * Standalone module specs assume a fixed persona. The integrated stack uses real
 * M01 sessions, so those specs are not selected here. These journeys cover the
 * product shell: login, CSRF session, home after guardian sign-in, and the
 * unauthenticated redirect.
 */

const G1 = { login: "guardian.g1", password: "Guardian-G1-test-only" };

test("login screen is reachable", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByLabel("Login name")).toBeVisible();
});

test("wrong password shows an error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Login name").fill(G1.login);
  await page.getByLabel("Password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
});

test("unauthenticated routes redirect to login with a status", async ({ page }) => {
  await page.goto("/settings/roles");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("status")).toBeVisible();
});

test("guardian password login reaches home", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Login name").fill(G1.login);
  await page.getByLabel("Password").fill(G1.password);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByTestId("signed-in")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
});

test("home shows fee statement when guardian holds fees.read", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Login name").fill(G1.login);
  await page.getByLabel("Password").fill(G1.password);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByTestId("signed-in")).toBeVisible();
  // Nav is permission-filtered; guardian grant includes fees.read.
  await expect(page.getByRole("navigation")).toContainText(/fee|statement|Fee/i);
});
