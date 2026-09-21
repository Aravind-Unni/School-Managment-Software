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
      navLabelKey: "nav.files_review",
      requiredPermission: FILES_PERMISSIONS.reviewQuality,
    },
    {
      path: "/files/view",
      component: ParentFileViewerPage,
      navLabelKey: "nav.files_view",
      requiredPermission: FILES_PERMISSIONS.read,
    },
  ],
};
