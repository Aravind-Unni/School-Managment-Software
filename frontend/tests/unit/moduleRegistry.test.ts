import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { navigationRoutes, validateModule, type FeatureModule } from "@app/moduleRegistry";
import { REGISTERED_MODULES } from "@app/registeredModules";
import { DEMO_PERMISSIONS, demoModule } from "@features/demo/module";

describe("module registry", () => {
  it("registers exactly one module in a standalone build", () => {
    expect(REGISTERED_MODULES).toHaveLength(1);
    expect(REGISTERED_MODULES[0]?.id).toBe("M00");
  });

  it("builds navigation from each feature's own metadata", () => {
    const routes = navigationRoutes(REGISTERED_MODULES);
    expect(routes.map((route) => route.navLabelKey)).toEqual(["nav.demo"]);
  });

  it.each([
    ["an id outside M00..M14", { ...demoModule, id: "M99" }],
    ["a mismatched api prefix", { ...demoModule, apiPrefix: "/api/other/" }],
  ])("rejects %s", (_label, broken) => {
    expect(() => validateModule(broken as FeatureModule)).toThrow();
  });

  it("rejects a route requiring another module's permission", () => {
    expect(() =>
      validateModule({
        ...demoModule,
        routes: [{ path: "/demo", component: () => null, requiredPermission: "fees.read_invoice" }],
      }),
    ).toThrow(/namespaced/);
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
