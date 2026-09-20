/**
 * M08 transport frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { TransportBillingPage } from "./TransportBillingPage";
import { TransportParticipantsPage } from "./TransportParticipantsPage";

export const TRANSPORT_PERMISSIONS = {
  manage: "transport.manage",
  read: "transport.read",
  bill: "transport.bill",
} as const;

export const transportModule: FeatureModule = {
  id: "M08",
  slug: "transport",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["transport."],
  routes: [
    {
      path: "/transport",
      component: TransportParticipantsPage,
      navLabelKey: "nav.transport",
      requiredPermission: TRANSPORT_PERMISSIONS.read,
    },
    {
      path: "/transport/billing",
      component: TransportBillingPage,
      navLabelKey: "nav.transport_billing",
      requiredPermission: TRANSPORT_PERMISSIONS.bill,
    },
  ],
};
