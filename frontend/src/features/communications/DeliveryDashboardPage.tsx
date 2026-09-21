/** Delivery status lookup by id. */

import { useState } from "react";
import { toLoadError } from "@shared/api/errors";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { getDelivery, type Delivery } from "./api";

export function DeliveryDashboardPage() {
  const { t } = useLanguage();
  const [deliveryId, setDeliveryId] = useState("");
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const id = deliveryId.trim();
    if (id.length === 0) return;
    setLoading(true);
    setErrorKey(null);
    setDelivery(null);
    try {
      setDelivery(await getDelivery(id));
    } catch (error) {
      setErrorKey(toLoadError(error).messageKey);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h1>{t("communications.deliveries_title")}</h1>
      <label>
        {t("communications.delivery_id")}
        <input value={deliveryId} onChange={(event) => setDeliveryId(event.target.value)} />
      </label>
      <button type="button" disabled={loading || deliveryId.trim().length === 0} onClick={() => void load()}>
        {loading ? t("ui.loading") : t("communications.load_delivery")}
      </button>
      {errorKey !== null && (
        <div role="alert">
          <p>{t(errorKey)}</p>
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </div>
      )}
      {delivery !== null && (
        <section>
          <dl>
            <div>
              <dt>{t("communications.delivery_state")}</dt>
              <dd>{delivery.state}</dd>
            </div>
            <div>
              <dt>{t("communications.channel")}</dt>
              <dd>{delivery.channel}</dd>
            </div>
            <div>
              <dt>{t("communications.template_key")}</dt>
              <dd>{delivery.template_key}</dd>
            </div>
          </dl>
          {delivery.attempts.length === 0 ? (
            <p role="status">{t("ui.empty")}</p>
          ) : (
            <ul>
              {delivery.attempts.map((attempt) => (
                <li key={attempt.id}>
                  {attempt.attempted_at} · {attempt.outcome}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </section>
  );
}
