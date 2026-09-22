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
    "error.required": "This is required.",
    "error.invalid_login_name": "Use letters, numbers, dots or dashes, with no spaces.",
    "error.login_name_taken": "Another account already uses this login name.",
    "error.password_too_short": "Use at least 10 characters.",
    "error.password_incorrect": "Your current password is not correct.",
    "error.password_unchanged": "Choose a password different from the current one.",
    "error.person_already_has_account": "This person already has a login.",
    "error.last_owner": "The school must keep at least one active owner.",
    "error.cannot_deactivate_self": "You cannot deactivate your own account.",
    "error.unknown_role": "One of the chosen roles no longer exists.",
    "error.grant_escalation": "You cannot give out permissions you do not hold yourself.",
    "ui.request_id": "Reference",
    "ui.saved": "Saved.",
    "ui.cancel": "Cancel",
    "ui.optional": "optional",
    "home.title": "Home",
    "home.everyday": "Everyday tasks",
    "home.nothing": "Your account has no tasks yet. Ask the school office to check your role.",
    "home.setup.title": "Setting up the school",
    "home.setup.check_school": "1. Check the school name, year, classes and subjects",
    "home.setup.staff": "2. Add staff, give them logins, assign what they teach",
    "home.setup.students": "3. Admit students and create parent logins",
    "home.setup.import": "   …or import many students at once from a spreadsheet",
    "home.setup.timetable": "4. Fill in and publish the timetable",
    "home.setup.fees": "5. Set up fee heads and fee plans",
    "home.setup.accounts": "6. Review everyone who can sign in",
    "nav.demo": "Demo",
    "ui.loading": "Loading…",
    "ui.not_for_account": "This page is not part of your account.",
    "ui.go_home": "Go to your home page",
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
    "error.required": "ഇത് നിർബന്ധമാണ്.",
    "error.invalid_login_name": "അക്ഷരങ്ങൾ, അക്കങ്ങൾ, കുത്ത്, ഡാഷ് എന്നിവ മാത്രം; സ്പേസ് പാടില്ല.",
    "error.login_name_taken": "ഈ ലോഗിൻ പേര് മറ്റൊരു അക്കൗണ്ട് ഉപയോഗിക്കുന്നു.",
    "error.password_too_short": "കുറഞ്ഞത് 10 അക്ഷരങ്ങൾ ഉപയോഗിക്കുക.",
    "error.password_incorrect": "നിലവിലെ പാസ്‌വേഡ് ശരിയല്ല.",
    "error.password_unchanged": "നിലവിലുള്ളതിൽ നിന്ന് വ്യത്യസ്തമായ പാസ്‌വേഡ് തിരഞ്ഞെടുക്കുക.",
    "error.person_already_has_account": "ഈ വ്യക്തിക്ക് ഇതിനകം ലോഗിൻ ഉണ്ട്.",
    "error.last_owner": "സ്കൂളിന് കുറഞ്ഞത് ഒരു സജീവ ഉടമയെങ്കിലും വേണം.",
    "error.cannot_deactivate_self": "സ്വന്തം അക്കൗണ്ട് നിർജ്ജീവമാക്കാൻ കഴിയില്ല.",
    "error.unknown_role": "തിരഞ്ഞെടുത്ത ഒരു റോൾ ഇപ്പോൾ നിലവിലില്ല.",
    "error.grant_escalation": "നിങ്ങൾക്കില്ലാത്ത അനുമതികൾ മറ്റുള്ളവർക്ക് നൽകാൻ കഴിയില്ല.",
    "ui.request_id": "റഫറൻസ്",
    "ui.saved": "സംരക്ഷിച്ചു.",
    "ui.cancel": "റദ്ദാക്കുക",
    "ui.optional": "ഐച്ഛികം",
    "home.title": "ഹോം",
    "home.everyday": "ദൈനംദിന ജോലികൾ",
    "home.nothing": "നിങ്ങളുടെ അക്കൗണ്ടിന് ഇനിയും ജോലികളില്ല. സ്കൂൾ ഓഫീസിനോട് റോൾ പരിശോധിക്കാൻ ആവശ്യപ്പെടുക.",
    "home.setup.title": "സ്കൂൾ സജ്ജീകരണം",
    "home.setup.check_school": "1. സ്കൂളിന്റെ പേര്, വർഷം, ക്ലാസുകൾ, വിഷയങ്ങൾ പരിശോധിക്കുക",
    "home.setup.staff": "2. ജീവനക്കാരെ ചേർക്കുക, ലോഗിൻ നൽകുക, അധ്യാപന ചുമതല നൽകുക",
    "home.setup.students": "3. വിദ്യാർത്ഥികളെ പ്രവേശിപ്പിക്കുക, രക്ഷിതാക്കൾക്ക് ലോഗിൻ നൽകുക",
    "home.setup.import": "   …അല്ലെങ്കിൽ സ്പ്രെഡ്ഷീറ്റിൽ നിന്ന് ഒരുമിച്ച് ഇറക്കുമതി ചെയ്യുക",
    "home.setup.timetable": "4. ടൈംടേബിൾ പൂരിപ്പിച്ച് പ്രസിദ്ധീകരിക്കുക",
    "home.setup.fees": "5. ഫീസ് ഇനങ്ങളും പദ്ധതികളും സജ്ജമാക്കുക",
    "home.setup.accounts": "6. സൈൻ ഇൻ ചെയ്യാൻ കഴിയുന്നവരെ പരിശോധിക്കുക",
    "nav.demo": "ഡെമൊ",
    "ui.loading": "ലോഡ് ചെയ്യുന്നു…",
    "ui.not_for_account": "ഈ പേജ് നിങ്ങളുടെ അക്കൗണ്ടിന്റെ ഭാഗമല്ല.",
    "ui.go_home": "ഹോം പേജിലേക്ക് പോകുക",
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
