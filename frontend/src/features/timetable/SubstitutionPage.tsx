/**
 * Date-specific substitution: pick a class and a date, then cover one period.
 *
 * The screen states plainly that a substitute's access ends with that school
 * day. It is the one thing a clerk assigning cover in a corridor should know,
 * and a UI that stays silent about it invites the question "so they can see the
 * class from now on?" -- to which the answer is no.
 */

import { useCallback, useEffect, useState } from "react";
import {
  assignSubstitution,
  listSubstitutions,
  listTimetables,
  readSectionDay,
  readTimetable,
  withdrawSubstitution,
  type SectionDay,
  type Substitution,
} from "./api";
import { periodLabel, shortId, todayIso, toErrorState, type LoadState } from "./state";
import { useTimetableMessages } from "./useMessages";

interface SubstitutionValue {
  readonly sections: readonly string[];
  readonly day: SectionDay | null;
  readonly substitutions: readonly Substitution[];
}

export function SubstitutionPage() {
  const t = useTimetableMessages();
  const [date, setDate] = useState(todayIso());
  const [sectionId, setSectionId] = useState("");
  const [slotId, setSlotId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [reason, setReason] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [state, setState] = useState<LoadState<SubstitutionValue>>({ status: "loading" });

  const load = useCallback(async (chosenSection: string, chosenDate: string) => {
    try {
      const page = await listTimetables({ state: "published" });
      const latest = page.items[0];
      const sections =
        latest === undefined
          ? []
          : [
              ...new Set((await readTimetable(latest.id)).slots.map((slot) => slot.section_id)),
            ].sort();
      const section = chosenSection !== "" ? chosenSection : (sections[0] ?? "");
      const substitutions = (await listSubstitutions(chosenDate)).items;
      if (section === "") {
        setState({ status: "ready", value: { sections, day: null, substitutions } });
        return;
      }
      const day = await readSectionDay({ sectionId: section, date: chosenDate });
      setSectionId(section);
      setState({ status: "ready", value: { sections, day, substitutions } });
    } catch (error) {
      setState(toErrorState(error));
    }
  }, []);

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

  const { sections, day, substitutions } = state.value;

  async function assign() {
    try {
      await assignSubstitution({ date, slotId, teacherId, reason });
      setNotice(t("timetable.substitution.assigned"));
      await load(sectionId, date);
    } catch (error) {
      setState(toErrorState(error));
    }
  }

  async function withdraw(substitution: Substitution) {
    try {
      await withdrawSubstitution(substitution.id, substitution.version);
      setNotice(t("timetable.substitution.withdrawn"));
      await load(sectionId, date);
    } catch (error) {
      setState(toErrorState(error));
    }
  }

  return (
    <section aria-labelledby="timetable-substitution-heading">
      <h2 id="timetable-substitution-heading">{t("timetable.substitution.title")}</h2>
      <p>{t("timetable.substitution.expires")}</p>

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

      <label>
        {t("timetable.editor.period")}
        <select
          value={slotId}
          aria-label={t("timetable.editor.period")}
          onChange={(event) => setSlotId(event.target.value)}
        >
          <option value="">{"—"}</option>
          {(day?.sessions ?? []).map((session) => (
            <option key={session.timetable_session_id} value={session.slot_id}>
              {`${session.slot_code} · ${periodLabel(
                session.starts_at_local,
                session.ends_at_local,
              )}`}
            </option>
          ))}
        </select>
      </label>

      <label>
        {t("timetable.substitution.substitute")}
        <input
          type="text"
          value={teacherId}
          aria-label={t("timetable.substitution.substitute")}
          onChange={(event) => setTeacherId(event.target.value.trim())}
        />
      </label>

      <label>
        {t("timetable.substitution.reason")}
        <input
          type="text"
          value={reason}
          aria-label={t("timetable.substitution.reason")}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>

      <button
        type="button"
        onClick={() => void assign()}
        disabled={slotId === "" || teacherId === "" || reason === ""}
      >
        {t("timetable.substitution.assign")}
      </button>

      {notice !== null && <p role="status">{notice}</p>}

      {substitutions.length === 0 ? (
        <p role="status">{t("timetable.substitution.none")}</p>
      ) : (
        <ul>
          {substitutions.map((substitution) => (
            <li key={substitution.id} data-testid="substitution">
              <span>{shortId(substitution.substitute_teacher_id)}</span>
              <span>{substitution.withdrawn ? t("timetable.substitution.withdrawn") : ""}</span>
              <span>{`${t("timetable.substitution.validUntil")}: ${substitution.valid_until}`}</span>
              {!substitution.withdrawn && (
                <button type="button" onClick={() => void withdraw(substitution)}>
                  {t("timetable.substitution.withdraw")}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
