/**
 * Change one's own password. Every other signed-in device is signed out; this
 * one stays signed in.
 *
 * Does not handle: forgotten passwords (the school office resets those from
 * the Accounts page).
 */

import { useState, type FormEvent } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as api from "./api";

export function ChangePasswordForm() {
  const { t } = useLanguage();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [mismatch, setMismatch] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setDone(false);
    setError(null);
    if (next !== repeat) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    setBusy(true);
    try {
      await api.changeOwnPassword({ currentPassword: current, newPassword: next });
      setCurrent("");
      setNext("");
      setRepeat("");
      setDone(true);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)} className="stack" aria-labelledby="pw-title">
      <h3 id="pw-title">{t("access.password.title")}</h3>
      <label>
        {t("access.password.current")}
        <input
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </label>
      <label>
        {t("access.password.new")}
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
      </label>
      <label>
        {t("access.password.repeat")}
        <input
          type="password"
          autoComplete="new-password"
          required
          value={repeat}
          onChange={(e) => setRepeat(e.target.value)}
        />
      </label>
      {mismatch ? <p role="alert">{t("access.password.mismatch")}</p> : null}
      {done ? <p role="status">{t("access.password.changed")}</p> : null}
      <Problem error={error} />
      <button type="submit" disabled={busy}>
        {t("access.password.submit")}
      </button>
    </form>
  );
}
