/**
 * Translation for M03, merging its catalogue over the shared one.
 *
 * A module owns its own strings; the shell owns the shared error and UI keys. A
 * missing key renders as the key itself, so a gap is visible in the UI and in a
 * screenshot rather than silently blank.
 *
 * `format` fills {placeholders} -- the publish confirmation names a date, and
 * building that string by concatenation would put English word order into the
 * Malayalam sentence.
 */

import { useLanguage } from "@shared/i18n/LanguageContext";
import { SHARED_MESSAGES } from "@shared/i18n/messages";
import { TIMETABLE_MESSAGES } from "./locales/messages";

export type Translate = (key: string, values?: Record<string, string>) => string;

export function useTimetableMessages(): Translate {
  const { language } = useLanguage();
  return (key: string, values?: Record<string, string>) => {
    const template =
      TIMETABLE_MESSAGES[language]?.[key] ??
      SHARED_MESSAGES[language]?.[key] ??
      TIMETABLE_MESSAGES.en?.[key] ??
      SHARED_MESSAGES.en?.[key] ??
      key;
    if (values === undefined) return template;
    return Object.entries(values).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, value),
      template,
    );
  };
}
