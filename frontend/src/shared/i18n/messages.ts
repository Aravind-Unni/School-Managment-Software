/**
 * English and Malayalam message catalogues.
 *
 * The backend returns `message_key` values and never user-facing prose, so this
 * is the only place a human-readable string exists. A missing key renders the
 * key itself rather than throwing: a half-translated screen is recoverable, a
 * crashed one is not.
 */

export type Language = "en" | "ml";

export const LANGUAGES: readonly Language[] = ["en", "ml"] as const;

/**
 * Shared keys every module can use: the error taxonomy and common UI.
 * A module adds its own catalogue beside its feature and merges it in.
 */
export const SHARED_MESSAGES: Record<Language, Record<string, string>> = {
  en: {
    "error.unauthenticated": "Please sign in to continue.",
    "error.two_factor_required": "Two-factor authentication is required for this action.",
    "error.two_factor_stale": "Please confirm two-factor authentication again to continue.",
    "error.action_denied": "You do not have permission to do this.",
    "error.object_inaccessible": "This item is not available.",
    "error.version_conflict": "Someone else changed this first. Reload and try again.",
    "error.state_conflict": "This cannot be done in the item's current state.",
    "error.validation_failed": "Please correct the highlighted fields.",
    "error.client_asserted_identity": "The application sent an invalid request.",
    "error.server_internal_field_rejected": "The application sent an invalid request.",
    "error.malformed_cursor": "This page link is no longer valid. Start from the first page.",
    "error.cursor_field_missing": "This page link is no longer valid.",
    "error.transport": "Could not reach the server. Check your connection.",
    "nav.demo": "Demo",
    "ui.loading": "Loading…",
    "ui.empty": "Nothing to show yet.",
    "ui.retry": "Try again",
    "ui.load_more": "Load more",
    "ui.language": "Language",
  },
  ml: {
    "error.unauthenticated": "തുടരാൻ സൈൻ ഇൻ ചെയ്യുക.",
    "error.two_factor_required": "ഈ പ്രവർത്തനത്തിന് രണ്ടു-ഘടക സ്ഥിരീകരണം ആവശ്യമാണ്.",
    "error.two_factor_stale": "തുടരാൻ രണ്ടു-ഘടക സ്ഥിരീകരണം വീണ്ടും നടത്തുക.",
    "error.action_denied": "ഇതു ചെയ്യാൻ നിങ്ങൾക്ക് അനുമതിയില്ല.",
    "error.object_inaccessible": "ഈ വിവരം ലബ്യമല്ല.",
    "error.version_conflict": "മറ്റൊരാൾ ഇതിന് മുമ്പ് മാറ്റം വരുത്തി. വീണ്ടും ലോഡ് ചെയ്യുക.",
    "error.state_conflict": "ഇപ്പോഴത്തെ അവസ്ഥയിൽ ഇതു ചെയ്യാൻ കഴിയില്ല.",
    "error.validation_failed": "അടയാളപ്പെടുത്തിയ ഫീൽഡുകൾ ശരിയാക്കുക.",
    "error.client_asserted_identity": "അപ്ലിക്കേഷൻ അസാധുവായ അപേക്ഷ അയച്ചു.",
    "error.server_internal_field_rejected": "അപ്ലിക്കേഷൻ അസാധുവായ അപേക്ഷ അയച്ചു.",
    "error.malformed_cursor": "ഈ പേജ് ലിങ്ക് ഇനി സാധുവല്ല. ആദ്യ പേജിൽ നിന്ന് തുടങ്ങുക.",
    "error.cursor_field_missing": "ഈ പേജ് ലിങ്ക് ഇനി സാധുവല്ല.",
    "error.transport": "സർവറിൽ എത്താൻ കഴിയില്ല. കണക്ഷൻ പരിശോധിക്കുക.",
    "nav.demo": "ഡെമൊ",
    "ui.loading": "ലോഡ് ചെയ്യുന്നു…",
    "ui.empty": "ഇനിയും ഒന്നുമില്ല.",
    "ui.retry": "വീണ്ടും ശ്രമിക്കുക",
    "ui.load_more": "കൂടുതൽ ലോഡ് ചെയ്യുക",
    "ui.language": "മൊഴി",
  },
};

/**
 * Resolve a message key for a language.
 *
 * Falls back to English, then to the key itself. Returning the key makes an
 * untranslated string obvious in the UI and in a screenshot, which is what a
 * reviewer needs, whereas an empty string silently hides it.
 */
export function translate(
  language: Language,
  key: string,
  catalogue: Record<Language, Record<string, string>> = SHARED_MESSAGES,
): string {
  return catalogue[language]?.[key] ?? catalogue.en?.[key] ?? key;
}

/** Keys present in English but missing in another language. */
export function missingKeys(
  language: Language,
  catalogue: Record<Language, Record<string, string>> = SHARED_MESSAGES,
): string[] {
  const english = Object.keys(catalogue.en ?? {});
  const target = catalogue[language] ?? {};
  return english.filter((key) => !(key in target));
}
