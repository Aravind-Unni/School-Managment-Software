/**
 * Render an otpauth:// URI as a QR code for authenticator enrolment.
 *
 * Generated entirely in-browser so the TOTP seed never leaves the page as a
 * third-party image request. Does not handle: printing or offline export.
 */

import { useEffect, useState } from "react";
import QRCode from "qrcode";

export function TotpQrCode({
  otpauthUri,
  label,
}: {
  readonly otpauthUri: string;
  readonly label: string;
}) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    setFailed(false);
    void QRCode.toDataURL(otpauthUri, {
      errorCorrectionLevel: "M",
      margin: 2,
      width: 220,
      color: { dark: "#111111", light: "#ffffff" },
    })
      .then((url) => {
        if (!cancelled) setDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [otpauthUri]);

  if (failed) {
    return (
      <p role="status">
        QR code could not be drawn. Use the manual key below.
      </p>
    );
  }
  if (dataUrl === null) {
    return <p role="status">Preparing QR code…</p>;
  }
  return (
    <figure className="totp-qr" data-testid="enrol-qr">
      <img src={dataUrl} alt={label} width={220} height={220} />
    </figure>
  );
}
