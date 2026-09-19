/** Vitest setup: jest-dom matchers and a clean fetch mock per test. */
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});
