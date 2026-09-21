/**
 * Post-login home: the school's name, a getting-started checklist for the
 * people who set the school up, and role-shaped shortcuts for everyone else.
 *
 * Only shows links the caller can use (from /auth/capabilities); the server
 * still authorises every action. Does not handle: dashboards with live counts.
 */

import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { can, useSession } from "./SessionContext";
import { REGISTERED_MODULES } from "./registeredModules";
import { navigationRoutes, type FeatureRoute } from "./moduleRegistry";

/** The order a new school is set up in. Each step links to its page. */
const SETUP_STEPS: readonly { readonly path: string; readonly key: string }[] = [
  { path: "/registry/setup", key: "home.setup.check_school" },
  { path: "/registry/staff", key: "home.setup.staff" },
  { path: "/registry/admit", key: "home.setup.students" },
  { path: "/imports", key: "home.setup.import" },
  { path: "/timetable/editor", key: "home.setup.timetable" },
  { path: "/fees/setup", key: "home.setup.fees" },
  { path: "/settings/accounts", key: "home.setup.accounts" },
];

/** Paths that make up each role's day, most used first. */
const TEACHER_PATHS = [
  "/attendance",
  "/timetable/teacher",
  "/assessment/setup",
  "/performance/at-risk",
  "/notices",
];
const FAMILY_PATHS = [
  "/registry/overview",
  "/timetable/student",
  "/performance",
  "/fees/statement",
  "/files/view",
  "/library",
];
const OFFICE_PATHS = ["/fees/collect", "/registry/students", "/library/desk", "/transport"];

function pick(routes: readonly FeatureRoute[], paths: readonly string[]): FeatureRoute[] {
  return paths
    .map((path) => routes.find((route) => route.path === path))
    .filter((route): route is FeatureRoute => route !== undefined);
}

export function HomePage() {
  const { t } = useLanguage();
  const { status, session, actions } = useSession();
  const schoolName = session?.school_name ?? null;

  if (status !== "authenticated" || session === null) {
    return null;
  }

  const routes = navigationRoutes(REGISTERED_MODULES).filter(
    (route) => !route.path.startsWith("/demo") && can(actions, route.requiredPermission),
  );
  const setup = SETUP_STEPS.filter((step) => routes.some((route) => route.path === step.path));
  const everyday = [
    ...pick(routes, TEACHER_PATHS),
    ...pick(routes, OFFICE_PATHS),
    ...pick(routes, FAMILY_PATHS),
  ].filter((route, index, all) => all.findIndex((other) => other.path === route.path) === index);

  return (
    <section className="home">
      <h2 data-testid="signed-in">{schoolName ?? t("home.title")}</h2>
      {setup.length >= 3 ? (
        <>
          <h3>{t("home.setup.title")}</h3>
          <ol className="home-links setup-steps">
            {setup.map((step) => (
              <li key={step.path}>
                <Link to={step.path}>{t(step.key)}</Link>
              </li>
            ))}
          </ol>
        </>
      ) : null}
      {everyday.length > 0 ? (
        <>
          <h3>{t("home.everyday")}</h3>
          <ul className="home-links">
            {everyday.slice(0, 8).map((route) => (
              <li key={route.path}>
                <Link to={route.path}>{t(route.navLabelKey ?? route.path)}</Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {setup.length < 3 && everyday.length === 0 ? <p>{t("home.nothing")}</p> : null}
    </section>
  );
}
