/**
 * The school's buses: who rides each one, the monthly fee, and the two things
 * the office does here: put a pupil on a bus, and take one off.
 *
 * Buses and their fees come from the school config file ([transport]); the
 * fee a pupil pays is the plan of the bus they were put on. Does not handle:
 * routes and stops, or billing (see Bus billing).
 */

import { useCallback, useEffect, useState } from "react";
import { request } from "@shared/api/client";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { rupees, shortDate } from "@shared/format";
import { Problem } from "@shared/ui/Problem";
import { can, useSession } from "@app/SessionContext";
import { StudentPicker, type PickedStudent } from "@features/registry/StudentPicker";
import { schoolToday } from "@features/registry/useSchoolStructure";
import { Loading } from "@shared/ui/Loading";

interface BusRow {
  readonly id: string;
  readonly label: string;
  readonly active: boolean;
  readonly fee_plan_id: string | null;
  readonly monthly_fee_paise: number | null;
}

interface Rider {
  readonly participation_id: string;
  readonly student_id: string;
  readonly display_name: string;
  readonly bus_id: string | null;
  readonly bus_label: string | null;
  readonly version: number;
  readonly from_date: string;
  readonly to_date: string | null;
}

export function TransportParticipantsPage() {
  const { t, language } = useLanguage();
  const { actions } = useSession();
  const canManage = can(actions, "transport.manage");
  const [buses, setBuses] = useState<readonly BusRow[]>([]);
  const [riders, setRiders] = useState<readonly Rider[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [student, setStudent] = useState<PickedStudent | null>(null);
  const [busId, setBusId] = useState("");
  const [from, setFrom] = useState(schoolToday());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [busPage, riderPage] = await Promise.all([
        request<{ items: BusRow[] }>("/api/v1/buses"),
        request<{ items: Rider[] }>("/api/v1/bus-participants", { query: { date: schoolToday() } }),
      ]);
      setBuses(busPage.items.filter((row) => row.active));
      setRiders(riderPage.items);
    } catch (caught) {
      setError(caught);
      setRiders([]);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads this screen's data
    void load();
  }, [load]);

  const act = async (work: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await work();
      setNotice(done);
      await load();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  };

  const bus = buses.find((row) => row.id === busId) ?? null;
  const addRider = () =>
    act(async () => {
      if (!student || !bus?.fee_plan_id) return;
      await request("/api/v1/bus-participations", {
        method: "POST",
        body: { student_id: student.id, bus_id: bus.id, fee_plan_id: bus.fee_plan_id, from_date: from },
      });
      setStudent(null);
      setAdding(false);
    }, `${student?.display_name ?? ""} ${t("bus.added")} ${bus?.label ?? ""}.`);

  const stop = (rider: Rider) =>
    act(
      () =>
        request(`/api/v1/bus-participations/${rider.participation_id}`, {
          method: "PATCH",
          body: { expected_version: rider.version, reason: "Stopped using the bus", to_date: schoolToday() },
        }),
      `${rider.display_name} ${t("bus.stopped")}`,
    );

  const onBus = (id: string) => (riders ?? []).filter((row) => row.bus_id === id && !row.to_date);

  return (
    <section aria-labelledby="bus-title">
      <h2 id="bus-title">{t("bus.title")}</h2>
      {notice ? (
        <p role="status" className="notice-success">
          {notice}
        </p>
      ) : null}
      <Problem error={error} />

      {canManage && !adding ? (
        <button type="button" onClick={() => setAdding(true)}>
          {t("bus.add")}
        </button>
      ) : null}
      {adding ? (
        <div className="cover-pick stack">
          <h3>{t("bus.add")}</h3>
          {student === null ? (
            <StudentPicker onPick={setStudent} />
          ) : (
            <div className="picked-person">
              <strong>{student.display_name}</strong>
              <span className="hint">{student.admission_no}</span>
              <button type="button" className="quiet" onClick={() => setStudent(null)}>
                {t("fees.collect.change_student")}
              </button>
            </div>
          )}
          <div className="teacher-choices" role="radiogroup" aria-label={t("bus.which")}>
            {buses.map((row) => (
              <label key={row.id} className="teacher-choice">
                <input type="radio" name="bus" checked={busId === row.id} onChange={() => setBusId(row.id)} />
                <span>
                  <strong>{row.label}</strong>
                  <span className="hint">
                    {rupees(row.monthly_fee_paise)} {t("bus.per_month")} · {onBus(row.id).length} {t("bus.riders")}
                  </span>
                </span>
              </label>
            ))}
          </div>
          <label>
            {t("bus.from")}
            <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
          </label>
          <div className="row-actions">
            <button aria-busy={busy} type="button" disabled={busy || !student || !bus} onClick={() => void addRider()}>
              {busy ? t("ui.loading") : t("bus.confirm")}
            </button>
            <button type="button" className="quiet" onClick={() => setAdding(false)}>
              {t("details.cancel")}
            </button>
          </div>
        </div>
      ) : null}

      {riders === null ? (
        <Loading />
      ) : buses.length === 0 ? (
        <p className="empty-state">{t("bus.none")}</p>
      ) : (
        buses.map((row) => {
          const list = onBus(row.id);
          return (
            <div key={row.id}>
              <h3>
                {row.label}{" "}
                <span className="hint">
                  · {list.length} {t("bus.riders")} · {rupees(row.monthly_fee_paise)} {t("bus.per_month")}
                </span>
              </h3>
              {list.length === 0 ? (
                <p className="hint">{t("bus.empty")}</p>
              ) : (
                <ul className="charge-list">
                  {list.map((rider) => (
                    <li key={rider.participation_id}>
                      <div>
                        <strong>{rider.display_name}</strong>
                        <span className="hint">
                          {t("bus.since")} {shortDate(rider.from_date, language)}
                        </span>
                      </div>
                      {canManage ? (
                        <button type="button" className="quiet" disabled={busy} onClick={() => void stop(rider)}>
                          {t("bus.stop")}
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })
      )}
    </section>
  );
}
