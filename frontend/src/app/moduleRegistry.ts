/**
 * Frontend counterpart of ModuleRegistration.
 *
 * Navigation metadata lives beside each feature, not in a central menu file, so
 * deleting a feature directory cannot leave a dangling menu entry. The app shell
 * composes whatever features are registered; in a standalone profile that is
 * exactly one.
 */

import type { ComponentType } from "react";

/** One route a module owns. */
export interface FeatureRoute {
  readonly path: string;
  readonly component: ComponentType;
  /** Message key, never literal prose: the label must translate. */
  readonly navLabelKey?: string;
  /** Permission code the backend checks. Used to hide navigation, never to authorise. */
  readonly requiredPermission?: string;
}

/** One module's frontend declaration. Mirrors the backend registration. */
export interface FeatureModule {
  readonly id: string;
  readonly slug: string;
  readonly apiPrefix: string;
  readonly routes: readonly FeatureRoute[];
}

/**
 * Validate a module declaration at startup.
 *
 * Throws rather than warning: a malformed declaration that merely warned would
 * produce an app with silently missing navigation.
 */
export function validateModule(module: FeatureModule): FeatureModule {
  if (!/^M(0[0-9]|1[0-4])$/.test(module.id)) {
    throw new Error(`module id must be M00..M14, got ${module.id}`);
  }
  if (!new RegExp(`^/api/${module.slug}/$`).test(module.apiPrefix)) {
    throw new Error(
      `apiPrefix ${module.apiPrefix} must be /api/${module.slug}/`,
    );
  }
  for (const route of module.routes) {
    if (!route.path.startsWith("/")) {
      throw new Error(`route path must be absolute, got ${route.path}`);
    }
    if (route.requiredPermission && !route.requiredPermission.startsWith(`${module.slug}.`)) {
      throw new Error(
        `permission ${route.requiredPermission} must be namespaced to ${module.slug}`,
      );
    }
  }
  return module;
}

/** Routes that should appear in navigation, in declaration order. */
export function navigationRoutes(modules: readonly FeatureModule[]): FeatureRoute[] {
  return modules.flatMap((module) =>
    module.routes.filter((route) => route.navLabelKey !== undefined),
  );
}
