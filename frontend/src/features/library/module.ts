/**
 * M09 library frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { LibraryCataloguePage } from "./LibraryCataloguePage";
import { LibraryDeskPage } from "./LibraryDeskPage";
import { LibraryOverduesPage } from "./LibraryOverduesPage";

export const LIBRARY_PERMISSIONS = {
  catalogueManage: "library.catalogue.manage",
  issue: "library.issue",
  return: "library.return",
  renew: "library.renew",
  readOverdues: "library.read_overdues",
  readOwn: "library.read_own",
} as const;

export const libraryModule: FeatureModule = {
  id: "M09",
  slug: "library",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["library."],
  routes: [
    {
      path: "/library",
      component: LibraryCataloguePage,
      navLabelKey: "nav.library",
      requiredPermission: LIBRARY_PERMISSIONS.readOwn,
    },
    {
      path: "/library/desk",
      component: LibraryDeskPage,
      navLabelKey: "nav.library_desk",
      requiredPermission: LIBRARY_PERMISSIONS.issue,
    },
    {
      path: "/library/overdues",
      component: LibraryOverduesPage,
      navLabelKey: "nav.library_overdues",
      requiredPermission: LIBRARY_PERMISSIONS.readOverdues,
    },
  ],
};
