/**
 * Marking grid with a side-by-side answer-sheet viewer placeholder.
 */

import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  getSectionRoster,
  type RosterStudent,
} from "@features/registry/api";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  patchResult,
  submitAssessment,
  type AssessmentDTO,
  viewEvidence,
} from "./api";
import { loadAssessment, loadAttemptId, rememberAssessment } from "./storage";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

function rosterDateIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Best-effort attempt discovery for rows created in this browser session. */
async function primeMissingAttempts(
  assessmentId: string,
  expectedVersion: number,
  students: readonly RosterStudent[],
): Promise<void> {
  await Promise.all(
    students.map(async (student) => {
      if (loadAttemptId(assessmentId, student.student_id)) return;
      try {
        await patchResult(assessmentId, student.student_id, {
          expected_version: expectedVersion,
          attempt_id: student.student_id,
          status: "draft",
          marking_outcome: "absent",
        });
      } catch {
        // Attempt ids are server-assigned; discovery succeeds only when cached from PATCH.
      }
    }),
  );
}

type RowState = {
  readonly student: RosterStudent;
  score: string;
  outcome: "scored" | "absent" | "exempt";
  attemptId: string | null;
  resultId: string | null;
  bindingId: string | null;
  busy: boolean;
  errorKey: string | null;
};

