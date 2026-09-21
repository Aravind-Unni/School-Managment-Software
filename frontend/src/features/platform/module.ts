/**
 * M14 platform frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AuditViewerPage } from "./AuditViewerPage";
import { BackupReportsPage } from "./BackupReportsPage";
import { OperatorJobsPage } from "./OperatorJobsPage";

export const PLATFORM_PERMISSIONS = {
  readHealth: "platform.read_health",
  jobsRead: "jobs.read",
  jobsRetry: "jobs.retry",
  auditRead: "audit.read",
  backupsManage: "backups.manage",
} as const;

export const platformModule: FeatureModule = {
  id: "M14",
  slug: "platform",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["platform.", "jobs.", "audit.", "backups."],
  routes: [
    {
      path: "/platform/jobs",
      component: OperatorJobsPage,
      navLabelKey: "nav.platform_jobs",
      requiredPermission: PLATFORM_PERMISSIONS.jobsRead,
    },
    {
      path: "/platform/audit",
      component: AuditViewerPage,
      navLabelKey: "nav.platform_audit",
      requiredPermission: PLATFORM_PERMISSIONS.auditRead,
    },
    {
      path: "/platform/backups",
      component: BackupReportsPage,
      navLabelKey: "nav.platform_backups",
      requiredPermission: PLATFORM_PERMISSIONS.backupsManage,
    },
  ],
};
