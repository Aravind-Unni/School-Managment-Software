/** Pending graduate/leaver candidate review. */

import { useCallback, useEffect, useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  approveCandidate,
  listCandidates,
  type AlumniCandidate,
  type CandidateState,
} from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly items: readonly AlumniCandidate[] }
  | { readonly status: "error"; readonly messageKey: string };

export function AlumniCandidatesPage() {
  const { t } = useLanguage();
  const [filter, setFilter] = useState<CandidateState | "">("pending");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    setNotice(null);
    try {
      const page = await listCandidates(
        filter !== "" ? { state: filter } : {},
      );
      setState({ status: "ready", items: page.items });
    } catch (error) {
      setState({ status: "error", messageKey: toLoadError(error).messageKey });
    }
  }, [filter]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function act(candidate: AlumniCandidate, include: boolean) {
    setBusyId(candidate.id);
    setNotice(null);
    try {
      await approveCandidate(candidate.id, {
        include,
        reason: include ? t("alumni.approve_reason") : t("alumni.exclude_reason"),
      });
      setNotice(include ? t("alumni.approved_ok") : t("alumni.excluded_ok"));
      await load();
    } catch (error) {
      setNotice(toLoadError(error).messageKey);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main>
      <h1>{t("alumni.candidates_title")}</h1>
      <label>
        {t("alumni.filter_state")}
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value as CandidateState | "")}
        >
          <option value="pending">{t("alumni.state.pending")}</option>
          <option value="approved">{t("alumni.state.approved")}</option>
          <option value="excluded">{t("alumni.state.excluded")}</option>
          <option value="">{t("alumni.filter_any")}</option>
        </select>
      </label>
      {notice !== null && (
        <p role="status">{notice.startsWith("alumni.") || notice.startsWith("error.") ? t(notice) : notice}</p>
      )}
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <div role="alert">
          <p>{t(state.messageKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {state.status === "ready" && state.items.length === 0 && (
        <p role="status">{t("ui.empty")}</p>
      )}
      {state.status === "ready" && state.items.length > 0 && (
        <ul>
          {state.items.map((candidate) => (
            <li key={candidate.id}>
              {candidate.display_name} · {candidate.admission_no} · {candidate.leaving_year} ·{" "}
              {t(`alumni.outcome.${candidate.outcome}`)} · {t(`alumni.state.${candidate.state}`)}
              {candidate.state === "pending" && (
                <>
                  {" "}
                  <button
                    type="button"
                    disabled={busyId === candidate.id}
                    onClick={() => void act(candidate, true)}
                  >
                    {t("alumni.include")}
                  </button>{" "}
                  <button
                    type="button"
                    disabled={busyId === candidate.id}
                    onClick={() => void act(candidate, false)}
                  >
                    {t("alumni.exclude")}
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
