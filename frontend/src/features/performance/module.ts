/**
 * M06 performance frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AtRiskListPage } from "./AtRiskListPage";
import { InterventionListPage } from "./InterventionListPage";
import { StudentDashboardPage } from "./StudentDashboardPage";

export const PERFORMANCE_PERMISSIONS = {
  read: "performance.read",
  warnings: "warnings.manage",
  interventions: "interventions.manage",
  meetings: "meetings.record",
  observations: "observations.read_sensitive",
} as const;

export const performanceModule: FeatureModule = {
  id: "M06",
  slug: "performance",
  apiPrefix: "/api/v1/",
  permissionPrefixes: [
    "performance.",
    "warnings.",
    "interventions.",
    "meetings.",
    "observations.",
  ],
  routes: [
    {
      path: "/performance",
      component: StudentDashboardPage,
      navLabelKey: "nav.performance_dashboard",
      requiredPermission: PERFORMANCE_PERMISSIONS.read,
    },
    {
      path: "/performance/at-risk",
      component: AtRiskListPage,
      navLabelKey: "nav.performance_at_risk",
      requiredPermission: PERFORMANCE_PERMISSIONS.warnings,
    },
    {
      path: "/performance/interventions",
      component: InterventionListPage,
      navLabelKey: "nav.performance_interventions",
      requiredPermission: PERFORMANCE_PERMISSIONS.interventions,
    },
  ],
};
