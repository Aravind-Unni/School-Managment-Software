/**
 * The application shell: session, language, grouped navigation, routed outlet.
 *
 * Contains no business logic. Features declare their own routes; the shell
 * filters navigation by the caller's held action codes from /auth/capabilities.
 */

import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import { LanguageProvider, useLanguage } from "@shared/i18n/LanguageContext";
import { LANGUAGES, type Language } from "@shared/i18n/messages";
import { REGISTERED_MODULES } from "./registeredModules";
import { navigationRoutes, type FeatureRoute } from "./moduleRegistry";
import { SessionProvider, can, useSession } from "./SessionContext";
import { HomePage } from "./HomePage";
import "./shell.css";

/** Product navigation groups — school staff should not see a flat dump. */
const startsWithAny = (path: string, prefixes: readonly string[]) =>
  prefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));

const NAV_GROUPS: readonly { readonly id: string; readonly label: string; readonly match: (path: string) => boolean }[] = [
  {
    id: "people",
    label: "People",
    match: (path) => startsWithAny(path, ["/registry", "/alumni"]),
  },
  {
    id: "academics",
    label: "Academics",
    match: (path) =>
      startsWithAny(path, ["/timetable", "/attendance", "/assessment", "/performance"]),
  },
  {
    id: "fees",
    label: "Fees & transport",
    match: (path) => startsWithAny(path, ["/fees", "/transport"]),
  },
  {
    id: "library",
    label: "Library",
    match: (path) => startsWithAny(path, ["/library"]),
  },
  {
    id: "comms",
    label: "Communications",
    match: (path) =>
      startsWithAny(path, ["/communications", "/notices", "/templates", "/deliveries", "/files"]),
  },
  {
    id: "reports",
    label: "Reports & data",
    match: (path) =>
      startsWithAny(path, ["/exchange", "/reports", "/report-cards", "/exports"]),
  },
  {
    id: "admin",
    label: "Admin",
    match: (path) => startsWithAny(path, ["/settings", "/platform"]),
  },
];

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

function visibleRoutes(actions: ReadonlySet<string>): FeatureRoute[] {
  return navigationRoutes(REGISTERED_MODULES).filter((route) => {
    // Demo is foundation regression only — never school chrome.
    if (route.path.startsWith("/demo")) {
      return false;
    }
    return can(actions, route.requiredPermission);
  });
}

function Navigation({ onNavigate }: { readonly onNavigate: () => void }) {
  const { t } = useLanguage();
  const { actions } = useSession();
  const routes = visibleRoutes(actions);
  return (
    <nav aria-label="Main" className="product-nav">
      {NAV_GROUPS.map((group) => {
        const items = routes.filter((route) => group.match(route.path));
        if (items.length === 0) {
          return null;
        }
        return (
          <div key={group.id} className="nav-group">
            <p className="nav-group-label">{group.label}</p>
            <ul>
              {items.map((route) => (
                <li key={route.path}>
                  <NavLink to={route.path} end onClick={onNavigate}>
                    {t(route.navLabelKey ?? route.path)}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

function SessionControls() {
  const { status, session, signOut } = useSession();
  if (status !== "authenticated") {
    return null;
  }
  return (
    <>
      {session?.display_name ? (
        <span className="signed-in-name" title={session.login_name ?? undefined}>
          {session.display_name}
        </span>
      ) : null}
      <button type="button" className="secondary" onClick={() => void signOut()}>
        Sign out
      </button>
    </>
  );
}

function NotFound() {
  const { t } = useLanguage();
  return <p role="status">{t("error.object_inaccessible")}</p>;
}

function RequireAuth({ children }: { readonly children: ReactNode }) {
  const { status } = useSession();
  const location = useLocation();
  if (status === "loading") {
    return <p role="status">Loading…</p>;
  }
  if (status === "anonymous" && location.pathname !== "/login") {
    // Preserve destination so denied journeys land on login with a visible status.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (status === "authenticated" && location.pathname === "/login") {
    return <Navigate to="/" replace />;
  }
  return children;
}

/** The shell, without the router (so tests can supply their own). */
export function AppShell() {
  return (
    <LanguageProvider>
      <SessionProvider>
        <RequireAuth>
          <Frame />
        </RequireAuth>
      </SessionProvider>
    </LanguageProvider>
  );
}

/** Sidebar + top bar + routed page. The sidebar is a drawer on phones. */
function Frame() {
  const { status, session } = useSession();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const signedIn = status === "authenticated" && location.pathname !== "/login";
  const schoolName = session?.school_name ?? "School";

  useEffect(() => {
    if (!navOpen) return undefined;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [navOpen]);

  return (
    <div className={`app${signedIn ? "" : " signed-out"}${navOpen ? " nav-open" : ""}`}>
      {signedIn ? (
        <aside className="sidebar" id="main-navigation">
          <Link className="brand" to="/" onClick={() => setNavOpen(false)}>
            {schoolName}
            <small>School management</small>
          </Link>
          <Navigation onNavigate={() => setNavOpen(false)} />
          <div className="sidebar-footer">
            <SessionControls />
          </div>
        </aside>
      ) : null}
      {signedIn ? (
        <div className="scrim" aria-hidden="true" onClick={() => setNavOpen(false)} />
      ) : null}
      <div className="main-column">
        {signedIn ? (
          <header className="topbar">
            <button
              type="button"
              className="secondary menu-button"
              aria-controls="main-navigation"
              aria-expanded={navOpen}
              onClick={() => setNavOpen((open) => !open)}
            >
              Menu
            </button>
            <span className="school-name">{schoolName}</span>
            <span className="spacer" />
            <LanguageSwitch />
          </header>
        ) : null}
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginRoute />} />
            {REGISTERED_MODULES.flatMap((module) =>
              module.routes.map((route) => (
                <Route key={route.path} path={route.path} element={<route.component />} />
              )),
            )}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function LoginRoute() {
  // Lazy import keeps login page as the registered module component.
  const LoginPage = REGISTERED_MODULES.flatMap((m) => m.routes).find(
    (r) => r.path === "/login",
  )?.component;
  if (LoginPage === undefined) {
    return <p role="alert">Login is not registered</p>;
  }
  return <LoginPage />;
}

export default AppShell;
