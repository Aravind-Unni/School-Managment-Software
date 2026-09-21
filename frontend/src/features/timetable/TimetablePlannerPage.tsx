/**
 * Timetable planner: who teaches what, and when, for each class, in one place.
 *
 * Left: the class's subjects with their teacher (changing one ends the old
 * teaching assignment yesterday and starts the new one today). Right: the
 * week. Tap a period to choose its subject; the teacher follows from the
 * mapping. Clashes (a teacher already in another class that period) show at
 * once. Changes are a draft until published from a chosen date.
 *
 * Does not handle: rooms, split/elective periods, or substitutions (see
 * Substitutions).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as registry from "@features/registry/api";
import { schoolToday, useSchoolStructure } from "@features/registry/useSchoolStructure";
import * as api from "./api";
import {
  DAY_NAMES,
  DAY_SHORT,
  cellKey,
  clashFor,
  gridFromSlots,
  reassignTeacher,
  slotsFromGrid,
  subjectLoad,
  teacherLoad,
  weekShape,
  type Cell,
  type PeriodRow,
} from "./plannerModel";
import { subjectColour } from "./subjectColours";

interface Base {
  readonly id: string;
  readonly version: number;
  readonly state: string;
  readonly effectiveFrom: string;
  readonly periods: readonly PeriodRow[];
  readonly slots: readonly api.Slot[];
}

interface Picking {
  readonly day: number;
  readonly code: string;
  readonly label: string;
}

const tomorrow = () => {
  const [y, m, d] = schoolToday().split("-").map(Number);
  const next = new Date(Date.UTC(y ?? 2026, (m ?? 1) - 1, (d ?? 1) + 1));
  return next.toISOString().slice(0, 10);
};

const yesterday = () => {
  const [y, m, d] = schoolToday().split("-").map(Number);
  const prev = new Date(Date.UTC(y ?? 2026, (m ?? 1) - 1, (d ?? 1) - 1));
  return prev.toISOString().slice(0, 10);
};

/** Pick the revision to edit: the newest draft, else the one in force today. */
async function loadBase(yearId: string | undefined): Promise<Base | null> {
  const page = await api.listTimetables();
  const rows = page.items.filter((row) => !yearId || row.year_id === yearId);
  const today = schoolToday();
  const draft = rows.find((row) => row.state === "draft");
  const published = rows
    .filter((row) => row.state === "published" && row.effective_from <= today)
    .sort((a, b) => b.effective_from.localeCompare(a.effective_from))[0];
  const chosen = draft ?? published ?? rows[0];
  if (!chosen) return null;
  const full = await api.readTimetable(chosen.id);
  return {
    id: full.id,
    version: full.version,
    state: full.state,
    effectiveFrom: full.effective_from,
    periods: full.periods,
    slots: full.slots,
  };
}

