import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { navigationRoutes, validateModule, type FeatureModule } from "@app/moduleRegistry";
import { REGISTERED_MODULES } from "@app/registeredModules";
import { DEMO_PERMISSIONS, demoModule } from "@features/demo/module";

describe("module registry", () => {
  it("registers every implemented module when none is selected", () => {
    // A standalone build sets VITE_SCHOOL_MODULE_ID to serve one module; with no
    // selection (the integrated case) every implemented module is registered.
    expect(REGISTERED_MODULES.map((module) => module.id)).toEqual([
      "M00",
      "M01",
      "M03",
      "M04",
      "M05",
      "M06",
      "M07",
      "M08",
      "M09",
      "M10",
      "M11",
      "M12",
      "M13",
    ]);
  });

  it("every registered module declares a valid shape", () => {
    for (const module of REGISTERED_MODULES) {
      expect(() => validateModule(module)).not.toThrow();
    }
  });

  it("builds navigation from each feature's own metadata", () => {
    const routes = navigationRoutes(REGISTERED_MODULES);
    expect(routes.map((route) => route.navLabelKey)).toEqual([
      "nav.demo",
      "nav.security",
      "nav.roles",
      "nav.timetable_editor",
      "nav.timetable_substitutions",
      "nav.timetable_class",
      "nav.timetable_teacher",
      "nav.timetable_student",
      "nav.attendance",
      "nav.assessment_setup",
      "nav.assessment_results",
      "nav.performance_dashboard",
      "nav.performance_at_risk",
      "nav.performance_interventions",
      "nav.fees_setup",
      "nav.fees_statement",
      "nav.fees_collect",
      "nav.fees_overdue",
      "nav.fees_concessions",
      "nav.transport",
      "nav.transport_billing",
      "nav.library",
      "nav.library_desk",
      "nav.library_overdues",
      "nav.alumni_candidates",
      "nav.alumni_directory",
      "nav.alumni_profile",
      "nav.alumni_export",
      "nav.notices",
      "nav.templates",
      "nav.deliveries",
      "nav.files_review",
      "nav.files_view",
      "nav.imports",
      "nav.exports",
      "nav.reports",
      "nav.report_cards",
    ]);
  });

  it("omits routes that carry no nav label", () => {
    // Login is reached when unauthenticated, not chosen from a menu.
    const paths = navigationRoutes(REGISTERED_MODULES).map((route) => route.path);
    expect(paths).not.toContain("/login");
  });

  it.each([
    ["an id outside M00..M14", { ...demoModule, id: "M99" }],
    ["a mismatched api prefix", { ...demoModule, apiPrefix: "/api/other/" }],
  ])("rejects %s", (_label, broken) => {
    expect(() => validateModule(broken as FeatureModule)).toThrow();
  });

  it("rejects a route requiring a permission outside the module's prefixes", () => {
    // Ownership is declared as prefixes now, matching the backend registration.
    expect(() =>
      validateModule({
        ...demoModule,
        routes: [{ path: "/demo", component: () => null, requiredPermission: "fees.read_invoice" }],
      }),
    ).toThrow(/owned/);
  });

  it("accepts a multi-segment permission inside a declared prefix", () => {
    expect(() =>
      validateModule({
        id: "M01",
        slug: "access",
        apiPrefix: "/api/v1/",
        permissionPrefixes: ["auth."],
        routes: [
          {
            path: "/settings/security",
            component: () => null,
            requiredPermission: "auth.factor.manage_self",
          },
        ],
      }),
    ).not.toThrow();
  });

  it("rejects a relative route path", () => {
    expect(() =>
      validateModule({ ...demoModule, routes: [{ path: "demo", component: () => null }] }),
    ).toThrow(/absolute/);
  });

  it("declares the same permission codes as the backend registration", () => {
    // The two sides are written separately, so this asserts they agree rather
    // than assuming it. A rename on one side fails here.
    // Resolved from the Vitest root (frontend/), not from import.meta.url:
    // under the jsdom environment import.meta.url is not a file: URL.
    const backend = readFileSync(
      resolve(process.cwd(), "../backend/modules/demo/registration.py"),
      "utf8",
    );
    for (const code of Object.values(DEMO_PERMISSIONS)) {
      expect(backend).toContain(`"${code}"`);
    }
    expect(backend).toContain('api_prefix="/api/demo/"');
  });

  it("uses the same api prefix as the backend registration", () => {
    expect(demoModule.apiPrefix).toBe("/api/demo/");
  });
});
