/**
 * M04 attendance frontend declaration.
 */

import type { FeatureModule } from "@app/moduleRegistry";
import { AttendanceSessionPage } from "./AttendanceSessionPage";
import { AttendanceTodayPage } from "./AttendanceTodayPage";
import { AttendanceRecordPage } from "@features/registry/AttendanceRecordPage";

export const ATTENDANCE_PERMISSIONS = {
  read: "attendance.read",
  mark: "attendance.mark",
  submit: "attendance.submit",
  correct: "attendance.correct",
} as const;

export const attendanceModule: FeatureModule = {
  id: "M04",
  slug: "attendance",
  apiPrefix: "/api/v1/",
  permissionPrefixes: ["attendance."],
  routes: [
    {
      path: "/attendance/record",
      forFamilies: true,
      component: AttendanceRecordPage,
      navLabelKey: "nav.attendance_record",
      requiredPermission: "attendance.read",
    },
    {
      path: "/attendance",
      component: AttendanceTodayPage,
      navLabelKey: "nav.attendance",
      requiredPermission: ATTENDANCE_PERMISSIONS.read,
    },
    {
      path: "/attendance/session/:sessionId",
      component: AttendanceSessionPage,
      requiredPermission: ATTENDANCE_PERMISSIONS.mark,
    },
  ],
};
