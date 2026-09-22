/**
 * A pupil's photo, or their initials when there is none; and the control
 * that takes a new one (a phone offers the camera or the gallery).
 *
 * The picture is shrunk in the browser to at most 480 px on its longer side
 * and saved as JPEG, so a 5 MB camera photo uploads as roughly 40 KB.
 * Does not handle: cropping (the photo is centred in a circle when shown).
 */

import { useState, type ChangeEvent } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { Problem } from "@shared/ui/Problem";

const LONGEST_SIDE = 480;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "")).toUpperCase();
}

/** Shrink an image file to a JPEG blob no longer than LONGEST_SIDE. */
async function shrink(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, LONGEST_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("could not encode photo"))), "image/jpeg", 0.85),
  );
}

/** Shrink and store a pupil's photo. */
export async function uploadStudentPhoto(studentId: string, file: File): Promise<void> {
  const data = await shrink(file);
  await request(`/api/v1/students/${studentId}/photo`, {
    method: "PUT",
    rawBody: { data, contentType: "image/jpeg" },
  });
}

export function StudentAvatar({
  studentId,
  name,
  size = 64,
  version = 0,
}: {
  readonly studentId: string;
  readonly name: string;
  readonly size?: number;
  readonly version?: number;
}) {
  const [failed, setFailed] = useState<string | null>(null);
  const key = `${studentId}:${version}`;
  const style = { width: size, height: size, fontSize: size * 0.38 };
  if (failed === key) {
    return (
      <span className="avatar avatar-initials" style={style} aria-hidden="true">
        {initials(name)}
      </span>
    );
  }
  return (
    <img
      className="avatar"
      style={style}
      src={`/api/v1/students/${studentId}/photo?v=${version}`}
      alt={name}
      onError={() => setFailed(key)}
    />
  );
}

/** Photo with Take/Change and Remove buttons, for the office. */
export function StudentPhotoEditor({ studentId, name }: { readonly studentId: string; readonly name: string }) {
  const { t } = useLanguage();
  const [version, setVersion] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadStudentPhoto(studentId, file);
      setVersion(Date.now());
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await request(`/api/v1/students/${studentId}/photo`, { method: "DELETE" });
      setVersion(Date.now());
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="photo-editor">
      <StudentAvatar studentId={studentId} name={name} size={112} version={version} />
      <div className="photo-actions">
        <label className="button-link secondary photo-pick">
          {busy ? t("ui.loading") : t("photo.choose")}
          <input
            type="file"
            accept="image/*"
            disabled={busy}
            onChange={(event) => void choose(event)}
          />
        </label>
        <button type="button" className="quiet" disabled={busy} onClick={() => void remove()}>
          {t("photo.remove")}
        </button>
        <Problem error={error} />
      </div>
    </div>
  );
}
