import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "@shared/i18n/LanguageContext";
import { LoginPage } from "@features/access/LoginPage";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response;
}

function renderLogin() {
  return render(
    <MemoryRouter>
      <LanguageProvider>
        <LoginPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}

async function submitPassword() {
  await userEvent.type(screen.getByLabelText("Login name"), "teacher.t1");
  await userEvent.type(screen.getByLabelText("Password"), "pw");
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
}

describe("M01 login flow", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("asks for a code when the account already has a factor", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        { challenge_id: "c1", expires_at: "2026-07-15T05:00:00Z", next_action: "totp_required" },
        201,
      ),
    );
    renderLogin();
    await submitPassword();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Enter your 6-digit code" })).toBeInTheDocument(),
    );
  });

  it("shows the manual key and the no-phone note on first enrolment", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(
          {
            challenge_id: "c1",
            expires_at: "2026-07-15T05:00:00Z",
            next_action: "enrol_factor_required",
          },
          201,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            factor_id: "f1",
            secret_base32: "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
            otpauth_uri: "otpauth://totp/x",
            digits: 6,
            period_seconds: 30,
            issuer: "School Platform",
            account_name: "teacher.t1",
          },
          201,
        ),
      );
    renderLogin();
    await submitPassword();
    // The manual key is the accessible path: setup must not require a camera.
    await waitFor(() =>
      expect(screen.getByTestId("manual-secret")).toHaveTextContent(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
      ),
    );
    // Setup copy must not assume a student owns a phone.
    expect(screen.getByTestId("no-phone-note")).toBeInTheDocument();
  });

  it("renders a denial through its message key with the request id", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          code: "unauthenticated",
          message_key: "error.challenge_invalid",
          request_id: "req-9",
          field_errors: [],
        },
        401,
      ),
    );
    renderLogin();
    await submitPassword();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByTestId("request-id")).toHaveTextContent("req-9");
  });

  it("reports a throttled login without claiming a business reason", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          code: "rate_limited",
          message_key: "error.too_many_attempts",
          request_id: "req-10",
          field_errors: [],
        },
        429,
      ),
    );
    renderLogin();
    await submitPassword();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("shows the recovery codes once, with the warning that nobody can re-show them", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(
          {
            challenge_id: "c1",
            expires_at: "2026-07-15T05:00:00Z",
            next_action: "enrol_factor_required",
          },
          201,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            factor_id: "f1",
            secret_base32: "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
            otpauth_uri: "otpauth://totp/x",
            digits: 6,
            period_seconds: 30,
            issuer: "School Platform",
            account_name: "teacher.t1",
          },
          201,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          {
            codes: Array.from({ length: 10 }, (_unused, index) => `AAAAA-0000${index}`),
            generated_at: "2026-07-15T04:30:00Z",
            count: 10,
          },
          201,
        ),
      );
    renderLogin();
    await submitPassword();
    await waitFor(() => expect(screen.getByTestId("manual-secret")).toBeInTheDocument());
    await userEvent.type(screen.getByLabelText("Now enter the code your app shows"), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Activate" }));
    await waitFor(() =>
      expect(screen.getByTestId("recovery-codes").children).toHaveLength(10),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/nobody can show them to you later/i);
  });
});
