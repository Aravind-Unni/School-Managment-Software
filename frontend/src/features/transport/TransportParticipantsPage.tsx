/** Effective bus participants on a school date. */

import { useCallback, useEffect, useState } from "react";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { listBusParticipants, type ParticipantRowDTO } from "./api";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly items: readonly ParticipantRowDTO[] }
  | { readonly status: "error"; readonly messageKey: string };

function defaultDate(): string {
  return "2026-06-15";
}

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function TransportParticipantsPage() {
  const { t } = useLanguage();
  const [date, setDate] = useState(defaultDate);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async (on: string) => {
    setState({ status: "loading" });
    try {
      const page = await listBusParticipants(on);
      setState({ status: "ready", items: page.items });
    } catch (error) {
      setState({ status: "error", messageKey: toMessageKey(error) });
    }
  }, []);

  useEffect(() => {
    void load(date);
  }, [date, load]);

  return (
    <main>
      <h1>{t("transport.participants_title")}</h1>
      <label>
        {t("transport.pick_date")}
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          aria-label={t("transport.pick_date")}
        />
      </label>
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}
          <button type="button" onClick={() => void load(date)}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && state.items.length === 0 && <p>{t("ui.empty")}</p>}
      {state.status === "ready" && state.items.length > 0 && (
        <table>
          <caption>{t("transport.participants_title")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("transport.col_student")}</th>
              <th scope="col">{t("transport.col_bus")}</th>
              <th scope="col">{t("transport.col_from")}</th>
              <th scope="col">{t("transport.col_to")}</th>
            </tr>
          </thead>
          <tbody>
            {state.items.map((row) => (
              <tr key={row.participation_id}>
                <th scope="row">{row.display_name}</th>
                <td>{row.bus_id ?? "—"}</td>
                <td>{row.from_date}</td>
                <td>{row.to_date ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
