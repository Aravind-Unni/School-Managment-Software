import { describe, expect, it } from "vitest";
import {
  ApiError,
  ERROR_CODES,
  TransportError,
  isErrorEnvelope,
} from "@shared/api/errors";

describe("error envelope", () => {
  const envelope = {
    code: "validation_failed" as const,
    message_key: "error.validation_failed",
    request_id: "req-1",
    field_errors: [
      { field: "body", message_key: "error.required" },
      { field: "body", message_key: "error.too_long" },
      { field: "subject_person_id", message_key: "error.required" },
    ],
  };

  it("exposes the same seven codes as the backend", () => {
    expect([...ERROR_CODES]).toEqual([
      "unauthenticated",
      "stale_auth",
      "action_denied",
      "object_inaccessible",
      "version_conflict",
      "state_conflict",
      "validation_failed",
    ]);
  });

  it("recognises a well-formed envelope", () => {
    expect(isErrorEnvelope(envelope)).toBe(true);
  });

  it.each([
    ["null", null],
    ["a string", "boom"],
    ["an unknown code", { ...envelope, code: "teapot" }],
    ["a missing request_id", { code: "action_denied", message_key: "k", field_errors: [] }],
    ["field_errors not an array", { ...envelope, field_errors: {} }],
    ["an HTML error page", "<html><body>502</body></html>"],
  ])("rejects %s", (_label, value) => {
    expect(isErrorEnvelope(value)).toBe(false);
  });

  it("groups field errors by field for form rendering", () => {
    const error = new ApiError(422, envelope);
    expect(error.fieldErrorsByField()).toEqual({
      body: ["error.required", "error.too_long"],
      subject_person_id: ["error.required"],
    });
  });

  it("flags stale two-factor so the UI can prompt for it", () => {
    const stale = new ApiError(401, {
      code: "stale_auth",
      message_key: "error.two_factor_stale",
      request_id: "req-2",
      field_errors: [],
    });
    expect(stale.needsFreshTwoFactor).toBe(true);
    expect(new ApiError(403, { ...envelope, code: "action_denied" }).needsFreshTwoFactor).toBe(
      false,
    );
  });

  it("keeps transport failures distinct from business errors", () => {
    const transport = new TransportError("offline");
    expect(transport).toBeInstanceOf(TransportError);
    expect(transport).not.toBeInstanceOf(ApiError);
  });
});
