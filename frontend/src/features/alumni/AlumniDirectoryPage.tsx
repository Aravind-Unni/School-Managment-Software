/** Alumni directory search by year and outcome. */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listAlumni, type AlumniProfile, type LeavingOutcome } from "./api";
import { Loading } from "@shared/ui/Loading";

type LoadState =
  | { readonly status: "loading" }
  | {
      readonly status: "ready";
      readonly items: readonly AlumniProfile[];
      readonly nextCursor: string | null;
    }
  | { readonly status: "error"; readonly messageKey: string; readonly requestId: string | null };

export function AlumniDirectoryPage() {
  const { t } = useLanguage();
  const [year, setYear] = useState("");
  const [outcome, setOutcome] = useState<"" | LeavingOutcome>("");
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (cursor?: string, append = false) => {
    if (!append) setState({ status: "loading" });
    try {
      const page = await listAlumni({
        ...(year.length > 0 ? { year: Number(year) } : {}),
        ...(outcome !== "" ? { outcome } : {}),
        ...(cursor !== undefined ? { cursor } : {}),
      });
      setState((previous) => ({
        status: "ready",
        items:
          append && previous.status === "ready"
            ? [...previous.items, ...page.items]
            : page.items,
        nextCursor: page.next_cursor,
      }));
    } catch (error) {
      setState({ status: "error", ...toLoadError(error) });
    }
  }, [year, outcome]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return (
    <section>
      <h1>{t("alumni.directory_title")}</h1>
      <fieldset>
        <legend>{t("alumni.filters")}</legend>
        <label>
          {t("alumni.filter_year")}
          <input
            type="number"
            value={year}
            onChange={(event) => setYear(event.target.value)}
            aria-label={t("alumni.filter_year")}
          />
        </label>
        <label>
          {t("alumni.filter_outcome")}
          <select
            value={outcome}
            onChange={(event) => setOutcome(event.target.value as "" | LeavingOutcome)}
            aria-label={t("alumni.filter_outcome")}
          >
            <option value="">{t("alumni.filter_any")}</option>
            <option value="graduate">{t("alumni.outcome.graduate")}</option>
            <option value="transfer">{t("alumni.outcome.transfer")}</option>
          </select>
        </label>
        <button type="button" onClick={() => void load()}>
          {t("alumni.apply_filters")}
        </button>
      </fieldset>
      {state.status === "loading" && <Loading />}
      {state.status === "error" && (
        <div role="alert">
          <p>{t(state.messageKey)}</p>
          {state.requestId !== null && <code>{state.requestId}</code>}
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
          {state.items.map((profile) => (
            <li key={profile.id}>
              {profile.display_name} · {profile.admission_no} · {profile.leaving_year}{" "}
              <Link to="/alumni/profile" state={{ profile }}>
                {t("alumni.edit_contact")}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {state.status === "ready" && state.nextCursor !== null && (
        <button type="button" onClick={() => void load(state.nextCursor ?? undefined, true)}>
          {t("ui.load_more")}
        </button>
      )}
    </section>
  );
}
