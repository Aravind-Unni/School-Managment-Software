/**
 * M03 timetable frontend declaration.
 *
 * Mirrors backend/modules/timetable/registration.py. A test asserts the permission
 * codes and api prefix agree, so a rename on one side cannot silently drift from
 * the other.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { ClassSchedulePage } from "./ClassSchedulePage";
import { StudentSchedulePage } from "./StudentSchedulePage";
import { SubstitutionPage } from "./SubstitutionPage";
import { TeacherSchedulePage } from "./TeacherSchedulePage";
import { WeeklyEditorPage } from "./WeeklyEditorPage";

export const TIMETABLE_PERMISSIONS = {
  read: "timetable.read",
  readSection: "timetable.read_section",
  readTeacher: "timetable.read_teacher",
  readStudent: "timetable.read_student",
  edit: "timetable.edit",
  publish: "timetable.publish",
  substitute: "timetable.substitute",
} as const;

export const timetableModule: FeatureModule = {
  id: "M03",
  slug: "timetable",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["timetable."],
  routes: [
    {
      path: "/timetable/editor",
      component: WeeklyEditorPage,
      navLabelKey: "nav.timetable_editor",
      requiredPermission: TIMETABLE_PERMISSIONS.edit,
    },
    {
      path: "/timetable/substitutions",
      component: SubstitutionPage,
      navLabelKey: "nav.timetable_substitutions",
      requiredPermission: TIMETABLE_PERMISSIONS.substitute,
    },
    {
      path: "/timetable/class",
      component: ClassSchedulePage,
      navLabelKey: "nav.timetable_class",
      requiredPermission: TIMETABLE_PERMISSIONS.readSection,
    },
    {
      path: "/timetable/teacher",
      component: TeacherSchedulePage,
      navLabelKey: "nav.timetable_teacher",
      requiredPermission: TIMETABLE_PERMISSIONS.readTeacher,
    },
    {
      path: "/timetable/student",
      component: StudentSchedulePage,
      navLabelKey: "nav.timetable_student",
      requiredPermission: TIMETABLE_PERMISSIONS.readStudent,
    },
  ],
};
