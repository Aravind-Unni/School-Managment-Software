/**
 * The central weekly editor: the grid, the conflicts list and the publish preview.
 *
 * The grid is read from a revision and shown as weekday columns, because that is
 * how a school reads a timetable. Editing a cell is a draft-only action and goes
 * through the whole-week replace, so a save is one transaction that is either
 * taken or refused.
 *
 * Publication is deliberately a two-step: the preview states what will change and
 * what will be kept, because making a schedule live for 4,000 pupils should not
 * be one unlabelled click.
 */

import { useCallback, useEffect, useState } from "react";
import {
  listTimetables,
  publishTimetable,
  readTimetable,
  validateTimetable,
  type Conflict,
  type TimetableSummary,
  type TimetableVersion,
} from "./api";
import { toErrorState, type LoadState } from "./state";
import { useTimetableMessages } from "./useMessages";
import { Loading } from "@shared/ui/Loading";

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
const WEEKDAY_LABELS: Record<number, string> = {
  1: "Mon",
  2: "Tue",
  3: "Wed",
  4: "Thu",
  5: "Fri",
  6: "Sat",
  7: "Sun",
};

interface EditorValue {
  readonly versions: readonly TimetableSummary[];
  readonly selected: TimetableVersion | null;
}

export function WeeklyEditorPage() {
  const t = useTimetableMessages();
  const [state, setState] = useState<LoadState<EditorValue>>({ status: "loading" });
  const [conflicts, setConflicts] = useState<readonly Conflict[] | null>(null);
  const [preview, setPreview] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (timetableId?: string) => {
    try {
      const page = await listTimetables();
      const chosen =
        timetableId ??
        page.items.find((item) => item.state === "draft")?.id ??
        page.items[0]?.id;
      const selected = chosen === undefined ? null : await readTimetable(chosen);
      setState({ status: "ready", value: { versions: page.items, selected } });
    } catch (error) {
      setState(toErrorState(error));
    }
  }, []);

  useEffect(() => {
    // The foundation ships no data-fetching library; loading on mount and setting
    // state is done plainly here and flagged, exactly as the placeholder does.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  if (state.status === "loading") {
    return <Loading />;
  }

  if (state.status === "error") {
    return (
      <div role="alert">
        <p>{t(state.messageKey)}</p>
        {state.requestId !== null && (
          <p className="request-id">
            <code>{state.requestId}</code>
          </p>
        )}
        <button type="button" onClick={() => void load()}>
          {t("ui.retry")}
        </button>
      </div>
    );
  }

  const { versions, selected } = state.value;

  async function check() {
    if (selected === null) return;
    try {
      const report = await validateTimetable(selected.id);
      setConflicts(report.conflicts);
      setNotice(null);
    } catch (error) {
      setState(toErrorState(error));
    }
  }

  async function confirmPublish() {
    if (selected === null) return;
    try {
      const result = await publishTimetable(selected.id, selected.version);
      setPreview(false);
      setNotice(t("timetable.editor.published_ok", { date: result.effective_from }));
      await load(result.id);
    } catch (error) {
      setState(toErrorState(error));
    }
  }

  return (
    <section aria-labelledby="timetable-editor-heading">
      <h2 id="timetable-editor-heading">{t("timetable.editor.title")}</h2>

      <label>
        {t("timetable.editor.versions")}
        <select
          value={selected?.id ?? ""}
          onChange={(event) => void load(event.target.value)}
          aria-label={t("timetable.editor.versions")}
        >
          {versions.map((version) => (
            <option key={version.id} value={version.id}>
              {`${t(`timetable.editor.${version.state}`)} · ${version.effective_from}`}
            </option>
          ))}
        </select>
      </label>

      {selected === null ? (
        <p role="status">{t("ui.empty")}</p>
      ) : (
        <>
          <p className="timetable-effective">
            {`${t("timetable.editor.effectiveFrom")}: ${selected.effective_from} · ` +
              `${t("timetable.editor.effectiveTo")}: ${
                selected.effective_to ?? t("timetable.editor.openEnded")
              }`}
          </p>

          <Grid version={selected} />

          <button type="button" onClick={() => void check()}>
            {t("timetable.editor.checkConflicts")}
          </button>
          {selected.state === "draft" && (
            <button type="button" onClick={() => setPreview(true)}>
              {t("timetable.editor.publish")}
            </button>
          )}

          {conflicts !== null && <ConflictList conflicts={conflicts} />}

          {preview && (
            <div role="dialog" aria-label={t("timetable.editor.publishPreview")}>
              <h3>{t("timetable.editor.publishPreview")}</h3>
              <p>{t("timetable.editor.publishExplains")}</p>
              <p>{`${t("timetable.editor.effectiveFrom")}: ${selected.effective_from}`}</p>
              <button type="button" onClick={() => void confirmPublish()}>
                {t("timetable.editor.publish")}
              </button>
            </div>
          )}

          {notice !== null && <p role="status">{notice}</p>}
        </>
      )}
    </section>
  );
}

/** The week as a table: one column per weekday the school actually teaches. */
function Grid({ version }: { readonly version: TimetableVersion }) {
  const t = useTimetableMessages();
  const weekdays = [...new Set(version.periods.map((period) => period.day_of_week))].sort();
  const codes = [...new Set(version.periods.map((period) => period.slot_code))].sort();

  return (
    <div className="timetable-grid-scroll">
      <table className="timetable-grid">
        <caption className="visually-hidden">{t("timetable.editor.title")}</caption>
        <thead>
          <tr>
            <th scope="col">{t("timetable.editor.period")}</th>
            {weekdays.map((day) => (
              <th key={WEEKDAY_KEYS[day - 1]} scope="col">
                {WEEKDAY_LABELS[day]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {codes.map((code) => (
            <tr key={code}>
              <th scope="row">{code}</th>
              {weekdays.map((day) => {
                const cells = version.slots.filter(
                  (slot) => slot.day_of_week === day && slot.slot_code === code,
                );
                return (
                  <td key={`${code}-${day}`}>
                    {cells.length === 0 ? (
                      <span className="timetable-free">{t("timetable.editor.free")}</span>
                    ) : (
                      cells.map((slot) => (
                        <span key={slot.id} className="timetable-cell">
                          {`${slot.section_id.slice(0, 8)} · ${slot.subject_id.slice(0, 8)}`}
                        </span>
                      ))
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The conflicts list, separating what blocks publication from what merely warns. */
function ConflictList({ conflicts }: { readonly conflicts: readonly Conflict[] }) {
  const t = useTimetableMessages();
  if (conflicts.length === 0) {
    return <p role="status">{t("timetable.editor.noConflicts")}</p>;
  }
  return (
    <section aria-labelledby="timetable-conflicts-heading">
      <h3 id="timetable-conflicts-heading">{t("timetable.editor.conflicts")}</h3>
      <ul>
        {conflicts.map((conflict, index) => (
          <li key={`${conflict.code}-${index}`} data-testid="conflict">
            <strong>
              {conflict.blocking
                ? t("timetable.editor.blocking")
                : t("timetable.editor.advisory")}
            </strong>
            <span>{t(conflict.message_key)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
