/**
 * The Originator mark: a ring (the school's whole year, going round) with
 * one marked point where something starts. Drawn inline so it is crisp at any
 * size and needs no request. ``onDark`` drops the tile for navy backgrounds.
 */

export const PRODUCT_NAME = "Originator";

export function OriginatorMark({ size = 32, onDark = false }: { readonly size?: number; readonly onDark?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false" className="originator-mark">
      {onDark ? null : <rect width="64" height="64" rx="15" fill="#1E4E8C" />}
      <circle cx="30" cy="34" r="15" fill="none" stroke="#FFFFFF" strokeWidth="8" />
      <circle cx="40.6" cy="23.4" r="8.5" fill="#E8A317" stroke="#1E4E8C" strokeWidth="3.5" />
    </svg>
  );
}
