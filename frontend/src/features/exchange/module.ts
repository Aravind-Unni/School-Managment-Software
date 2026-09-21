/**
 * M13 exchange frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { ExportCentrePage } from "./ExportCentrePage";
import { ImportCentrePage } from "./ImportCentrePage";
import { ReportCardPreviewPage } from "./ReportCardPreviewPage";
import { ReportCentrePage } from "./ReportCentrePage";

export const EXCHANGE_PERMISSIONS = {
  importsValidate: "imports.validate",
  importsCommit: "imports.commit",
  reportsRead: "reports.read",
  reportsExport: "reports.export",
  reportCardsGenerate: "reportcards.generate",
} as const;

export const exchangeModule: FeatureModule = {
  id: "M13",
  slug: "exchange",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["imports.", "reports.", "reportcards."],
  routes: [
    {
      path: "/imports",
      component: ImportCentrePage,
      navLabelKey: "nav.imports",
      requiredPermission: EXCHANGE_PERMISSIONS.importsValidate,
    },
    {
      path: "/exports",
      component: ExportCentrePage,
      navLabelKey: "nav.exports",
      requiredPermission: EXCHANGE_PERMISSIONS.reportsExport,
    },
    {
      path: "/reports",
      component: ReportCentrePage,
      navLabelKey: "nav.reports",
      requiredPermission: EXCHANGE_PERMISSIONS.reportsRead,
    },
    {
      path: "/report-cards",
      component: ReportCardPreviewPage,
      navLabelKey: "nav.report_cards",
      requiredPermission: EXCHANGE_PERMISSIONS.reportCardsGenerate,
    },
  ],
};
