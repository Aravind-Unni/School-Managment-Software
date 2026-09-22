/**
 * The Originator mark: a plain square carrying a letter O. Institutional and
 * quiet, like an examination board's seal; drawn inline so it is crisp at any
 * size. ``onDark`` inverts it for the navy sidebar.
 */

export const PRODUCT_NAME = "Originator";

export function OriginatorMark({ size = 32, onDark = false }: { readonly size?: number; readonly onDark?: boolean }) {
  const ground = onDark ? "#FFFFFF" : "#1E4E8C";
  const letter = onDark ? "#1E4E8C" : "#FFFFFF";
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false" className="originator-mark">
      <rect width="64" height="64" rx="4" fill={ground} />
      <circle cx="32" cy="32" r="15" fill="none" stroke={letter} strokeWidth="7" />
    </svg>
  );
}
