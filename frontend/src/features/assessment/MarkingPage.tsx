/**
 * Enter and review one assessment's marks.
 *
 * Each score saves when you leave the box (or press Enter), with a tick when
 * the server has it; "Absent" records an absence rather than a zero. The
 * teacher submits when every pupil has a mark; the principal approves and
 * publishes, after which parents see the marks.
 *
 * Does not handle: per-question components (one total per pupil) or scanned
 * answer sheets (see "Attach answer sheets").
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import { can, useSession } from "@app/SessionContext";
import { approveAssessment, patchResult, publishAssessment, submitAssessment } from "./api";
import { Loading } from "@shared/ui/Loading";

interface ResultRow {
  readonly student_id: string;
  readonly display_name: string;
  readonly attempt_id: string;
  readonly score: string | null;
  readonly marking_outcome: string | null;
}

interface Detail {
  readonly id: string;
  readonly version: number;
  readonly state: string;
  readonly type: string;
  readonly max_score: string;
  readonly section_label: string | null;
  readonly subject_name: string | null;
  readonly components: readonly { readonly id: string }[];
  readonly results: readonly ResultRow[];
}

type RowState = { score: string; absent: boolean; saved: boolean; saving: boolean; error: boolean };

export function MarkingPage() {
  const { t } = useLanguage();
  const { actions } = useSession();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [rows, setRows] = useState<Record<string, RowState>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Saves run one after another, each with the version the previous one
  // returned; typing quickly through the list never races two saves.
  const versionRef = useRef(0);
  const queue = useRef<Promise<void>>(Promise.resolve());

  const load = useCallback(async () => {
    if (!assessmentId) return;
    try {
      const loaded = await request<Detail>(`/api/v1/assessments/${assessmentId}`);
      setDetail(loaded);
      versionRef.current = loaded.version;
      const next: Record<string, RowState> = {};
      for (const row of loaded.results) {
        next[row.student_id] = {
          score: row.score !== null ? String(Number(row.score)) : "",
          absent: row.marking_outcome === "absent",
          saved: row.score !== null || row.marking_outcome === "absent",
          saving: false,
          error: false,
        };
      }
      setRows(next);
    } catch (caught) {
      setError(caught);
    }
  }, [assessmentId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  if (detail === null) return error ? <Problem error={error} /> : <Loading />;

  const max = Number(detail.max_score);
  const editable = detail.state === "draft" || detail.state === "reopened";
  const componentId = detail.components[0]?.id ?? "";
  const marked = Object.values(rows).filter((row) => row.saved).length;
  const total = detail.results.length;

  const save = (studentId: string, next: RowState) => {
    queue.current = queue.current.then(() => saveNow(studentId, next));
    return queue.current;
  };

  const saveNow = async (studentId: string, next: RowState) => {
    const result = detail.results.find((row) => row.student_id === studentId);
    if (!result || !editable) return;
    const value = Number(next.score);
    if (!next.absent && (next.score === "" || Number.isNaN(value) || value < 0 || value > max)) {
      setRows((previous) => ({ ...previous, [studentId]: { ...next, error: next.score !== "", saved: false } }));
      return;
    }
    setRows((previous) => ({ ...previous, [studentId]: { ...next, saving: true, error: false } }));
    try {
      const response = await patchResult(detail.id, studentId, {
        expected_version: versionRef.current,
        attempt_id: result.attempt_id,
        status: "draft",
        marking_outcome: next.absent ? "absent" : "scored",
        component_scores: next.absent ? [] : [{ component_id: componentId, score: value.toFixed(2) }],
      });
      versionRef.current = response.version;
      setRows((previous) => ({ ...previous, [studentId]: { ...next, saving: false, saved: true } }));
    } catch (caught) {
      setError(caught);
      setRows((previous) => ({ ...previous, [studentId]: { ...next, saving: false, error: true } }));
    }
  };

  const step = async (work: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work();
      setNotice(done);
      await load();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="marking-title">
      <p>
        <Link to="/assessment/setup">{t("assessments.back")}</Link>
      </p>
      <h2 id="marking-title">
        {detail.section_label} · {detail.subject_name}
      </h2>
      <p className="hint">
        {t(`assessments.type.${detail.type}`)} · {t("assessments.out_of")} {max} ·{" "}
        {t(`assessments.state.${detail.state}`)}
      </p>
      <p role="status" aria-live="polite">
        {marked}/{total} {t("assessments.marked")}
        {editable ? ` · ${t("assessments.autosave")}` : ""}
      </p>
      {notice ? <p role="status" className="notice-success">{notice}</p> : null}
      <Problem error={error} />
      <ol className="register-list marks-list">
        {detail.results.map((result) => {
          const row = rows[result.student_id];
          if (!row) return null;
          return (
            <li key={result.student_id} className={row.absent ? "mark-absent" : ""}>
              <span className="register-name">{result.display_name}</span>
              <div className="mark-inputs">
                <input
                  aria-label={`${t("assessments.marks_for")} ${result.display_name}`}
                  inputMode="decimal"
                  className={row.error ? "invalid" : ""}
                  disabled={!editable || row.absent}
                  value={row.absent ? "" : row.score}
                  onChange={(event) =>
                    setRows((previous) => ({
                      ...previous,
                      [result.student_id]: { ...row, score: event.target.value, saved: false },
                    }))
                  }
                  onBlur={() => void save(result.student_id, row)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") (event.target as HTMLInputElement).blur();
                  }}
                />
                <span className="hint">/ {max}</span>
                <label className="inline">
                  <input
                    type="checkbox"
                    checked={row.absent}
                    disabled={!editable}
                    onChange={(event) => {
                      // Show the tick at once; the save follows in order behind earlier saves.
                      const next = { ...row, absent: event.target.checked, saved: false };
                      setRows((previous) => ({ ...previous, [result.student_id]: next }));
                      void save(result.student_id, next);
                    }}
                  />
                  {t("assessments.absent")}
                </label>
                <span className="save-state" aria-hidden="true">
                  {row.saving ? "…" : row.saved ? "✓" : ""}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="sticky-actions">
        {editable ? (
          <button
            type="button"
            disabled={busy || marked < total}
            title={marked < total ? t("assessments.mark_everyone") : undefined}
            onClick={() =>
              void step(async () => {
                await queue.current;
                return submitAssessment(detail.id, versionRef.current);
              }, t("assessments.submitted"))
            }
          >
            {t("assessments.submit")}
          </button>
        ) : null}
        {detail.state === "submitted" && can(actions, "results.approve") ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => void step(() => approveAssessment(detail.id, versionRef.current), t("assessments.approved"))}
          >
            {t("assessments.approve")}
          </button>
        ) : null}
        {detail.state === "approved" && can(actions, "results.publish") ? (
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void step(
                () => publishAssessment(detail.id, versionRef.current, crypto.randomUUID()),
                t("assessments.published"),
              )
            }
          >
            {t("assessments.publish")}
          </button>
        ) : null}
      </div>
    </section>
  );
}

export default MarkingPage;
