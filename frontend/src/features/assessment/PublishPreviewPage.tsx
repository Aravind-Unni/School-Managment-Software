/**
 * Publish preview for an approved assessment.
 */

import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError, TransportError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import {
  approveAssessment,
  publishAssessment,
  reopenAssessment,
  submitAssessment,
  type AssessmentDTO,
} from "./api";
import { loadAssessment, rememberAssessment } from "./storage";

function toMessageKey(error: unknown): string {
  if (error instanceof ApiError) return error.messageKey;
  if (error instanceof TransportError) return "error.transport";
  return "error.transport";
}

export function PublishPreviewPage() {
  const { t } = useLanguage();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const location = useLocation();
  const [assessment, setAssessment] = useState<AssessmentDTO | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!assessmentId) return;
    const fromState = (location.state as { assessment?: AssessmentDTO } | null)?.assessment;
    const cached = fromState ?? loadAssessment(assessmentId);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    if (cached) setAssessment(cached);
  }, [assessmentId, location.state]);

  async function runStep(
    step: string,
    action: (version: number) => Promise<AssessmentDTO | { publication_id: string }>,
  ) {
    if (!assessmentId || !assessment) return;
    setBusy(step);
    setErrorKey(null);
    setMessage(null);
    try {
      const outcome = await action(assessment.version);
      if ("publication_id" in outcome) {
        setMessage(outcome.publication_id);
        setAssessment((current) => {
          if (!current) return current;
          const next = { ...current, state: "published", version: current.version + 1 };
          rememberAssessment(next);
          return next;
        });
      } else {
        setAssessment(outcome);
        rememberAssessment(outcome);
      }
    } catch (error) {
      setErrorKey(toMessageKey(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section>
      <h1>{t("assessment.publish.title")}</h1>
      <p>
        <Link to={assessmentId ? `/assessment/${assessmentId}/marking` : "/assessment/setup"}>
          {t("assessment.back")}
        </Link>
      </p>
      {assessment ? (
        <p>
          {t("assessment.marking.state")}: {assessment.state} (v{assessment.version})
        </p>
      ) : (
        assessmentId && <p role="status">{t("assessment.marking.missing_context")}</p>
      )}
      {errorKey && <p role="alert">{t(errorKey)}</p>}
      {message && (
        <p role="status">
          {t("assessment.publish.done")}: {message}
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: "20rem" }}>
        <button
          type="button"
          disabled={!assessment || busy !== null || assessment.state !== "draft"}
          onClick={() =>
            void runStep("submit", (version) => submitAssessment(assessmentId!, version))
          }
        >
          {busy === "submit" ? t("ui.loading") : t("assessment.marking.submit")}
        </button>
        <button
          type="button"
          disabled={!assessment || busy !== null || assessment.state !== "submitted"}
          onClick={() =>
            void runStep("approve", (version) => approveAssessment(assessmentId!, version))
          }
        >
          {busy === "approve" ? t("ui.loading") : t("assessment.publish.approve")}
        </button>
        <button
          type="button"
          disabled={!assessment || busy !== null || assessment.state !== "approved"}
          onClick={() =>
            void runStep("publish", (version) =>
              publishAssessment(
                assessmentId!,
                version,
                `publish-${assessmentId}-${version}-${Date.now()}`,
              ),
            )
          }
        >
          {busy === "publish" ? t("ui.loading") : t("assessment.publish.action")}
        </button>
        <button
          type="button"
          disabled={!assessment || busy !== null || assessment.state !== "published"}
          onClick={() =>
            void runStep("reopen", (version) => reopenAssessment(assessmentId!, version))
          }
        >
          {busy === "reopen" ? t("ui.loading") : t("assessment.publish.reopen")}
        </button>
      </div>
      {message && assessmentId && (
        <p>
          <Link to={`/assessment/${assessmentId}/marking`}>{t("assessment.marking.title")}</Link>
        </p>
      )}
    </section>
  );
}
