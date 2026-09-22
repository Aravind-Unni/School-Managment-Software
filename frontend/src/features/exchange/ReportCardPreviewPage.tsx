/**
 * Report cards for a whole class: choose the term and the class, generate,
 * and each pupil's card appears as it is ready, with an Open button.
 *
 * A card holds the marks published for that term, so publish results first.
 * A pupil with nothing published gets "No published marks" rather than an
 * empty card. Does not handle: sending cards to parents (they see published
 * marks on their own overview) or editing a card's layout.
 */

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";
import * as registry from "@features/registry/api";
import { schoolToday, useSchoolStructure } from "@features/registry/useSchoolStructure";
import { createReportCards, downloadReport, getReportCardJob, type ExchangeLocale, type ReportCardJob } from "./api";

const TEMPLATE_VERSION = "standard-v1";

interface CardRow {
  readonly name: string;
  readonly job: ReportCardJob;
}

const finished = (state: string) => state === "ready" || state === "failed";

export function ReportCardPreviewPage() {
  const { t, language } = useLanguage();
  const { state } = useSchoolStructure();
  const sections = state.kind === "ready" ? state.structure.sections : [];
  const [terms, setTerms] = useState<readonly registry.Term[]>([]);
  const [termId, setTermId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [locale, setLocale] = useState<ExchangeLocale>(language === "ml" ? "ml" : "en");
  const [cards, setCards] = useState<readonly CardRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const cardsRef = useRef(cards);
  useEffect(() => {
    cardsRef.current = cards;
  }, [cards]);

  useEffect(() => {
    registry.listAllTerms().then(
      (rows) => {
        setTerms(rows);
        const today = schoolToday();
        const current = rows.find((row) => row.start <= today && today <= row.end) ?? rows[0];
        if (current) setTermId(current.id);
      },
      setError,
    );
  }, []);

  // Poll unfinished cards every two seconds until each is ready or failed.
  const pending = cards.some((row) => !finished(row.job.state));
  useEffect(() => {
    if (!pending) return undefined;
    const timer = window.setInterval(() => {
      void Promise.all(
        cardsRef.current.map(async (row) =>
          finished(row.job.state) ? row : { ...row, job: await getReportCardJob(row.job.id).catch(() => row.job) },
        ),
      ).then(setCards);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [pending]);

  const generate = async () => {
    setBusy(true);
    setError(null);
    setCards([]);
    try {
      const roster = await registry.getSectionRoster(sectionId, schoolToday());
      const pupils = [...roster.students].sort((a, b) => a.display_name.localeCompare(b.display_name));
      const names = new Map(pupils.map((row) => [row.student_id, row.display_name]));
      const result = await createReportCards({
        publication_id: termId,
        student_ids: pupils.map((row) => row.student_id),
        locale,
        template_version: TEMPLATE_VERSION,
      });
      setCards(result.jobs.map((job) => ({ job, name: names.get(job.student_id) ?? "" })));
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const open = async (job: ReportCardJob) => {
    const reportId = job.report_id;
    if (!reportId) return;
    // Open the tab now, inside the click, so pop-up blockers allow it.
    const tab = window.open("", "_blank");
    try {
      const access = await downloadReport(reportId);
      if (tab) tab.location.replace(access.authorized_read_url);
      else window.location.assign(access.authorized_read_url);
    } catch (caught) {
      tab?.close();
      setError(caught);
    }
  };

  const ready = cards.filter((row) => row.job.state === "ready").length;
  const failed = cards.filter((row) => row.job.state === "failed").length;

  return (
    <section aria-labelledby="cards-title">
      <h2 id="cards-title">{t("exchange.report_cards_title")}</h2>
      <p className="hint">{t("cards.intro")}</p>
      <form
        className="inline-fields"
        onSubmit={(event) => {
          event.preventDefault();
          void generate();
        }}
      >
        <label>
          {t("cards.term")}
          <select value={termId} onChange={(event) => setTermId(event.target.value)}>
            {terms.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("cards.class")}
          <select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
            <option value="">—</option>
            {sections.map((row) => (
              <option key={row.id} value={row.id}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("cards.language")}
          <select value={locale} onChange={(event) => setLocale(event.target.value as ExchangeLocale)}>
            <option value="en">English</option>
            <option value="ml">മലയാളം</option>
          </select>
        </label>
        <div className="form-end">
          <button aria-busy={busy} type="submit" disabled={busy || termId === "" || sectionId === ""}>
            {busy ? t("ui.loading") : t("exchange.generate_report_cards")}
          </button>
        </div>
      </form>
      <Problem error={error} />
      {cards.length > 0 ? (
        <>
          <p role="status" aria-live="polite">
            {ready}/{cards.length} {t("cards.ready")}
            {failed > 0 ? ` · ${failed} ${t("cards.no_marks")}` : ""}
          </p>
          <ul className="register-list">
            {cards.map((row) => (
              <li key={row.job.id}>
                <span className="register-name">{row.name}</span>
                {row.job.state === "ready" ? (
                  <button type="button" className="secondary" onClick={() => void open(row.job)}>
                    {t("cards.open")}
                  </button>
                ) : row.job.state === "failed" ? (
                  <span className="attention">{t("cards.no_marks")}</span>
                ) : (
                  <span className="hint">{t("cards.preparing")}</span>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
