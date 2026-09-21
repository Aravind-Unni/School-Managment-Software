/**
 * M02 registry frontend declaration.
 *
 * Mirrors backend/modules/registry/registration.py route paths and permissions.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { SchoolSetupPage } from "./SchoolSetupPage";
import { StudentDirectoryPage } from "./StudentDirectoryPage";
import { StudentProfilePage } from "./StudentProfilePage";

export const REGISTRY_PERMISSIONS = {
  manage: "registry.manage",
  studentsRead: "students.read",
} as const;

export const registryModule: FeatureModule = {
  id: "M02",
  slug: "registry",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["registry.", "students.", "guardians.", "staff.", "year."],
  routes: [
    {
      path: "/registry/setup",
      component: SchoolSetupPage,
      navLabelKey: "nav.registry_setup",
      requiredPermission: REGISTRY_PERMISSIONS.manage,
    },
    {
      path: "/registry/students",
      component: StudentDirectoryPage,
      navLabelKey: "nav.students",
      requiredPermission: REGISTRY_PERMISSIONS.studentsRead,
    },
    {
      path: "/registry/students/:studentId",
      component: StudentProfilePage,
      requiredPermission: REGISTRY_PERMISSIONS.studentsRead,
    },
  ],
};