export function MarkingGridPage() {
  const { t } = useLanguage();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const location = useLocation();
  const [assessment, setAssessment] = useState<AssessmentDTO | null>(null);
  const [assessmentVersion, setAssessmentVersion] = useState(1);
  const [rows, setRows] = useState<RowState[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [submitBusy, setSubmitBusy] = useState(false);

  useEffect(() => {
    if (!assessmentId) return;
    const fromState = (location.state as { assessment?: AssessmentDTO } | null)?.assessment;
    const cached = fromState ?? loadAssessment(assessmentId);
    if (cached) {
      setAssessment(cached);
      setAssessmentVersion(cached.version);
    }
  }, [assessmentId, location.state]);

  useEffect(() => {
    if (!assessmentId || !assessment) return;
    let cancelled = false;
    void (async () => {
      try {
        const roster = await getSectionRoster(
          assessment.section_id,
          rosterDateIso(),
          assessment.subject_id,
        );
        if (cancelled) return;
        await primeMissingAttempts(assessmentId, assessmentVersion, roster.students);
        if (cancelled) return;
        setRows(
          roster.students.map((student) => ({
            student,
            score: "",
            outcome: "scored" as const,
            attemptId: loadAttemptId(assessmentId, student.student_id),
            resultId: null,
            bindingId: null,
            busy: false,
            errorKey: null,
          })),
        );
        if (roster.students[0]) {
          setSelectedStudentId(roster.students[0].student_id);
        }
        setPageError(null);
      } catch (error) {
        if (!cancelled) setPageError(toMessageKey(error));
      }
    })();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once for the initial load
  }, [assessment, assessmentId]);

  async function saveRow(studentId: string) {
    if (!assessmentId || !assessment) return;
    const componentId = assessment.components[0]?.id;
    if (!componentId) return;

    let rowSnapshot: RowState | undefined;
    setRows((current) => {
      rowSnapshot = current.find((item) => item.student.student_id === studentId);
      return current.map((row) =>
        row.student.student_id === studentId ? { ...row, busy: true, errorKey: null } : row,
      );
    });

    const attemptId =
      rowSnapshot?.attemptId ?? loadAttemptId(assessmentId, studentId);
    if (!attemptId) {
      setRows((current) =>
        current.map((item) =>
          item.student.student_id === studentId
            ? { ...item, busy: false, errorKey: "assessment.marking.no_attempt" }
            : item,
        ),
      );
      return;
    }

    const body: Record<string, unknown> = {
      expected_version: assessmentVersion,
      attempt_id: attemptId,
      status: "draft",
      marking_outcome: rowSnapshot?.outcome ?? "scored",
    };
    if (rowSnapshot?.outcome === "scored") {
      body.component_scores = [
        { component_id: componentId, score: rowSnapshot.score || "0.00" },
      ];
    }

    try {
      const patched = await patchResult(assessmentId, studentId, body);
      const nextAssessment = { ...assessment, version: patched.version };
      setAssessment(nextAssessment);
      setAssessmentVersion(patched.version);
      rememberAssessment(nextAssessment);
      setRows((current) =>
        current.map((item) =>
          item.student.student_id === studentId
            ? {
                ...item,
                busy: false,
                attemptId: patched.result.attempt_id,
                resultId: patched.result.result_id,
                bindingId: patched.result.evidence_refs[0]?.binding_id ?? item.bindingId,
                score: patched.result.score ?? item.score,
                errorKey: null,
              }
            : item,
        ),
      );
    } catch (error) {
      setRows((current) =>
        current.map((item) =>
          item.student.student_id === studentId
            ? { ...item, busy: false, errorKey: toMessageKey(error) }
            : item,
        ),
      );
    }
  }

  async function onSubmitForReview() {
    if (!assessmentId || !assessment) return;
    setSubmitBusy(true);
    setPageError(null);
    try {
      const submitted = await submitAssessment(assessmentId, assessmentVersion);
      setAssessment(submitted);
      setAssessmentVersion(submitted.version);
      rememberAssessment(submitted);
    } catch (error) {
      setPageError(toMessageKey(error));
    } finally {
      setSubmitBusy(false);
    }
  }

  useEffect(() => {
    if (!selectedStudentId) {
      setViewerUrl(null);
      return;
    }
    const row = rows.find((item) => item.student.student_id === selectedStudentId);
    if (!row?.resultId || !row.bindingId) {
      setViewerUrl(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const grant = await viewEvidence(row.resultId!, row.bindingId!);
        if (!cancelled) setViewerUrl(grant.read_url);
      } catch {
        if (!cancelled) setViewerUrl(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [rows, selectedStudentId]);

  return (
    <section>
      <h1>{t("assessment.marking.title")}</h1>
      <p>
        <Link to="/assessment/setup">{t("assessment.back")}</Link>
        {assessment ? (
          <>
            {" · "}
            {t("assessment.marking.state")}: {assessment.state} (v{assessmentVersion})
          </>
        ) : null}
      </p>
      {pageError && <p role="alert">{t(pageError)}</p>}
      {!assessment && assessmentId && (
        <p role="status">{t("assessment.marking.missing_context")}</p>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <section aria-label={t("assessment.marking.title")}>
          {rows.length === 0 && !pageError && <p role="status">{t("ui.loading")}</p>}
          <table>
            <thead>
              <tr>
                <th scope="col">{t("assessment.marking.pupil")}</th>
                <th scope="col">{t("assessment.marking.score")}</th>
                <th scope="col">{t("assessment.marking.outcome")}</th>
                <th scope="col">{t("assessment.marking.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.student.student_id}>
                  <th scope="row">
                    <button
                      type="button"
                      onClick={() => setSelectedStudentId(row.student.student_id)}
                    >
                      {row.student.display_name}
                    </button>
                  </th>
                  <td>
                    <input
                      type="text"
                      inputMode="decimal"
                      value={row.score}
                      disabled={row.outcome !== "scored"}
                      onChange={(event) =>
                        setRows((current) =>
                          current.map((item) =>
                            item.student.student_id === row.student.student_id
                              ? { ...item, score: event.target.value }
                              : item,
                          ),
                        )
                      }
                    />
                  </td>
                  <td>
                    <select
                      value={row.outcome}
                      onChange={(event) =>
                        setRows((current) =>
                          current.map((item) =>
                            item.student.student_id === row.student.student_id
                              ? {
                                  ...item,
                                  outcome: event.target.value as RowState["outcome"],
                                }
                              : item,
                          ),
                        )
                      }
                    >
                      <option value="scored">{t("assessment.marking.outcome_scored")}</option>
                      <option value="absent">{t("assessment.marking.outcome_absent")}</option>
                      <option value="exempt">{t("assessment.marking.outcome_exempt")}</option>
                    </select>
                  </td>
                  <td>
                    <button
                      type="button"
                      disabled={row.busy}
                      onClick={() => void saveRow(row.student.student_id)}
                    >
                      {t("assessment.marking.save")}
                    </button>
                    {row.errorKey && <p role="alert">{t(row.errorKey)}</p>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {assessment && assessment.state === "draft" && (
            <p>
              <button type="button" disabled={submitBusy} onClick={() => void onSubmitForReview()}>
                {t("assessment.marking.submit")}
              </button>
            </p>
          )}
        </section>
        <aside aria-label={t("assessment.marking.viewer")}>
          <h2>{t("assessment.marking.viewer")}</h2>
          {viewerUrl ? (
            <iframe title={t("assessment.marking.viewer")} src={viewerUrl} width="100%" height="360" />
          ) : (
            <p>{t("assessment.marking.viewer_placeholder")}</p>
          )}
        </aside>
      </div>
      {assessmentId ? (
        <p>
          <Link to={`/assessment/${assessmentId}/publish`}>{t("assessment.publish.title")}</Link>
        </p>
      ) : null}
    </section>
  );
}
