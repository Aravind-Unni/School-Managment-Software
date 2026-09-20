/**
 * M05 assessment frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AssessmentSetupPage } from "./AssessmentSetupPage";
import { MarkingGridPage } from "./MarkingGridPage";
import { PublishPreviewPage } from "./PublishPreviewPage";
import { PublishedResultPage } from "./PublishedResultPage";

export const ASSESSMENT_PERMISSIONS = {
  manage: "assessment.manage",
  edit: "marks.edit",
  submit: "marks.submit",
  approve: "results.approve",
  publish: "results.publish",
  reopen: "results.reopen",
  evidenceView: "evidence.view",
} as const;

export const assessmentModule: FeatureModule = {
  id: "M05",
  slug: "assessment",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["assessment.", "marks.", "results.", "evidence."],
  routes: [
    {
      path: "/assessment/setup",
      component: AssessmentSetupPage,
      navLabelKey: "nav.assessment_setup",
      requiredPermission: ASSESSMENT_PERMISSIONS.manage,
    },
    {
      path: "/assessment/:assessmentId/marking",
      component: MarkingGridPage,
      requiredPermission: ASSESSMENT_PERMISSIONS.edit,
    },
    {
      path: "/assessment/:assessmentId/publish",
      component: PublishPreviewPage,
      requiredPermission: ASSESSMENT_PERMISSIONS.publish,
    },
    {
      path: "/assessment/results/:resultId",
      component: PublishedResultPage,
      navLabelKey: "nav.assessment_results",
      requiredPermission: ASSESSMENT_PERMISSIONS.evidenceView,
    },
  ],
};
