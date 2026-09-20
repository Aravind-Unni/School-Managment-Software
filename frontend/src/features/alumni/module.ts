/**
 * M10 alumni frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AlumniCandidatesPage } from "./AlumniCandidatesPage";
import { AlumniDirectoryPage } from "./AlumniDirectoryPage";
import { AlumniExportPage } from "./AlumniExportPage";
import { AlumniProfilePage } from "./AlumniProfilePage";

export const ALUMNI_PERMISSIONS = {
  review: "alumni.review",
  manage: "alumni.manage",
  read: "alumni.read",
  export: "alumni.export",
  contactSelf: "alumni.contact_self",
} as const;

export const alumniModule: FeatureModule = {
  id: "M10",
  slug: "alumni",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["alumni."],
  routes: [
    {
      path: "/alumni/candidates",
      component: AlumniCandidatesPage,
      navLabelKey: "nav.alumni_candidates",
      requiredPermission: ALUMNI_PERMISSIONS.review,
    },
    {
      path: "/alumni",
      component: AlumniDirectoryPage,
      navLabelKey: "nav.alumni_directory",
      requiredPermission: ALUMNI_PERMISSIONS.read,
    },
    {
      path: "/alumni/profile",
      component: AlumniProfilePage,
      navLabelKey: "nav.alumni_profile",
      requiredPermission: ALUMNI_PERMISSIONS.manage,
    },
    {
      path: "/alumni/export",
      component: AlumniExportPage,
      navLabelKey: "nav.alumni_export",
      requiredPermission: ALUMNI_PERMISSIONS.export,
    },
  ],
};
