/**
 * Overdue fees: who owes what, since when, and one tap to collect.
 * Sorted by amount so the office sees the largest balances first.
 */

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { rupees, shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { fetchOverdue, type OverdueItemDTO } from "./api";
import { Loading } from "@shared/ui/Loading";

function daysBetween(fromIso: string, toIso: string): number {
  return Math.max(0, Math.round((Date.parse(toIso) - Date.parse(fromIso)) / 86_400_000));
}

export function FeeOverduePage() {
  const { t, language } = useLanguage();
  const [items, setItems] = useState<readonly OverdueItemDTO[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const today = schoolToday();

  useEffect(() => {
    fetchOverdue().then(
      (body) => setItems(body.items),
      (caught: unknown) => {
        setError(caught);
        setItems([]);
      },
    );
  }, []);

  const byStudent = useMemo(() => {
    const totals = new Map<string, { name: string; balance: number; oldest: string }>();
    for (const row of items ?? []) {
      const current = totals.get(row.student_id);
      totals.set(row.student_id, {
        name: row.display_name ?? "",
        balance: (current?.balance ?? 0) + row.balance_paise,
        oldest: current && current.oldest < row.due_date ? current.oldest : row.due_date,
      });
    }
    return [...totals.entries()].sort((a, b) => b[1].balance - a[1].balance);
  }, [items]);
  const grand = byStudent.reduce((sum, [, row]) => sum + row.balance, 0);

  return (
    <section aria-labelledby="overdue-title">
      <h2 id="overdue-title">{t("fees.overdue_title")}</h2>
      <Problem error={error} />
      {items === null ? <Loading /> : null}
      {items !== null && byStudent.length === 0 && error === null ? (
        <p role="status" className="notice-success">
          {t("fees.overdue.none")}
        </p>
      ) : null}
      {byStudent.length > 0 ? (
        <>
          <p>
            {byStudent.length} {t("fees.overdue.students")} · <strong>{rupees(grand)}</strong>{" "}
            {t("fees.overdue.in_total")}
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("fees.collect.student")}</th>
                  <th scope="col">{t("fees.overdue.since")}</th>
                  <th scope="col">{t("fees.overdue.days")}</th>
                  <th scope="col">{t("fees.collect.balance")}</th>
                  <th scope="col" />
                </tr>
              </thead>
              <tbody>
                {byStudent.map(([studentId, row]) => (
                  <tr key={studentId}>
                    <th scope="row">{row.name}</th>
                    <td>{shortDate(row.oldest, language)}</td>
                    <td>{daysBetween(row.oldest, today)}</td>
                    <td>
                      <strong>{rupees(row.balance)}</strong>
                    </td>
                    <td>
                      <Link className="button-link secondary" to={`/fees/collect?student=${studentId}`}>
                        {t("fees.overdue.collect")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
