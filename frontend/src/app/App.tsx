/**
 * The application shell: language switch, navigation, and the routed outlet.
 *
 * Contains no business logic and knows no module by name -- it renders whatever
 * is in REGISTERED_MODULES, which is what lets one standalone build serve one
 * module without the shell changing.
 */

import { NavLink, Route, Routes } from "react-router-dom";
import { LanguageProvider, useLanguage } from "@shared/i18n/LanguageContext";
import { LANGUAGES, type Language } from "@shared/i18n/messages";
import { REGISTERED_MODULES } from "./registeredModules";
import { navigationRoutes } from "./moduleRegistry";

/** Language selector. Labels are the language's own name, so they are not translated. */
function LanguageSwitch() {
  const { language, setLanguage, t } = useLanguage();
  const names: Record<Language, string> = { en: "English", ml: "മലയാളം" };
  return (
    <label className="language-switch">
      <span>{t("ui.language")}</span>
      <select
        aria-label={t("ui.language")}
        value={language}
        onChange={(event) => setLanguage(event.target.value as Language)}
      >
        {LANGUAGES.map((code) => (
          <option key={code} value={code}>
            {names[code]}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Primary navigation, built from each feature's own metadata. */
function Navigation() {
  const { t } = useLanguage();
  const routes = navigationRoutes(REGISTERED_MODULES);
  return (
    <nav aria-label="Main">
      <ul>
        {routes.map((route) => (
          <li key={route.path}>
            <NavLink to={route.path}>{t(route.navLabelKey ?? route.path)}</NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Shown for an unknown path. */
function NotFound() {
  const { t } = useLanguage();
  return <p role="status">{t("error.object_inaccessible")}</p>;
}

/** The shell, without the router (so tests can supply their own). */
export function AppShell() {
  return (
    <LanguageProvider>
      <header>
        <h1>School platform</h1>
        <Navigation />
        <LanguageSwitch />
      </header>
      <main>
        <Routes>
          {REGISTERED_MODULES.flatMap((module) =>
            module.routes.map((route) => (
              <Route key={route.path} path={route.path} element={<route.component />} />
            )),
          )}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </LanguageProvider>
  );
}

export default AppShell;
