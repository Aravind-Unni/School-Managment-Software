/**
 * M05 assessment frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AssessmentsPage } from "./AssessmentsPage";
import { MarkingPage } from "./MarkingPage";
import { MarkingGridPage } from "./MarkingGridPage";
import { PublishPreviewPage } from "./PublishPreviewPage";
import { PublishedResultPage } from "./PublishedResultPage";
import { ExamResultsPage } from "@features/registry/ExamResultsPage";

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
      path: "/assessment/results",
      forFamilies: true,
      component: ExamResultsPage,
      navLabelKey: "nav.exam_results",
      requiredPermission: "evidence.view",
    },
    {
      path: "/assessment/setup",
      component: AssessmentsPage,
      navLabelKey: "nav.assessment_setup",
      requiredPermission: ASSESSMENT_PERMISSIONS.manage,
    },
    {
      path: "/assessment/:assessmentId/marking",
      component: MarkingPage,
      requiredPermission: ASSESSMENT_PERMISSIONS.evidenceView,
    },
    {
      path: "/assessment/:assessmentId/evidence",
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
