/**
 * Language selection, shared by every feature.
 *
 * The chosen language lives in React state and in localStorage, not in a URL or
 * a cookie the server reads: the backend returns message keys and is
 * language-agnostic, so language is purely a client concern.
 */

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ACCESS_MESSAGES } from "@features/access/locales/messages";
import { LANGUAGES, SHARED_MESSAGES, translate, type Language } from "./messages";

const STORAGE_KEY = "school.language";

interface LanguageContextValue {
  readonly language: Language;
  readonly setLanguage: (language: Language) => void;
  readonly t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

/** Read the stored language, tolerating disabled or cleared storage. */
function storedLanguage(): Language {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (raw && (LANGUAGES as readonly string[]).includes(raw)) {
      return raw as Language;
    }
  } catch {
    // Private browsing or blocked storage. English is a safe default.
  }
  return "en";
}

/** Provides the active language and a translate function to the tree. */
export function LanguageProvider({ children }: { readonly children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(storedLanguage);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    try {
      globalThis.localStorage?.setItem(STORAGE_KEY, next);
    } catch {
      // Non-fatal: the choice simply will not persist across reloads.
    }
  }, []);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage,
      // Module catalogues are merged over the shared one, so a module's keys
      // resolve anywhere in the tree without each screen wiring its own lookup.
      t: (key: string) =>
        translate(language, key, {
          en: { ...SHARED_MESSAGES.en, ...ACCESS_MESSAGES.en },
          ml: { ...SHARED_MESSAGES.ml, ...ACCESS_MESSAGES.ml },
        }),
    }),
    [language, setLanguage],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

/** Access the active language. Throws outside a LanguageProvider, by design. */
export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (value === null) {
    throw new Error("useLanguage must be used inside a LanguageProvider");
  }
  return value;
}
