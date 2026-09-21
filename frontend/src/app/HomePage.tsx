/**
 * Post-login home: role-shaped shortcuts from the caller's held actions.
 */

import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { can, useSession } from "./SessionContext";
import { REGISTERED_MODULES } from "./registeredModules";
import { navigationRoutes } from "./moduleRegistry";

/** Suggest a small set of primary destinations for the signed-in actor. */
export function HomePage() {
  const { t } = useLanguage();
  const { status, session, actions } = useSession();
  if (status !== "authenticated" || session === null) {
    return null;
  }

  const routes = navigationRoutes(REGISTERED_MODULES).filter(
    (route) => !route.path.startsWith("/demo") && can(actions, route.requiredPermission),
  );

  const teacher = routes.filter(
    (r) =>
      r.path.includes("attendance") ||
      r.path.includes("timetable") ||
      r.path.includes("assessment") ||
      r.path.includes("marking"),
  );
  const guardian = routes.filter(
    (r) =>
      r.path.includes("statement") ||
      r.path.includes("student") ||
      r.path.includes("performance") ||
      r.path.includes("files") ||
      r.path.includes("notice"),
  );
  const admin = routes.filter(
    (r) =>
      r.path.includes("settings") ||
      r.path.includes("fees/setup") ||
      r.path.includes("exchange") ||
      r.path.includes("platform"),
  );

  const primary =
    admin.length > 0 ? admin.slice(0, 6) : teacher.length > 0 ? teacher.slice(0, 6) : guardian.slice(0, 6);

  return (
    <section className="home">
      <h2>Home</h2>
      <p role="status" data-testid="signed-in">
        {session.auth_level}
      </p>
      <p>Choose a task. Links you cannot use are hidden.</p>
      <ul className="home-links">
        {primary.map((route) => (
          <li key={route.path}>
            <Link to={route.path}>{t(route.navLabelKey ?? route.path)}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
