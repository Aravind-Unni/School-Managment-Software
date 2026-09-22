/**
 * Loading indicators: a spinner with its label for a panel or page that is
 * waiting, and the slim bar across the top of the screen while any request is
 * in flight (shown only after a moment, so quick actions do not flicker).
 */

import { useEffect, useState } from "react";
import { onRequestActivity } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";

export function Loading({ label }: { readonly label?: string }) {
  const { t } = useLanguage();
  return (
    <p role="status" className="loading">
      <span className="spinner" aria-hidden="true" />
      {label ?? t("ui.loading")}
    </p>
  );
}

export function ActivityBar() {
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => onRequestActivity(setBusy), []);

  useEffect(() => {
    if (!busy) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors request activity
      setShown(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setShown(true), 200);
    return () => window.clearTimeout(timer);
  }, [busy]);

  return <div className={`activity-bar${shown ? " on" : ""}`} aria-hidden="true" />;
}
