/** Notice composer and audience preview. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createNotice, publishNotice, type Notice, type NoticeLocale } from "./api";

export function NoticeComposerPage() {
  const { t, language } = useLanguage();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [locale, setLocale] = useState<NoticeLocale>(language === "ml" ? "ml" : "en");
  const [audienceKind, setAudienceKind] = useState<"section" | "person_ids">("section");
  const [sectionId, setSectionId] = useState("");
  const [personIds, setPersonIds] = useState("");
  const [draft, setDraft] = useState<Notice | null>(null);
  const [publishedCount, setPublishedCount] = useState<number | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function saveDraft() {
    setBusy(true);
    setErrorKey(null);
    setPublishedCount(null);
    try {
      const audience =
        audienceKind === "section"
          ? { kind: "section" as const, section_id: sectionId.trim() }
          : {
              kind: "person_ids" as const,
              person_ids: personIds
                .split(/[\s,]+/)
                .map((id) => id.trim())
                .filter((id) => id.length > 0),
            };
      const notice = await createNotice({ title: title.trim(), body: body.trim(), locale, audience });
      setDraft(notice);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (draft === null) return;
    setBusy(true);
    setErrorKey(null);
    try {
      const result = await publishNotice(draft.id, draft.version);
      setDraft(result.notice);
      setPublishedCount(result.audience_snapshot.recipient_ids.length);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>{t("communications.notices_title")}</h1>
      <label>
        {t("communications.notice_title")}
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        {t("communications.notice_body")}
        <textarea value={body} onChange={(event) => setBody(event.target.value)} rows={6} />
      </label>
      <label>
        {t("communications.notice_locale")}
        <select value={locale} onChange={(event) => setLocale(event.target.value as NoticeLocale)}>
          <option value="en">en</option>
          <option value="ml">ml</option>
        </select>
      </label>
      <fieldset>
        <legend>{t("communications.audience")}</legend>
        <label>
          <input
            type="radio"
            checked={audienceKind === "section"}
            onChange={() => setAudienceKind("section")}
          />
          {t("communications.audience_section")}
        </label>
        <label>
          <input
            type="radio"
            checked={audienceKind === "person_ids"}
            onChange={() => setAudienceKind("person_ids")}
          />
          {t("communications.audience_people")}
        </label>
        {audienceKind === "section" ? (
          <label>
            {t("communications.section_id")}
            <input value={sectionId} onChange={(event) => setSectionId(event.target.value)} />
          </label>
        ) : (
          <label>
            {t("communications.person_ids")}
            <textarea
              value={personIds}
              onChange={(event) => setPersonIds(event.target.value)}
              placeholder={t("communications.person_ids_hint")}
            />
          </label>
        )}
      </fieldset>
      <button type="button" disabled={busy || title.trim().length === 0 || body.trim().length === 0} onClick={() => void saveDraft()}>
        {t("communications.save_draft")}
      </button>
      {draft !== null && (
        <section>
          <p role="status">
            {t("communications.draft_saved")}: {draft.id} · {draft.state} · v{draft.version}
          </p>
          {draft.state === "draft" && (
            <button type="button" disabled={busy} onClick={() => void publish()}>
              {t("communications.publish")}
            </button>
          )}
          {publishedCount !== null && (
            <p role="status">
              {t("communications.published_recipients")}: {publishedCount}
            </p>
          )}
        </section>
      )}
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
        </div>
      )}
    </section>
  );
}
