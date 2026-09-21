/**
 * The at-risk list: pupils whose attendance has fallen below the school's
 * threshold or who have missed work, grouped by class, each with the figure
 * that raised it.
 *
 * Staff mark a warning "Following up" once someone owns it, or dismiss it with
 * a reason. Warnings are raised when progress is recomputed (nightly, or with
 * "Check again now" here). Does not handle: creating interventions (open the
 * pupil and use Interventions) or changing thresholds (the school config file).
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { can, useSession } from "@app/SessionContext";
import { performanceMessages } from "./locales/messages";

interface ListedWarning {
  readonly id: string;
  readonly student_id: string;
  readonly student_name: string | null;
  readonly section_label: string | null;
  readonly rule_code: string;
  readonly threshold: string;
  readonly state: "open" | "acknowledged";
  readonly version: number;
  readonly source_refs: readonly string[];
  readonly opened_at: string;
}

type Filter = "all" | "low_attendance" | "missing_work";

/** Pull "62.50" out of ["attendance:62.50", ...]. */
function refValue(refs: readonly string[], prefix: string): string | null {
  const found = refs.find((ref) => ref.startsWith(`${prefix}:`));
  return found ? found.slice(prefix.length + 1) : null;
}

export function AtRiskListPage() {
  const { language } = useLanguage();
  const t = performanceMessages[language];
  const { actions } = useSession();
  const canManage = can(actions, "warnings.manage");
  const [rows, setRows] = useState<readonly ListedWarning[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const page = await request<{ items: ListedWarning[] }>("/api/v1/warnings");
      setRows(page.items);
    } catch (caught) {
      setError(caught);
      setRows([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const act = async (work: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
      setDismissing(null);
      setReason("");
      await load();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const transition = (row: ListedWarning, verb: "acknowledge" | "dismiss", why: string) =>
    act(() =>
      request(`/api/v1/warnings/${row.id}/${verb}`, {
        method: "POST",
        body: { reason: why, expected_version: row.version },
      }),
    );

  const [checking, setChecking] = useState(false);
  const recheck = () =>
    act(async () => {
      const started = await request<{ state: string }>("/api/v1/performance/rebuild", { method: "POST", body: {} });
      if (started.state === "queued") setChecking(true);
    });

  // A queued check runs on the server for a minute or two; refresh the list
  // every ten seconds for three minutes so new warnings appear by themselves.
  useEffect(() => {
    if (!checking) return undefined;
    let rounds = 0;
    const timer = window.setInterval(() => {
      rounds += 1;
      void load();
      if (rounds >= 18) setChecking(false);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [checking, load]);

  if (rows === null) return <p role="status">{t["performance.loading"]}</p>;

  const shown = rows.filter((row) => filter === "all" || row.rule_code === filter);
  const byClass = new Map<string, ListedWarning[]>();
  for (const row of shown) {
    const key = row.section_label ?? "—";
    byClass.set(key, [...(byClass.get(key) ?? []), row]);
  }
  const classes = [...byClass.keys()].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const count = (code: Filter) => rows.filter((row) => code === "all" || row.rule_code === code).length;

  const reasonLine = (row: ListedWarning) => {
    if (row.rule_code === "low_attendance") {
      const value = refValue(row.source_refs, "attendance");
      return `${t["risk.attendance"]} ${value ? Number(value).toFixed(0) : "?"}% · ${t["risk.below"]} ${Number(row.threshold).toFixed(0)}%`;
    }
    if (row.rule_code === "missing_work") {
      return `${refValue(row.source_refs, "missing") ?? "?"} ${t["risk.missing_count"]}`;
    }
    return row.rule_code;
  };

  return (
    <section aria-labelledby="risk-title">
      <h2 id="risk-title">{t["performance.at_risk_title"]}</h2>
      <p className="hint">{t["risk.intro"]}</p>
      <div className="toolbar">
        <div className="segmented" role="group" aria-label={t["risk.show"]}>
          {(["all", "low_attendance", "missing_work"] as const).map((code) => (
            <button
              key={code}
              type="button"
              className="seg"
              aria-pressed={filter === code}
              onClick={() => setFilter(code)}
            >
              {t[`risk.filter.${code}`]} ({count(code)})
            </button>
          ))}
        </div>
        {canManage ? (
          <button type="button" className="secondary" disabled={busy || checking} onClick={() => void recheck()}>
            {busy ? t["performance.loading"] : t["risk.recheck"]}
          </button>
        ) : null}
      </div>
      {checking ? (
        <p role="status" className="hint">
          {t["risk.checking"]}
        </p>
      ) : null}
      <Problem error={error} />
      {shown.length === 0 ? (
        <p role="status" className="empty-state">
          {t["risk.none"]}
        </p>
      ) : (
        classes.map((label) => (
          <div key={label}>
            <h3>{label}</h3>
            <ul className="risk-list">
              {(byClass.get(label) ?? []).map((row) => (
                <li key={row.id} className={`risk-${row.rule_code} ${row.state}`}>
                  <div className="risk-who">
                    <strong>{row.student_name ?? t["performance.student_label"]}</strong>
                    <span className="attention">{reasonLine(row)}</span>
                    <span className="hint">
                      {t["risk.raised"]} {shortDate(row.opened_at, language)}
                      {row.state === "acknowledged" ? ` · ${t["risk.following"]}` : ""}
                    </span>
                  </div>
                  <div className="row-actions">
                    <Link className="button-link secondary" to={`/registry/overview?student=${row.student_id}`}>
                      {t["risk.view"]}
                    </Link>
                    {canManage && row.state === "open" ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void transition(row, "acknowledge", t["risk.following"])}
                      >
                        {t["risk.follow_up"]}
                      </button>
                    ) : null}
                    {canManage && dismissing !== row.id ? (
                      <button type="button" className="quiet" disabled={busy} onClick={() => setDismissing(row.id)}>
                        {t["risk.dismiss"]}
                      </button>
                    ) : null}
                  </div>
                  {dismissing === row.id ? (
                    <form
                      className="risk-dismiss"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void transition(row, "dismiss", reason.trim());
                      }}
                    >
                      <label>
                        {t["risk.dismiss_reason"]}
                        <input value={reason} autoFocus onChange={(event) => setReason(event.target.value)} />
                      </label>
                      <div className="row-actions">
                        <button type="submit" disabled={busy || reason.trim() === ""}>
                          {t["risk.dismiss"]}
                        </button>
                        <button type="button" className="quiet" onClick={() => setDismissing(null)}>
                          {t["risk.cancel"]}
                        </button>
                      </div>
                    </form>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </section>
  );
}
