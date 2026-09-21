/**
 * Notices: write one, choose who it goes to by class or by student, and send
 * it. Staff who cannot publish send it for approval; whoever can publish sees
 * drafts waiting and publishes them from the same page.
 *
 * Choosing several classes creates one notice per class, so each class's
 * parents see exactly the notice meant for them.
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { can, useSession } from "@app/SessionContext";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { useSchoolStructure } from "@features/registry/useSchoolStructure";
import { createNotice, publishNotice, type Notice, type NoticeLocale } from "./api";

type Audience = "classes" | "students";

export function NoticeComposerPage() {
  const { t, language } = useLanguage();
  const { actions } = useSession();
  const canPublish = can(actions, "notices.publish");
  const { state } = useSchoolStructure();
  const sections = state.kind === "ready" ? state.structure.sections : [];
  const sectionLabel = new Map(sections.map((row) => [row.id, row.label]));

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [locale, setLocale] = useState<NoticeLocale>(language === "ml" ? "ml" : "en");
  const [audience, setAudience] = useState<Audience>("classes");
  const [chosenSections, setChosenSections] = useState<readonly string[]>([]);
  const [students, setStudents] = useState<readonly PickedStudent[]>([]);
  const [recent, setRecent] = useState<readonly Notice[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadRecent = useCallback(async () => {
    try {
      const page = await request<{ items: Notice[] }>("/api/v1/notices/recent");
      setRecent(page.items);
    } catch {
      setRecent([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void loadRecent();
  }, [loadRecent]);

  const audienceLabel = (row: Notice) => {
    const value = row.audience as { kind: string; section_id?: string; person_ids?: string[] };
    return value.kind === "section"
      ? (sectionLabel.get(value.section_id ?? "") ?? t("communications.a_class"))
      : `${value.person_ids?.length ?? 0} ${t("communications.students")}`;
  };

  const ready =
    title.trim() !== "" &&
    body.trim() !== "" &&
    (audience === "classes" ? chosenSections.length > 0 : students.length > 0);

  const send = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const audiences =
        audience === "classes"
          ? chosenSections.map((id) => ({ kind: "section" as const, section_id: id }))
          : [{ kind: "person_ids" as const, person_ids: students.map((row) => row.id) }];
      for (const target of audiences) {
        const draft = await createNotice({ title: title.trim(), body: body.trim(), locale, audience: target });
        if (canPublish) await publishNotice(draft.id, draft.version);
      }
      setNotice(canPublish ? t("communications.sent") : t("communications.sent_for_approval"));
      setTitle("");
      setBody("");
      setChosenSections([]);
      setStudents([]);
      await loadRecent();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const approve = async (row: Notice) => {
    setBusy(true);
    setError(null);
    try {
      await publishNotice(row.id, row.version);
      setNotice(t("communications.sent"));
      await loadRecent();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const drafts = recent.filter((row) => row.state === "draft");
  const sent = recent.filter((row) => row.state !== "draft");

  return (
    <section aria-labelledby="notices-title">
      <h2 id="notices-title">{t("communications.notices_title")}</h2>
      {notice ? <p role="status" className="notice-success">{notice}</p> : null}
      <Problem error={error} />
      <div className="two-column">
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            void send();
          }}
        >
          <h3>{t("communications.write")}</h3>
          <label>
            {t("communications.notice_title")}
            <input value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            {t("communications.notice_body")}
            <textarea value={body} onChange={(event) => setBody(event.target.value)} rows={6} />
          </label>
          <div className="inline-options">
            {(["en", "ml"] as const).map((value) => (
              <label key={value} className="inline">
                <input type="radio" checked={locale === value} onChange={() => setLocale(value)} />
                {value === "en" ? "English" : "മലയാളം"}
              </label>
            ))}
          </div>
          <fieldset>
            <legend>{t("communications.send_to")}</legend>
            <div className="inline-options">
              <label className="inline">
                <input type="radio" checked={audience === "classes"} onChange={() => setAudience("classes")} />
                {t("communications.audience_section")}
              </label>
              <label className="inline">
                <input type="radio" checked={audience === "students"} onChange={() => setAudience("students")} />
                {t("communications.audience_people")}
              </label>
            </div>
            {audience === "classes" ? (
              <div className="class-grid">
                {sections.map((row) => (
                  <label key={row.id} className="inline">
                    <input
                      type="checkbox"
                      checked={chosenSections.includes(row.id)}
                      onChange={(event) =>
                        setChosenSections((previous) =>
                          event.target.checked
                            ? [...previous, row.id]
                            : previous.filter((id) => id !== row.id),
                        )
                      }
                    />
                    {row.label}
                  </label>
                ))}
              </div>
            ) : (
              <>
                <StudentPicker
                  onPick={(row) =>
                    setStudents((previous) =>
                      previous.some((item) => item.id === row.id) ? previous : [...previous, row],
                    )
                  }
                />
                <ul className="chips">
                  {students.map((row) => (
                    <li key={row.id}>
                      {row.display_name}
                      <button
                        type="button"
                        className="quiet"
                        aria-label={`${t("communications.remove")} ${row.display_name}`}
                        onClick={() => setStudents((previous) => previous.filter((item) => item.id !== row.id))}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="hint">{t("communications.parents_see")}</p>
          </fieldset>
          <button type="submit" disabled={busy || !ready}>
            {canPublish ? t("communications.send") : t("communications.send_for_approval")}
          </button>
        </form>

        <div>
          {drafts.length > 0 ? (
            <>
              <h3>{t("communications.waiting")}</h3>
              <ul className="notice-list">
                {drafts.map((row) => (
                  <li key={row.id}>
                    <strong>{row.title}</strong>
                    <span className="hint">
                      {audienceLabel(row)} · {shortDate(row.created_at, language)}
                    </span>
                    <p>{row.body}</p>
                    {canPublish ? (
                      <button type="button" disabled={busy} onClick={() => void approve(row)}>
                        {t("communications.publish")}
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <h3>{t("communications.recently_sent")}</h3>
          {sent.length === 0 ? (
            <p className="hint">{t("ui.empty")}</p>
          ) : (
            <ul className="notice-list">
              {sent.slice(0, 20).map((row) => (
                <li key={row.id}>
                  <strong>{row.title}</strong>
                  <span className="hint">
                    {audienceLabel(row)} · {shortDate(row.updated_at, language)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
