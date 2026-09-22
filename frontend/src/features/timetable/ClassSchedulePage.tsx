/**
 * One class's week: the days across, the periods down, each lesson with its
 * subject and the teacher taking it (a cover teacher when one is arranged).
 *
 * This is the wall chart the office and the class teacher read. Tests and
 * exams set for the class that week appear under the day.
 * Does not handle: editing (see the planner) or arranging cover (see
 * Substitutions).
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Loading } from "@shared/ui/Loading";
import { Problem } from "@shared/ui/Problem";
import { useLabels } from "@features/registry/useLabels";
import { listTimetables, readSectionDay, readTimetable, type SectionDay } from "./api";
import { todayIso } from "./state";
import { useTimetableMessages } from "./useMessages";
import { WeekGrid, addDays, weekStart, type WeekDay } from "./WeekGrid";

interface ScheduledItem {
  readonly assessment_id: string;
  readonly date: string;
  readonly type: string;
  readonly subject_name: string | null;
  readonly section_id: string;
}

export function ClassSchedulePage() {
  const t = useTimetableMessages();
  const { t: tr, language } = useLanguage();
  const labels = useLabels();
  // The classes come from the published timetable itself, so this page works
  // for anyone who may read a schedule, with or without registry access.
  const [sections, setSections] = useState<readonly string[]>([]);
  const [sectionId, setSectionId] = useState("");
  const [monday, setMonday] = useState(() => weekStart(todayIso()));
  const [days, setDays] = useState<readonly WeekDay[] | null>(null);
  const [scheduled, setScheduled] = useState<readonly ScheduledItem[]>([]);
  const [error, setError] = useState<unknown>(null);

  const chosen = sectionId || sections[0] || "";
  const dates = Array.from({ length: 6 }, (_, index) => addDays(monday, index));

  const load = useCallback(async () => {
    if (chosen === "") return;
    setDays(null);
    setError(null);
    try {
      const [loaded, tests] = await Promise.all([
        Promise.all(dates.map((date) => readSectionDay({ sectionId: chosen, date }))),
        request<{ items: ScheduledItem[] }>("/api/v1/assessment-calendar", {
          query: { from: dates[0], to: dates[dates.length - 1], section_id: chosen },
        }).catch(() => ({ items: [] as ScheduledItem[] })),
      ]);
      setDays(
        loaded.map((day: SectionDay) => ({
          date: day.date,
          is_school_day: day.is_school_day,
          reason_key: day.reason_key,
          sessions: day.sessions.map((session) => ({ session })),
        })),
      );
      setScheduled(tests.items ?? []);
    } catch (caught) {
      setError(caught);
      setDays([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload per class and week
  }, [chosen, monday]);

  useEffect(() => {
    listTimetables({ state: "published" }).then(
      async (page) => {
        const latest = page.items[0];
        if (!latest) return;
        const slots = (await readTimetable(latest.id)).slots;
        setSections([...new Set(slots.map((slot) => slot.section_id))].sort());
      },
      () => setSections([]),
    );
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const today = todayIso();
  const dayName = (date: string) =>
    new Date(`${date}T00:00:00`).toLocaleDateString(language === "ml" ? "ml-IN" : "en-IN", {
      weekday: "short",
      day: "numeric",
    });

  return (
    <section aria-labelledby="class-week-title">
      <h2 id="class-week-title">{t("timetable.schedule.title")}</h2>
      <div className="toolbar">
        <label>
          {t("timetable.editor.section")}
          <select value={chosen} onChange={(event) => setSectionId(event.target.value)}>
            {sections.map((section) => (
              <option key={section} value={section}>
                {labels.section(section)}
              </option>
            ))}
          </select>
        </label>
        <div className="month-nav">
          <button type="button" className="secondary" onClick={() => setMonday(addDays(monday, -7))}>
            ←
          </button>
          <strong>
            {dayName(dates[0] ?? monday)} – {dayName(dates[5] ?? monday)}
          </strong>
          <button type="button" className="secondary" onClick={() => setMonday(addDays(monday, 7))}>
            →
          </button>
        </div>
        <button type="button" className="quiet" onClick={() => setMonday(weekStart(today))}>
          {t("timetable.schedule.thisWeek")}
        </button>
      </div>
      <Problem error={error} />
      {days === null ? (
        <Loading />
      ) : (
        <WeekGrid
          dates={dates}
          days={days}
          today={today}
          events={(date) =>
            scheduled
              .filter((row) => row.date === date)
              .map((row) => ({
                key: row.assessment_id,
                label: `${row.subject_name ?? ""} ${tr(`assessments.type.${row.type}`)}`,
                strong: row.type === "exam",
              }))
          }
        />
      )}
    </section>
  );
}
