import { describe, expect, it } from "vitest";
import { LANGUAGES, SHARED_MESSAGES, missingKeys, translate } from "@shared/i18n/messages";

describe("i18n", () => {
  it("supports exactly English and Malayalam", () => {
    expect([...LANGUAGES]).toEqual(["en", "ml"]);
  });

  it("translates a known key in both languages", () => {
    expect(translate("en", "error.action_denied")).toBe("You do not have permission to do this.");
    expect(translate("ml", "error.action_denied")).not.toBe("error.action_denied");
  });

  it("returns the key itself for an unknown key, so gaps are visible", () => {
    expect(translate("en", "error.not_a_real_key")).toBe("error.not_a_real_key");
  });

  it("has no untranslated keys in Malayalam", () => {
    expect(missingKeys("ml")).toEqual([]);
  });

  it("covers every error code the backend can return", () => {
    const required = [
      "error.unauthenticated",
      "error.action_denied",
      "error.object_inaccessible",
      "error.version_conflict",
      "error.state_conflict",
      "error.validation_failed",
      "error.two_factor_stale",
    ];
    for (const key of required) {
      expect(Object.keys(SHARED_MESSAGES.en)).toContain(key);
      expect(Object.keys(SHARED_MESSAGES.ml)).toContain(key);
    }
  });
});
