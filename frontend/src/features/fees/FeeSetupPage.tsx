/**
 * Fee setup: the school's fee types with what has been charged and what is
 * still owed, and a form to charge a fee to whole classes at once.
 *
 * Charging the same fee and due date again only charges pupils who were not
 * charged yet, so after new admissions the office simply repeats it.
 * Does not handle: one-off charges for a single pupil or waivers (use
 * Concessions), or editing an amount already charged.
 */

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { paiseFromRupees, rupees, shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { useSchoolStructure } from "@features/registry/useSchoolStructure";
import { Loading } from "@shared/ui/Loading";

interface FeeHeadRow {
  readonly id: string;
  readonly label_key: string;
  readonly charged_paise: number;
  readonly outstanding_paise: number;
  readonly pupils: number;
  readonly first_due: string | null;
}

interface ChargeResult {
  readonly label_key: string;
  readonly charged: number;
  readonly already_charged: number;
}

const NEW_FEE = "new";

export function FeeSetupPage() {
  const { t, language } = useLanguage();
  const { state } = useSchoolStructure();
  const sections = state.kind === "ready" ? state.structure.sections : [];
  const [heads, setHeads] = useState<readonly FeeHeadRow[] | null>(null);
  const [headId, setHeadId] = useState(NEW_FEE);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [due, setDue] = useState("");
  const [chosen, setChosen] = useState<readonly string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<ChargeResult | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await request<{ items: FeeHeadRow[] }>("/api/v1/fee-heads");
      setHeads(page.items);
    } catch (caught) {
      setError(caught);
      setHeads([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const standards = [...new Set(sections.map((row) => row.standardNumber))].sort((a, b) => a - b);
  const toggle = (ids: readonly string[], on: boolean) =>
    setChosen((previous) =>
      on ? [...new Set([...previous, ...ids])] : previous.filter((id) => !ids.includes(id)),
    );

  const paise = paiseFromRupees(amount);
  const ready =
    paise !== null && paise > 0 && due !== "" && chosen.length > 0 && (headId !== NEW_FEE || name.trim() !== "");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await request<ChargeResult>("/api/v1/fees/charge-classes", {
        method: "POST",
        body: {
          fee_head_id: headId === NEW_FEE ? null : headId,
          fee_name: headId === NEW_FEE ? name.trim() : "",
          amount_paise: paise,
          due_date: due,
          section_ids: chosen,
        },
      });
      setResult(response);
      setChosen([]);
      await load();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="fee-setup-title">
      <h2 id="fee-setup-title">{t("feesetup.title")}</h2>
      <div className="two-column">
        <div>
          <h3>{t("feesetup.types")}</h3>
          {heads === null ? (
            <Loading />
          ) : heads.length === 0 ? (
            <p className="empty-state">{t("feesetup.none")}</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th scope="col">{t("feesetup.fee")}</th>
                    <th scope="col">{t("feesetup.due")}</th>
                    <th scope="col" className="num">{t("feesetup.pupils")}</th>
                    <th scope="col" className="num">{t("feesetup.charged")}</th>
                    <th scope="col" className="num">{t("feesetup.outstanding")}</th>
                  </tr>
                </thead>
                <tbody>
                  {heads.map((row) => (
                    <tr key={row.id}>
                      <td>{t(row.label_key)}</td>
                      <td>{shortDate(row.first_due, language)}</td>
                      <td className="num">{row.pupils}</td>
                      <td className="num">{rupees(row.charged_paise)}</td>
                      <td className={`num${row.outstanding_paise > 0 ? " attention" : ""}`}>
                        {rupees(row.outstanding_paise)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <form className="stack" onSubmit={(event) => void submit(event)}>
          <h3>{t("feesetup.charge_title")}</h3>
          <label>
            {t("feesetup.fee")}
            <select value={headId} onChange={(event) => setHeadId(event.target.value)}>
              <option value={NEW_FEE}>{t("feesetup.new_fee")}</option>
              {(heads ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {t(row.label_key)}
                </option>
              ))}
            </select>
          </label>
          {headId === NEW_FEE ? (
            <label>
              {t("feesetup.name")}
              <input
                value={name}
                maxLength={120}
                placeholder={t("feesetup.name_example")}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
          ) : null}
          <div className="inline-fields">
            <label>
              {t("feesetup.amount")}
              <input inputMode="decimal" value={amount} placeholder="1500" onChange={(event) => setAmount(event.target.value)} />
            </label>
            <label>
              {t("feesetup.due")}
              <input type="date" value={due} onChange={(event) => setDue(event.target.value)} />
            </label>
          </div>
          <fieldset>
            <legend>{t("feesetup.classes")}</legend>
            {standards.map((standard) => {
              const inStandard = sections.filter((row) => row.standardNumber === standard);
              const ids = inStandard.map((row) => row.id);
              const all = ids.every((id) => chosen.includes(id));
              return (
                <div key={standard} className="class-grid">
                  {inStandard.map((row) => (
                    <label key={row.id} className="inline">
                      <input
                        type="checkbox"
                        checked={chosen.includes(row.id)}
                        onChange={(event) => toggle([row.id], event.target.checked)}
                      />
                      {row.label}
                    </label>
                  ))}
                  {inStandard.length > 1 ? (
                    <button type="button" className="quiet" onClick={() => toggle(ids, !all)}>
                      {all ? t("feesetup.clear_std") : t("feesetup.all_std")} {standard}
                    </button>
                  ) : null}
                </div>
              );
            })}
            <button
              type="button"
              className="quiet"
              onClick={() => toggle(sections.map((row) => row.id), chosen.length < sections.length)}
            >
              {chosen.length < sections.length ? t("feesetup.all_classes") : t("feesetup.clear")}
            </button>
          </fieldset>
          <p className="hint">{t("feesetup.repeat_hint")}</p>
          <Problem error={error} />
          {result ? (
            <p role="status" className="notice-success">
              {t(result.label_key)}: {t("feesetup.charged_to")} {result.charged} {t("feesetup.pupils_word")}
              {result.already_charged > 0
                ? ` · ${result.already_charged} ${t("feesetup.already")}`
                : ""}
            </p>
          ) : null}
          <button type="submit" disabled={busy || !ready}>
            {busy
              ? t("ui.loading")
              : paise
                ? `${t("feesetup.charge")} ${rupees(paise)}`
                : t("feesetup.charge")}
          </button>
        </form>
      </div>
    </section>
  );
}

export default FeeSetupPage;
