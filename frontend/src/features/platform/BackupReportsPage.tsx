/** Backup and restore rehearsal reports for company ops. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { createRestoreRehearsal, type RestoreRehearsal } from "./api";

export function BackupReportsPage() {
  const { t } = useLanguage();
  const [manifestId, setManifestId] = useState("");
  const [targetLabel, setTargetLabel] = useState("");
  const [rehearsal, setRehearsal] = useState<RestoreRehearsal | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setErrorKey(null);
    setRehearsal(null);
    try {
      setRehearsal(
        await createRestoreRehearsal({
          backup_manifest_id: manifestId.trim(),
          isolated_target_label: targetLabel.trim(),
        }),
      );
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>{t("platform.backups_title")}</h1>
      <p>{t("platform.backups_help")}</p>
      <label>
        {t("platform.backup_manifest_id")}
        <input value={manifestId} onChange={(event) => setManifestId(event.target.value)} />
      </label>
      <label>
        {t("platform.isolated_target_label")}
        <input value={targetLabel} onChange={(event) => setTargetLabel(event.target.value)} />
      </label>
      <button aria-busy={busy}
        type="button"
        disabled={busy || manifestId.trim().length === 0 || targetLabel.trim().length === 0}
        onClick={() => void submit()}
      >
        {busy ? t("ui.loading") : t("platform.start_rehearsal")}
      </button>
      {rehearsal === null && errorKey === null && !busy && (
        <p role="status">{t("platform.backups_empty")}</p>
      )}
      {rehearsal !== null && (
        <p role="status">
          {t("platform.rehearsal_created")}: {rehearsal.id} · {rehearsal.state}
        </p>
      )}
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
        </div>
      )}
    </section>
  );
}
