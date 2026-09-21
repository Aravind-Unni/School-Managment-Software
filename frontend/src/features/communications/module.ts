/**
 * M11 communications frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { DeliveryDashboardPage } from "./DeliveryDashboardPage";
import { NoticeComposerPage } from "./NoticeComposerPage";
import { TemplateEditorPage } from "./TemplateEditorPage";

export const COMMUNICATIONS_PERMISSIONS = {
  noticesCreate: "notices.create",
  noticesPublish: "notices.publish",
  messagesSend: "messages.send",
  messagesReadStatus: "messages.read_status",
  smsConfigure: "sms.configure",
} as const;

export const communicationsModule: FeatureModule = {
  id: "M11",
  slug: "communications",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["notices.", "messages.", "sms."],
  routes: [
    {
      path: "/notices",
      component: NoticeComposerPage,
      navLabelKey: "nav.notices",
      requiredPermission: COMMUNICATIONS_PERMISSIONS.noticesCreate,
    },
    {
      path: "/templates",
      component: TemplateEditorPage,
      navLabelKey: "nav.templates",
      requiredPermission: COMMUNICATIONS_PERMISSIONS.messagesSend,
    },
    {
      path: "/deliveries",
      component: DeliveryDashboardPage,
      navLabelKey: "nav.deliveries",
      requiredPermission: COMMUNICATIONS_PERMISSIONS.messagesReadStatus,
    },
  ],
};
