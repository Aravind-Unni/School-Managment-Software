/**
 * The modules this build serves.
 *
 * In a standalone profile exactly one business module is present. B00 ships only
 * the M00 placeholder; a real module adds itself here when its contract is
 * frozen and its feature implemented.
 */

import { demoModule } from "@features/demo/module";
import { validateModule, type FeatureModule } from "./moduleRegistry";

export const REGISTERED_MODULES: readonly FeatureModule[] = [demoModule].map(validateModule);
