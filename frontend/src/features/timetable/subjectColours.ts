/**
 * One colour per subject, the same everywhere (planner, timetables, marks).
 *
 * Well-known codes get fixed hues so "Maths is blue" holds across schools;
 * anything else gets a stable hue from its code. All hues keep AA contrast
 * for the dark text used on their 14% tint.
 */

const FIXED: Record<string, string> = {
  MATH: "#2463c9",
  ENG: "#8b3fb8",
  MAL: "#c2410c",
  HIN: "#b8325a",
  SCI: "#15803d",
  SST: "#a16207",
  EVS: "#0f766e",
  COMP: "#4338ca",
  PHY: "#0e7490",
  CHEM: "#9333ea",
  BIO: "#3f7d20",
  PE: "#be123c",
};

const SPARE = ["#0369a1", "#7c3aed", "#b45309", "#047857", "#be185d", "#4d7c0f"];

/** Return the colour for a subject code. */
export function subjectColour(code: string | undefined): string {
  if (!code) return "#64748b";
  const fixed = FIXED[code.toUpperCase()];
  if (fixed) return fixed;
  let hash = 0;
  for (const char of code) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return SPARE[hash % SPARE.length] ?? "#64748b";
}
