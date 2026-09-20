/**
 * M07 fees frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { FeeCollectionPage } from "./FeeCollectionPage";
import { FeeConcessionPage } from "./FeeConcessionPage";
import { FeeOverduePage } from "./FeeOverduePage";
import { FeeReceiptPage } from "./FeeReceiptPage";
import { FeeSetupPage } from "./FeeSetupPage";
import { FeeStatementPage } from "./FeeStatementPage";

export const FEES_PERMISSIONS = {
  configure: "fees.configure",
  read: "fees.read",
  recordPayment: "fees.record_payment",
  concede: "fees.concede",
  reverse: "fees.reverse_payment",
  refund: "fees.refund",
} as const;

export const feesModule: FeatureModule = {
  id: "M07",
  slug: "fees",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["fees."],
  routes: [
    {
      path: "/fees/setup",
      component: FeeSetupPage,
      navLabelKey: "nav.fees_setup",
      requiredPermission: FEES_PERMISSIONS.configure,
    },
    {
      path: "/fees/statement",
      component: FeeStatementPage,
      navLabelKey: "nav.fees_statement",
      requiredPermission: FEES_PERMISSIONS.read,
    },
    {
      path: "/fees/collect",
      component: FeeCollectionPage,
      navLabelKey: "nav.fees_collect",
      requiredPermission: FEES_PERMISSIONS.recordPayment,
    },
    {
      path: "/fees/receipt/:paymentId",
      component: FeeReceiptPage,
      requiredPermission: FEES_PERMISSIONS.read,
    },
    {
      path: "/fees/overdue",
      component: FeeOverduePage,
      navLabelKey: "nav.fees_overdue",
      requiredPermission: FEES_PERMISSIONS.read,
    },
    {
      path: "/fees/concessions",
      component: FeeConcessionPage,
      navLabelKey: "nav.fees_concessions",
      requiredPermission: FEES_PERMISSIONS.concede,
    },
  ],
};
