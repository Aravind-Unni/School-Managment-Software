/**
 * The modules this build serves.
 *
 * A standalone profile serves ONE module, so VITE_SCHOOL_MODULE_ID selects it. With
 * no selection every implemented module is registered, which is what an integrated
 * build wants.
 */

import { accessModule } from "@features/access/module";
import { attendanceModule } from "@features/attendance/module";
import { demoModule } from "@features/demo/module";
import { timetableModule } from "@features/timetable/module";
import { validateModule, type FeatureModule } from "./moduleRegistry";

const ALL: readonly FeatureModule[] = [
  demoModule,
  accessModule,
  timetableModule,
  attendanceModule,
].map(validateModule);

const selected = (import.meta.env as Record<string, string | undefined>)[
  "VITE_SCHOOL_MODULE_ID"
];

export const REGISTERED_MODULES: readonly FeatureModule[] =
  selected === undefined || selected === ""
    ? ALL
    : ALL.filter((module) => module.id === selected.toUpperCase());
