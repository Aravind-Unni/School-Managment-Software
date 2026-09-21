/**
 * M02 registry frontend declaration.
 *
 * Mirrors backend/modules/registry/registration.py route paths and permissions.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AdmitStudentPage } from "./AdmitStudentPage";
import { ImportStudentsPage } from "./ImportStudentsPage";
import { SchoolSetupPage } from "./SchoolSetupPage";
import { StaffAdminPage } from "./StaffAdminPage";
import { StudentOverviewPage } from "./StudentOverviewPage";
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
      path: "/registry/overview",
      component: StudentOverviewPage,
      navLabelKey: "nav.student_overview",
      requiredPermission: REGISTRY_PERMISSIONS.studentsRead,
    },
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
      path: "/registry/admit",
      component: AdmitStudentPage,
      navLabelKey: "nav.admit",
      requiredPermission: REGISTRY_PERMISSIONS.manage,
    },
    {
      path: "/registry/import",
      component: ImportStudentsPage,
      navLabelKey: "nav.import_students",
      requiredPermission: REGISTRY_PERMISSIONS.manage,
    },
    {
      path: "/registry/staff",
      component: StaffAdminPage,
      navLabelKey: "nav.staff",
      requiredPermission: REGISTRY_PERMISSIONS.manage,
    },
    {
      path: "/registry/students/:studentId",
      component: StudentProfilePage,
      requiredPermission: REGISTRY_PERMISSIONS.studentsRead,
    },
  ],
};
