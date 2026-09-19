/**
 * M01 access frontend declaration.
 *
 * Mirrors backend/modules/access/registration.py. A test asserts the permission codes
 * and api prefix agree, so a rename on one side cannot silently drift from the other.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { LoginPage } from "./LoginPage";
import { RoleEditorPage } from "./RoleEditorPage";
import { SecuritySettingsPage } from "./SecuritySettingsPage";

export const ACCESS_PERMISSIONS = {
  rolesManage: "roles.manage",
  rolesDelegate: "roles.delegate",
  accountsManage: "accounts.manage",
  factorManageSelf: "auth.factor.manage_self",
  factorResetOther: "auth.factor.reset_other",
} as const;

export const accessModule: FeatureModule = {
  id: "M01",
  slug: "access",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["auth.", "roles.", "accounts."],
  routes: [
    // Login carries no nav label: it is reached when unauthenticated, not chosen.
    { path: "/login", component: LoginPage },
    {
      path: "/settings/security",
      component: SecuritySettingsPage,
      navLabelKey: "nav.security",
      requiredPermission: ACCESS_PERMISSIONS.factorManageSelf,
    },
    {
      path: "/settings/roles",
      component: RoleEditorPage,
      navLabelKey: "nav.roles",
      requiredPermission: ACCESS_PERMISSIONS.rolesManage,
    },
  ],
};
