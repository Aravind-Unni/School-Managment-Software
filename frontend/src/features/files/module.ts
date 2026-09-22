/**
 * M12 files frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { FileReviewPage } from "./FileReviewPage";
import { ParentFileViewerPage } from "./ParentFileViewerPage";

export const FILES_PERMISSIONS = {
  upload: "files.upload",
  reviewQuality: "files.review_quality",
  read: "files.read",
  retentionManage: "files.retention.manage",
} as const;

export const filesModule: FeatureModule = {
  id: "M12",
  slug: "files",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["files."],
  routes: [
    {
      path: "/files/review",
      component: FileReviewPage,
      requiredPermission: FILES_PERMISSIONS.reviewQuality,
    },
    {
      path: "/files/view",
      component: ParentFileViewerPage,
      requiredPermission: FILES_PERMISSIONS.read,
    },
  ],
};
