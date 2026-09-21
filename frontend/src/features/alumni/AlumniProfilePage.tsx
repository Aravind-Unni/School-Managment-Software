/** Contact fields and preference editor. */

import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { findAlumniById, patchAlumniContact, type AlumniProfile } from "./api";

type LoadState =
  | { readonly status: "idle" }
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly profile: AlumniProfile }
  | { readonly status: "error"; readonly messageKey: string }
  | { readonly status: "missing" };

export function AlumniProfilePage() {
  const { t } = useLanguage();
  const location = useLocation();
  const routed = (location.state as { profile?: AlumniProfile } | null)?.profile;
  const [alumniId, setAlumniId] = useState(routed?.id ?? "");
  const [state, setState] = useState<LoadState>(
    routed !== undefined ? { status: "ready", profile: routed } : { status: "idle" },
  );
  const [email, setEmail] = useState(routed?.contact_fields.email ?? "");
  const [phone, setPhone] = useState(routed?.contact_fields.phone ?? "");
  const [postal, setPostal] = useState(routed?.contact_fields.postal_address ?? "");
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    if (id.length === 0) {
      setState({ status: "idle" });
      return;
    }
    setState({ status: "loading" });
    setNotice(null);
    try {
      const profile = await findAlumniById(id);
      if (profile === null) {
        setState({ status: "missing" });
        return;
      }
      setEmail(profile.contact_fields.email ?? "");
      setPhone(profile.contact_fields.phone ?? "");
      setPostal(profile.contact_fields.postal_address ?? "");
      setState({ status: "ready", profile });
    } catch (error) {
      setState({ status: "error", messageKey: toLoadError(error).messageKey });
    }
  }, []);

  useEffect(() => {
    if (routed !== undefined) return;
    if (alumniId.length === 0) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(alumniId);
  }, [alumniId, load, routed]);

  async function save() {
    if (state.status !== "ready") return;
    setNotice(null);
    try {
      const updated = await patchAlumniContact(state.profile.id, {
        expected_version: state.profile.version,
        reason: t("alumni.contact_update_reason"),
        fields: {
          email: email.length > 0 ? email : null,
          phone: phone.length > 0 ? phone : null,
          postal_address: postal.length > 0 ? postal : null,
        },
      });
      setState({ status: "ready", profile: updated });
      setNotice(t("alumni.contact_saved"));
    } catch (error) {
      setNotice(toLoadError(error).messageKey);
    }
  }

  return (
    <section>
      <h1>{t("alumni.profile_title")}</h1>
      <p>
        <Link to="/alumni">{t("alumni.back_directory")}</Link>
      </p>
      {routed === undefined && (
        <label>
          {t("alumni.profile_id")}
          <input
            value={alumniId}
            onChange={(event) => setAlumniId(event.target.value.trim())}
            aria-label={t("alumni.profile_id")}
          />
          <button type="button" onClick={() => void load(alumniId)}>
            {t("alumni.load_profile")}
          </button>
        </label>
      )}
      {state.status === "idle" && <p role="status">{t("alumni.profile_pick")}</p>}
      {state.status === "loading" && <p role="status">{t("ui.loading")}</p>}
      {state.status === "missing" && <p role="status">{t("alumni.profile_not_found")}</p>}
      {state.status === "error" && (
        <div role="alert">
          <p>{t(state.messageKey)}</p>
          <button type="button" onClick={() => void load(alumniId)}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {state.status === "ready" && (
        <>
          <p>
            {state.profile.display_name} · {state.profile.admission_no} · v{state.profile.version}
          </p>
          <label>
            {t("alumni.field_email")}
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            {t("alumni.field_phone")}
            <input value={phone} onChange={(event) => setPhone(event.target.value)} />
          </label>
          <label>
            {t("alumni.field_postal")}
            <textarea value={postal} onChange={(event) => setPostal(event.target.value)} />
          </label>
          <button type="button" onClick={() => void save()}>
            {t("alumni.save_contact")}
          </button>
        </>
      )}
      {notice !== null && (
        <p role="status">{notice.startsWith("alumni.") || notice.startsWith("error.") ? t(notice) : notice}</p>
      )}
    </section>
  );
}
