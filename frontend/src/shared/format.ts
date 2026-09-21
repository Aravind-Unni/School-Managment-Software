/**
 * Display formatting shared by every screen. Money is stored in paise; people
 * read rupees. Dates are stored as ISO; people read "22 Sep 2026".
 */

const RUPEES = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});

/** 1100000 paise -> "₹11,000". */
export function rupees(paise: number | null | undefined): string {
  if (paise === null || paise === undefined || Number.isNaN(paise)) return "—";
  return RUPEES.format(paise / 100);
}

/** "₹ 11,000.50" typed by a person -> paise, or null when it is not a number. */
export function paiseFromRupees(text: string): number | null {
  const cleaned = text.replace(/[₹,\s]/g, "");
  if (cleaned === "" || !/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  return Math.round(Number(cleaned) * 100);
}

/** "2026-09-22" -> "22 Sep 2026" in the reader's language. */
export function shortDate(iso: string | null | undefined, language = "en"): string {
  if (!iso) return "—";
  const date = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(language === "ml" ? "ml-IN" : "en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

/** Percentage of part in whole, rounded, or null when there is no whole. */
export function percent(part: number, whole: number): number | null {
  if (!whole) return null;
  return Math.round((part / whole) * 100);
}
