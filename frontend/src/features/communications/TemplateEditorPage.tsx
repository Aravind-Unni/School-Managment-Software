/** Enqueue templated message deliveries (contract has no template list API). */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { enqueueMessage, type Delivery, type NoticeLocale } from "./api";

export function TemplateEditorPage() {
  const { t, language } = useLanguage();
  const [templateKey, setTemplateKey] = useState("");
  const [recipientRef, setRecipientRef] = useState("");
  const [locale, setLocale] = useState<NoticeLocale>(language === "ml" ? "ml" : "en");
  const [channel, setChannel] = useState<"in_app" | "sms">("in_app");
  const [variablesJson, setVariablesJson] = useState("{}");
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send() {
    setBusy(true);
    setErrorKey(null);
    setDelivery(null);
    let variables: Record<string, string | number | boolean | null>;
    try {
      variables = JSON.parse(variablesJson) as Record<string, string | number | boolean | null>;
    } catch {
      setErrorKey("communications.variables_invalid");
      setBusy(false);
      return;
    }
    try {
      const result = await enqueueMessage({
        template_key: templateKey.trim(),
        recipient_ref: recipientRef.trim(),
        locale,
        channel,
        variables,
        dedupe_key: crypto.randomUUID(),
      });
      setDelivery(result);
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>{t("communications.templates_title")}</h1>
      <p>{t("communications.templates_enqueue_help")}</p>
      <label>
        {t("communications.template_key")}
        <input value={templateKey} onChange={(event) => setTemplateKey(event.target.value)} />
      </label>
      <label>
        {t("communications.recipient_ref")}
        <input value={recipientRef} onChange={(event) => setRecipientRef(event.target.value)} />
      </label>
      <label>
        {t("communications.channel")}
        <select value={channel} onChange={(event) => setChannel(event.target.value as "in_app" | "sms")}>
          <option value="in_app">in_app</option>
          <option value="sms">sms</option>
        </select>
      </label>
      <label>
        {t("communications.notice_locale")}
        <select value={locale} onChange={(event) => setLocale(event.target.value as NoticeLocale)}>
          <option value="en">en</option>
          <option value="ml">ml</option>
        </select>
      </label>
      <label>
        {t("communications.variables_json")}
        <textarea value={variablesJson} onChange={(event) => setVariablesJson(event.target.value)} rows={4} />
      </label>
      <button
        type="button"
        disabled={busy || templateKey.trim().length === 0 || recipientRef.trim().length === 0}
        onClick={() => void send()}
      >
        {t("communications.enqueue")}
      </button>
      {delivery !== null && (
        <section>
          <p role="status">
            {t("communications.delivery_created")}: {delivery.id} · {delivery.state}
          </p>
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