export function TimetablePlannerPage() {
  const { t } = useLanguage();
  const { state: structureState } = useSchoolStructure();
  const [base, setBase] = useState<Base | null>(null);
  const [grid, setGrid] = useState<Map<string, Cell>>(new Map());
  const [staff, setStaff] = useState<readonly registry.StaffMember[]>([]);
  const [assignments, setAssignments] = useState<readonly registry.TeachingAssignment[]>([]);
  const [sectionId, setSectionId] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [picking, setPicking] = useState<Picking | null>(null);
  const [mobileDay, setMobileDay] = useState(1);
  const [effectiveFrom, setEffectiveFrom] = useState(tomorrow());
  const dialog = useRef<HTMLDialogElement>(null);

  const structure = structureState.kind === "ready" ? structureState.structure : null;

  const reload = useCallback(async () => {
    try {
      const [loaded, people, rows] = await Promise.all([
        loadBase(structure?.year?.id),
        registry.listAllStaff(),
        registry.listAllTeachingAssignments(),
      ]);
      setStaff(people.filter((row) => !row.archived));
      setAssignments(rows);
      if (loaded) {
        setBase(loaded);
        setGrid(gridFromSlots(loaded.slots));
        setEffectiveFrom(loaded.state === "draft" && loaded.effectiveFrom > schoolToday()
          ? loaded.effectiveFrom
          : tomorrow());
      }
      setDirty(false);
    } catch (caught) {
      setError(caught);
    }
  }, [structure?.year?.id]);

  // Load once the school structure is known; switching class never reloads,
  // so unsaved edits in other classes are kept.
  useEffect(() => {
    if (structure === null) return;
    void reload();
  }, [structure, reload]);

  // Open on the first class that already has periods, not an empty one.
  const firstSection =
    structure?.sections.find((row) =>
      [...grid.keys()].some((key) => key.startsWith(`${row.id}|`)),
    )?.id ??
    structure?.sections[0]?.id ??
    "";
  useEffect(() => {
    if (sectionId === "" && firstSection !== "" && grid.size > 0) setSectionId(firstSection);
  }, [sectionId, firstSection, grid.size]);

  useEffect(() => {
    if (picking) dialog.current?.showModal();
    else dialog.current?.close();
  }, [picking]);

  const today = schoolToday();
  const active = useMemo(
    () => assignments.filter((row) => row.from_date <= today && (!row.to_date || row.to_date >= today)),
    [assignments, today],
  );
  const staffName = useMemo(() => new Map(staff.map((row) => [row.id, row.display_name])), [staff]);
  const subjectById = useMemo(
    () => new Map((structure?.subjects ?? []).map((row) => [row.id, row])),
    [structure],
  );
  const sectionLabel = useMemo(
    () => new Map((structure?.sections ?? []).map((row) => [row.id, row.label])),
    [structure],
  );

  if (structureState.kind === "loading") return <p role="status">{t("ui.loading")}</p>;
  if (structureState.kind === "failed") return <Problem error={structureState.error} />;
  if (base === null) {
    return (
      <section>
        <h2>{t("planner.title")}</h2>
        <Problem error={error} />
        <p role="status">{t("planner.no_timetable")}</p>
      </section>
    );
  }

  const { days, codes } = weekShape(base.periods);
  const mapping = new Map<string, string>(); // subject -> teacher, for this class
  for (const row of active) {
    if (row.section_id === sectionId) mapping.set(row.subject_id, row.staff_id);
  }
  const load = subjectLoad(grid, sectionId);
  const loadByTeacher = teacherLoad(grid);
  const classSubjects = [...new Set([...mapping.keys(), ...load.keys()])]
    .map((id) => subjectById.get(id))
    .filter((row): row is registry.Subject => row !== undefined)
    .sort((a, b) => a.display_name.localeCompare(b.display_name));
  const unmappedSubjects = (structure?.subjects ?? []).filter(
    (row) => !classSubjects.some((mapped) => mapped.id === row.id),
  );

  const act = async (work: () => Promise<void>, done?: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work();
      if (done) setNotice(done);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const changeTeacher = (subjectId: string, teacherId: string) =>
    act(async () => {
      const current = active.find(
        (row) => row.section_id === sectionId && row.subject_id === subjectId,
      );
      if (current && current.staff_id === teacherId) return;
      if (current) await registry.endTeachingAssignment(current, yesterday());
      if (teacherId) {
        await registry.createTeachingAssignment({
          staffId: teacherId,
          sectionId,
          subjectId,
          fromDate: today,
        });
        setGrid((previous) => reassignTeacher(previous, sectionId, subjectId, teacherId));
        setDirty(true);
      }
      setAssignments(await registry.listAllTeachingAssignments());
    }, t("planner.teacher_saved"));

  const place = (subjectId: string | null) => {
    if (!picking) return;
    const key = cellKey(sectionId, picking.day, picking.code);
    setGrid((previous) => {
      const next = new Map(previous);
      const teacherId = subjectId ? mapping.get(subjectId) : undefined;
      if (subjectId && teacherId) next.set(key, { subjectId, teacherId });
      else next.delete(key);
      return next;
    });
    setDirty(true);
    setPicking(null);
  };

  const periodsPayload = base.periods.map((row) => ({
    day_of_week: row.day_of_week,
    slot_code: row.slot_code,
    starts_at_local: row.starts_at_local,
    ends_at_local: row.ends_at_local,
  }));

  const saveDraft = async (): Promise<Base> => {
    const slots = slotsFromGrid(grid);
    const saved =
      base.state === "draft"
        ? await api.replaceTimetable(base.id, {
            effectiveFrom,
            periods: periodsPayload,
            slots,
            expectedVersion: base.version,
          })
        : await api.createTimetable({
            yearId: structure?.year?.id ?? "",
            effectiveFrom,
            periods: periodsPayload,
            slots,
          });
    const next = {
      id: saved.id,
      version: saved.version,
      state: saved.state,
      effectiveFrom: saved.effective_from,
      periods: saved.periods,
      slots: saved.slots,
    };
    setBase(next);
    setDirty(false);
    return next;
  };

  const clashes = [...grid.entries()].filter(([key, cell]) => {
    const [section, day, code] = key.split("|");
    return clashFor(grid, section ?? "", Number(day), code ?? "", cell.teacherId) !== null;
  }).length;

  const renderCell = (day: number, code: string, time: string) => {
    const cell = grid.get(cellKey(sectionId, day, code));
    const subject = cell ? subjectById.get(cell.subjectId) : undefined;
    const clash = cell ? clashFor(grid, sectionId, day, code, cell.teacherId) : null;
    const label = `${DAY_NAMES[day]}, ${code} (${time})`;
    return (
      <button
        type="button"
        className={`planner-cell${cell ? "" : " empty"}${clash ? " clash" : ""}`}
        style={{ "--subject": subjectColour(subject?.code) } as CSSProperties}
        aria-label={`${label}: ${subject?.display_name ?? t("planner.free")}`}
        onClick={() => setPicking({ day, code, label })}
      >
        {cell ? (
          <>
            <span className="cell-subject">{subject?.display_name ?? "?"}</span>
            <span className="cell-teacher">{staffName.get(cell.teacherId) ?? ""}</span>
            {clash ? (
              <span className="cell-clash">
                {t("planner.clash_with")} {sectionLabel.get(clash) ?? ""}
              </span>
            ) : null}
          </>
        ) : (
          <span className="cell-free">{t("planner.free")}</span>
        )}
      </button>
    );
  };

  return (
    <section className="planner" aria-labelledby="planner-title">
      <div className="planner-head">
        <h2 id="planner-title">{t("planner.title")}</h2>
        <label className="planner-class">
          {t("planner.class")}
          <select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
            {structure?.sections.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="planner-status" role="status">
        {base.state === "draft"
          ? t("planner.editing_draft")
          : `${t("planner.editing_published")} ${base.effectiveFrom}`}
        {dirty ? ` — ${t("planner.unsaved")}` : ""}
        {clashes > 0 ? ` — ${clashes} ${t("planner.clashes")}` : ""}
      </div>
      {notice ? <p role="status" className="notice-success">{notice}</p> : null}
      <Problem error={error} />

      <div className="planner-body">
        <aside className="planner-mapping" aria-labelledby="mapping-title">
          <h3 id="mapping-title">{t("planner.who_teaches")}</h3>
          <ul>
            {classSubjects.map((subject) => (
              <li key={subject.id} style={{ "--subject": subjectColour(subject.code) } as CSSProperties}>
                <span className="subject-chip">{subject.display_name}</span>
                <span className="mapping-load">
                  {load.get(subject.id) ?? 0} {t("planner.per_week")}
                </span>
                <select
                  aria-label={`${t("planner.teacher_for")} ${subject.display_name}`}
                  value={mapping.get(subject.id) ?? ""}
                  disabled={busy}
                  onChange={(event) => void changeTeacher(subject.id, event.target.value)}
                >
                  <option value="">{t("planner.no_teacher")}</option>
                  {staff.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.display_name} ({loadByTeacher.get(row.id) ?? 0})
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
          {unmappedSubjects.length > 0 ? (
            <label>
              {t("planner.add_subject")}
              <select
                value=""
                disabled={busy || staff.length === 0}
                onChange={(event) => {
                  const subjectId = event.target.value;
                  const first = staff[0];
                  if (subjectId && first) void changeTeacher(subjectId, first.id);
                }}
              >
                <option value="">—</option>
                {unmappedSubjects.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.display_name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <p className="hint">{t("planner.teacher_load_hint")}</p>
        </aside>

        <div className="planner-week">
          <div className="planner-days" role="tablist" aria-label={t("planner.day")}>
            {days.map((day) => (
              <button
                key={day}
                type="button"
                role="tab"
                aria-selected={mobileDay === day}
                className={mobileDay === day ? "" : "secondary"}
                onClick={() => setMobileDay(day)}
              >
                {DAY_SHORT[day]}
              </button>
            ))}
          </div>
          <table className="planner-grid">
            <thead>
              <tr>
                <th scope="col">{t("planner.period")}</th>
                {days.map((day) => (
                  <th
                    key={day}
                    scope="col"
                    className={mobileDay === day ? "is-mobile-day" : "not-mobile-day"}
                  >
                    {DAY_SHORT[day]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {codes.map(({ code, start, end }) => (
                <tr key={code}>
                  <th scope="row">
                    {code}
                    <small>
                      {start}–{end}
                    </small>
                  </th>
                  {days.map((day) => (
                    <td
                      key={day}
                      className={mobileDay === day ? "is-mobile-day" : "not-mobile-day"}
                    >
                      {renderCell(day, code, `${start}–${end}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="planner-actions">
        <label>
          {t("planner.takes_effect")}
          <input
            type="date"
            value={effectiveFrom}
            min={tomorrow()}
            onChange={(event) => setEffectiveFrom(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="secondary"
          disabled={busy || !dirty}
          onClick={() => void act(async () => void (await saveDraft()), t("planner.draft_saved"))}
        >
          {t("planner.save_draft")}
        </button>
        <button
          type="button"
          disabled={busy || clashes > 0}
          title={clashes > 0 ? t("planner.fix_clashes") : undefined}
          onClick={() =>
            void act(async () => {
              const saved = dirty || base.state !== "draft" ? await saveDraft() : base;
              await api.publishTimetable(saved.id, saved.version);
              await reload();
            }, t("planner.published"))
          }
        >
          {t("planner.publish")}
        </button>
      </div>

      <dialog ref={dialog} className="planner-picker" onClose={() => setPicking(null)}>
        {picking ? (
          <>
            <h3>{picking.label}</h3>
            <p className="hint">{sectionLabel.get(sectionId)}</p>
            <div className="picker-options">
              {classSubjects.map((subject) => {
                const teacherId = mapping.get(subject.id);
                const clash = teacherId
                  ? clashFor(grid, sectionId, picking.day, picking.code, teacherId)
                  : null;
                return (
                  <button
                    key={subject.id}
                    type="button"
                    className="picker-option"
                    disabled={!teacherId}
                    style={{ "--subject": subjectColour(subject.code) } as CSSProperties}
                    onClick={() => place(subject.id)}
                  >
                    <span className="cell-subject">{subject.display_name}</span>
                    <span className="cell-teacher">
                      {teacherId ? staffName.get(teacherId) : t("planner.no_teacher")}
                    </span>
                    {clash ? (
                      <span className="cell-clash">
                        {t("planner.busy_in")} {sectionLabel.get(clash)}
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
            <div className="row-actions">
              <button type="button" className="secondary" onClick={() => place(null)}>
                {t("planner.make_free")}
              </button>
              <button type="button" className="quiet" onClick={() => setPicking(null)}>
                {t("ui.cancel")}
              </button>
            </div>
          </>
        ) : null}
      </dialog>
    </section>
  );
}

export default TimetablePlannerPage;
