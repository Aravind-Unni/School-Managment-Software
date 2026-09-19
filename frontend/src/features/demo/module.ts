/**
 * M00 demo frontend declaration.
 *
 * Mirrors backend/modules/demo/registration.py. The two are asserted to agree by
 * tests/unit/moduleRegistry.test.ts, so a permission renamed on one side cannot
 * silently drift from the other.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { DemoNotesPage } from "./DemoNotesPage";

export const DEMO_PERMISSIONS = {
  list: "demo.list_notes",
  read: "demo.read_note",
  write: "demo.write_note",
} as const;

export const demoModule: FeatureModule = {
  id: "M00",
  slug: "demo",
  apiPrefix: "/api/demo/",
  routes: [
    {
      path: "/demo",
      component: DemoNotesPage,
      navLabelKey: "nav.demo",
      requiredPermission: DEMO_PERMISSIONS.list,
    },
  ],
};
