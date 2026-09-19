/**
 * Translation for M01, merging its catalogue over the shared one.
 *
 * A module owns its own strings; the shell owns the shared error and UI keys. A
 * missing key renders as the key itself, so a gap is visible in the UI and in a
 * screenshot rather than silently blank.
 */

import { useLanguage } from "@shared/i18n/LanguageContext";
import { SHARED_MESSAGES } from "@shared/i18n/messages";
import { ACCESS_MESSAGES } from "./locales/messages";

export function useAccessMessages(): (key: string) => string {
  const { language } = useLanguage();
  return (key: string) =>
    ACCESS_MESSAGES[language]?.[key] ??
    SHARED_MESSAGES[language]?.[key] ??
    ACCESS_MESSAGES.en?.[key] ??
    SHARED_MESSAGES.en?.[key] ??
    key;
}
