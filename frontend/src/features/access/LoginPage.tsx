/**
 * Login and the 2FA challenge, as one flow.
 *
 * Kept in one component because the steps share state that must never be persisted:
 * the challenge id, and the password needed for a first enrolment. Putting them in a
 * store or the URL would leave credential material somewhere it can be read.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "./api";
import { Failure } from "./Feedback";
import { useAccessMessages } from "./useMessages";
import { toMessage } from "./Feedback";
import { useSession } from "@app/SessionContext";
import { TotpQrCode } from "./TotpQrCode";

type Step =
  | { readonly kind: "password" }
  | { readonly kind: "totp"; readonly challengeId: string }
  | { readonly kind: "enrol"; readonly challengeId: string; readonly start: api.EnrolStart }
  | { readonly kind: "codes"; readonly codes: readonly string[] }
  | { readonly kind: "recovery"; readonly challengeId: string }
  | { readonly kind: "lostDevice" }
  | { readonly kind: "done"; readonly authLevel: string };

export function LoginPage() {
  const t = useAccessMessages();
  const navigate = useNavigate();
  const { refresh } = useSession();
  const [step, setStep] = useState<Step>({ kind: "password" });
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<{ messageKey: string; requestId: string | null } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  async function guard(action: () => Promise<void>) {
    setBusy(true);
    setProblem(null);
    try {
      await action();
    } catch (error) {
      setProblem(toMessage(error));
    } finally {
      setBusy(false);
    }
  }

  const finishSignedIn = async (authLevel: string) => {
    setStep({ kind: "done", authLevel });
    await refresh();
    void navigate("/", { replace: true });
  };

  const submitPassword = () =>
    guard(async () => {
      const challenge = await api.login({ loginName, password });
      if (challenge.next_action === "totp_required") {
        setStep({ kind: "totp", challengeId: challenge.challenge_id });
      } else if (challenge.next_action === "enrol_factor_required") {
        const start = await api.startEnrolment({
          password,
          challengeId: challenge.challenge_id,
        });
        setStep({ kind: "enrol", challengeId: challenge.challenge_id, start });
      } else {
        await finishSignedIn("password");
      }
    });

  const submitCode = (challengeId: string) =>
    guard(async () => {
      const result = await api.verifyTotp({ challengeId, code });
      await finishSignedIn(result.auth_level);
    });

  const submitEnrolment = (challengeId: string, factorId: string) =>
    guard(async () => {
      const result = await api.confirmEnrolment({ factorId, code, password, challengeId });
      setStep({ kind: "codes", codes: result.codes });
    });

  const submitRecovery = (challengeId: string) =>
    guard(async () => {
      const result = await api.recover({ challengeId, recoveryCode });
      await finishSignedIn(result.auth_level);
    });

  const submitLostDevice = () =>
    guard(async () => {
      await api.requestFactorReset(reason);
      setStep({ kind: "lostDevice" });
    });

  return (
    <section aria-labelledby="access-login-heading">
      <h2 id="access-login-heading">
        {step.kind === "password"
          ? t("access.login.title")
          : step.kind === "enrol"
            ? t("access.enrol.title")
            : step.kind === "codes"
              ? t("access.recovery.title")
              : step.kind === "recovery"
                ? t("access.challenge.useRecovery")
                : step.kind === "lostDevice"
                  ? t("access.lostDevice.title")
                  : step.kind === "done"
                    ? t("access.login.title")
                    : t("access.challenge.title")}
      </h2>

      {problem ? <Failure messageKey={problem.messageKey} requestId={problem.requestId} /> : null}

      {step.kind === "password" ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submitPassword();
          }}
        >
          <p role="status">{t("access.login.helper")}</p>
          <label htmlFor="login-name">{t("access.login.name")}</label>
          <input
            id="login-name"
            name="login_name"
            autoComplete="username"
            value={loginName}
            onChange={(event) => setLoginName(event.target.value)}
            required
          />
          <label htmlFor="login-password">{t("access.login.password")}</label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <button type="submit" disabled={busy}>
            {t("access.login.submit")}
          </button>
        </form>
      ) : null}

      {step.kind === "totp" ? (
        <>
          <p>{t("access.challenge.helper")}</p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submitCode(step.challengeId);
            }}
          >
            <label htmlFor="totp-code">{t("access.challenge.code")}</label>
            <input
              id="totp-code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              required
            />
            <button type="submit" disabled={busy}>
              {t("access.challenge.submit")}
            </button>
          </form>
          <button
            type="button"
            onClick={() => setStep({ kind: "recovery", challengeId: step.challengeId })}
          >
            {t("access.challenge.useRecovery")}
          </button>
          <button type="button" onClick={() => setStep({ kind: "lostDevice" })}>
            {t("access.challenge.lostDevice")}
          </button>
        </>
      ) : null}

      {step.kind === "enrol" ? (
        <>
          <p>{t("access.enrol.intro")}</p>
          <p data-testid="no-phone-note">{t("access.enrol.noPhoneNote")}</p>
          <h3>{t("access.enrol.scanQr")}</h3>
          <p>{t("access.enrol.scanQrHelp")}</p>
          <TotpQrCode
            otpauthUri={step.start.otpauth_uri}
            label={t("access.enrol.scanQr")}
          />
          <h3>{t("access.enrol.manualSecret")}</h3>
          <p>{t("access.enrol.manualSecretHelp")}</p>
          {/* Grouped for reading; clipboard copies the continuous base32 string. */}
          <output data-testid="manual-secret" style={{ fontFamily: "monospace" }}>
            {step.start.secret_base32.replace(/(.{4})/g, "$1 ").trim()}
          </output>
          <p>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                void navigator.clipboard.writeText(step.start.secret_base32);
              }}
            >
              {t("access.enrol.copySecret")}
            </button>
          </p>
          <p role="status">
            {t("access.enrol.totpProfile")
              .replace("{digits}", String(step.start.digits))
              .replace("{period}", String(step.start.period_seconds))}
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submitEnrolment(step.challengeId, step.start.factor_id);
            }}
          >
            <label htmlFor="enrol-code">{t("access.enrol.confirmCode")}</label>
            <input
              id="enrol-code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              value={code}
              onChange={(event) =>
                setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              required
            />
            <button type="submit" disabled={busy}>
              {t("access.enrol.confirm")}
            </button>
          </form>
        </>
      ) : null}

      {step.kind === "codes" ? (
        <RecoveryCodes
          codes={step.codes}
          onDone={() => void guard(() => finishSignedIn("password_totp"))}
        />
      ) : null}

      {step.kind === "recovery" ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submitRecovery(step.challengeId);
          }}
        >
          <label htmlFor="recovery-code">{t("access.challenge.recoveryCode")}</label>
          <input
            id="recovery-code"
            name="recovery_code"
            value={recoveryCode}
            onChange={(event) => setRecoveryCode(event.target.value)}
            required
          />
          <button type="submit" disabled={busy}>
            {t("access.challenge.submit")}
          </button>
        </form>
      ) : null}

      {step.kind === "lostDevice" ? (
        <>
          <p>{t("access.lostDevice.intro")}</p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submitLostDevice();
            }}
          >
            <label htmlFor="lost-reason">{t("access.lostDevice.reason")}</label>
            <textarea
              id="lost-reason"
              name="reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
            />
            <button type="submit" disabled={busy}>
              {t("access.lostDevice.submit")}
            </button>
          </form>
        </>
      ) : null}

      {step.kind === "done" ? (
        <p role="status" data-testid="signed-in">
          {step.authLevel}
        </p>
      ) : null}
    </section>
  );
}

/** One-time recovery codes, with a download that does not touch the network. */
function RecoveryCodes({
  codes,
  onDone,
}: {
  readonly codes: readonly string[];
  readonly onDone: () => void;
}) {
  const t = useAccessMessages();
  const download = () => {
    // Built in the browser from values already in memory: the codes are never sent
    // anywhere, and there is no endpoint that could return them again.
    const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "school-recovery-codes.txt";
    anchor.click();
    URL.revokeObjectURL(url);
  };
  return (
    <>
      <p>{t("access.recovery.intro")}</p>
      <p role="alert">{t("access.recovery.warning")}</p>
      <ul data-testid="recovery-codes">
        {codes.map((value) => (
          <li key={value}>
            <code>{value}</code>
          </li>
        ))}
      </ul>
      <div className="row-actions">
        <button type="button" className="secondary" onClick={download}>
          {t("access.recovery.download")}
        </button>
        <button type="button" onClick={onDone}>
          {t("access.recovery.done")}
        </button>
      </div>
    </>
  );
}

export default LoginPage;
