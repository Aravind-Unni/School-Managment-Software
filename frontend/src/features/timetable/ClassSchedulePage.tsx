/**
 * The read-only class schedule, for one section on one date.
 *
 * Today first: the date defaults to the school's civil date, because "what is on
 * now" is what a phone is opened for.
 *
 * The section list is derived from the effective revision's own slots. M03
 * cannot offer a proper picker with names: the frozen RegistryPort exposes no
 * way to list or name sections, which is recorded as gap 1 in
 * contracts/M03/ports.md. Ids are shortened rather than pretending to be names.
 */

import { useCallback, useEffect, useState } from "react";
import { listTimetables, readSectionDay, readTimetable, type SectionDay } from "./api";
import { SessionList } from "./SessionList";
import { shortId, todayIso, toErrorState, type LoadState } from "./state";
import { useTimetableMessages } from "./useMessages";

interface ClassValue {
  readonly sections: readonly string[];
  readonly day: SectionDay | null;
}

export function ClassSchedulePage() {
  const t = useTimetableMessages();
  const [date, setDate] = useState(todayIso());
  const [sectionId, setSectionId] = useState<string>("");
  const [state, setState] = useState<LoadState<ClassValue>>({ status: "loading" });

  const load = useCallback(
    async (chosenSection: string, chosenDate: string) => {
      try {
        const page = await listTimetables({ state: "published" });
        const latest = page.items[0];
        const sections =
          latest === undefined
            ? []
            : [
                ...new Set(
                  (await readTimetable(latest.id)).slots.map((slot) => slot.section_id),
                ),
              ].sort();
        const section = chosenSection !== "" ? chosenSection : (sections[0] ?? "");
        if (section === "") {
          setState({ status: "ready", value: { sections, day: null } });
          return;
        }
        const day = await readSectionDay({ sectionId: section, date: chosenDate });
        setSectionId(section);
        setState({ status: "ready", value: { sections, day } });
      } catch (error) {
        setState(toErrorState(error));
      }
    },
    [],
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(sectionId, date);
  }, [load, sectionId, date]);

  if (state.status === "loading") {
    return <p role="status">{t("ui.loading")}</p>;
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
        <button type="button" onClick={() => void load(sectionId, date)}>
          {t("ui.retry")}
        </button>
      </div>
    );
  }

  const { sections, day } = state.value;

  return (
    <section aria-labelledby="timetable-class-heading">
      <h2 id="timetable-class-heading">{t("timetable.schedule.title")}</h2>

      <label>
        {t("timetable.editor.section")}
        <select
          value={sectionId}
          aria-label={t("timetable.editor.section")}
          onChange={(event) => setSectionId(event.target.value)}
        >
          {sections.map((section) => (
            <option key={section} value={section}>
              {shortId(section)}
            </option>
          ))}
        </select>
      </label>

      <label>
        {t("timetable.schedule.date")}
        <input
          type="date"
          value={date}
          aria-label={t("timetable.schedule.date")}
          onChange={(event) => setDate(event.target.value)}
        />
      </label>

      {day === null ? (
        <p role="status">{t("ui.empty")}</p>
      ) : (
        <SessionList
          sessions={day.sessions}
          isSchoolDay={day.is_school_day}
          reasonKey={day.reason_key}
          t={t}
        />
      )}
    </section>
  );
}
