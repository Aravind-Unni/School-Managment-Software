import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { validateModule } from "@app/moduleRegistry";
import { LanguageProvider } from "@shared/i18n/LanguageContext";
import { ClassSchedulePage } from "@features/timetable/ClassSchedulePage";
import { StudentSchedulePage } from "@features/timetable/StudentSchedulePage";
import { SubstitutionPage } from "@features/timetable/SubstitutionPage";
import { WeeklyEditorPage } from "@features/timetable/WeeklyEditorPage";
import { TIMETABLE_MESSAGES } from "@features/timetable/locales/messages";
import { TIMETABLE_PERMISSIONS, timetableModule } from "@features/timetable/module";

const CONTRACT = resolve(import.meta.dirname, "../../../contracts/M03");

function contract(relative: string): unknown {
  return JSON.parse(readFileSync(resolve(CONTRACT, relative), "utf8")) as unknown;
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response;
}

const TIMETABLE_ID = "11111111-1111-4111-8111-111111111111";
const SECTION_ID = "22222222-2222-4222-8222-222222222222";
const SLOT_ID = "33333333-3333-4333-8333-333333333333";
const SESSION_ID = "44444444-4444-4444-8444-444444444444";

const SUMMARY = {
  id: TIMETABLE_ID,
  school_id: "s",
  version: 2,
  year_id: "y",
  effective_from: "2026-06-01",
  effective_to: null,
  state: "published",
  published_at: "2026-06-01T00:00:00+00:00",
  period_count: 2,
  slot_count: 1,
};

const SLOT = {
  id: SLOT_ID,
  school_id: "s",
  timetable_id: TIMETABLE_ID,
  period_template_id: "p",
  day_of_week: 3,
  slot_code: "P1",
  section_id: SECTION_ID,
  subject_id: "sub-00001",
  teacher_id: "t",
  room_code: "R1",
};

const VERSION = {
  ...SUMMARY,
  periods: [
    {
      id: "p",
      school_id: "s",
      timetable_id: TIMETABLE_ID,
      day_of_week: 3,
      slot_code: "P1",
      starts_at_local: "08:45",
      ends_at_local: "09:30",
    },
  ],
  slots: [SLOT],
};

const SESSION = {
  timetable_session_id: SESSION_ID,
  school_id: "s",
  section_id: SECTION_ID,
  date: "2026-07-15",
  slot_id: SLOT_ID,
  slot_code: "P1",
  subject_id: "sub-00001",
  assigned_teacher_id: "t",
  substitute_teacher_id: null,
  starts_at: "2026-07-15T03:15:00+00:00",
  ends_at: "2026-07-15T04:00:00+00:00",
  starts_at_local: "08:45",
  ends_at_local: "09:30",
  cancelled: false,
  cancellation_reason_key: null,
  room_code: "R1",
  timetable_id: TIMETABLE_ID,
  timetable_version: 2,
};

/** An override that answers with a non-2xx envelope rather than a body. */
interface FailureOverride {
  readonly __status: number;
  readonly body: unknown;
}

function isFailure(value: unknown): value is FailureOverride {
  return typeof value === "object" && value !== null && "__status" in value;
}

/** Answer each endpoint the page calls, by path, so order does not matter. */
function routeFetch(overrides: Record<string, unknown> = {}) {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
    // The shared client always passes a URL string; narrowing keeps eslint from
    // having to assume Request's default stringification.
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    for (const [fragment, body] of Object.entries(overrides)) {
      if (url.includes(fragment)) {
        return Promise.resolve(
          isFailure(body) ? jsonResponse(body.body, body.__status) : jsonResponse(body),
        );
      }
    }
    if (url.includes("/timetables/current")) {
      return Promise.resolve(
        jsonResponse({
          section_id: SECTION_ID,
          date: "2026-07-15",
          is_school_day: true,
          reason_key: null,
          timetable_id: TIMETABLE_ID,
          timetable_version: 2,
          sessions: [SESSION],
        }),
      );
    }
    if (url.includes(`/timetables/${TIMETABLE_ID}`)) {
      return Promise.resolve(jsonResponse(VERSION));
    }
    if (url.includes("/timetables")) {
      return Promise.resolve(jsonResponse({ items: [SUMMARY], next_cursor: null }));
    }
    if (url.includes("/substitutions")) {
      return Promise.resolve(jsonResponse({ items: [], next_cursor: null }));
    }
    return Promise.resolve(jsonResponse({}));
  });
}

function renderPage(page: React.ReactNode) {
  return render(
    <MemoryRouter>
      <LanguageProvider>{page}</LanguageProvider>
    </MemoryRouter>,
  );
}

describe("timetable module declaration", () => {
  it("is a valid feature module", () => {
    expect(() => validateModule(timetableModule)).not.toThrow();
  });

  it("declares only permissions the approved OpenAPI asks for", () => {
    const openapi = contract("openapi.json") as {
      paths: Record<string, Record<string, { "x-permission": string }>>;
    };
    const required = new Set(
      Object.values(openapi.paths).flatMap((path) =>
        Object.values(path).map((operation) => operation["x-permission"]),
      ),
    );
    for (const code of Object.values(TIMETABLE_PERMISSIONS)) {
      expect(required.has(code)).toBe(true);
    }
  });

  it("routes require a permission this module owns", () => {
    for (const route of timetableModule.routes) {
      expect(route.requiredPermission?.startsWith("timetable.")).toBe(true);
    }
  });
});

describe("timetable translations", () => {
  it("translates every key in both languages", () => {
    const english = Object.keys(TIMETABLE_MESSAGES.en);
    const malayalam = Object.keys(TIMETABLE_MESSAGES.ml);
    expect(malayalam.sort()).toEqual(english.sort());
  });

  it("has a Malayalam string for every conflict and error key the contract returns", () => {
    const errors = contract("error-codes.json") as {
      rows: { message_key: string }[];
      conflict_codes: { message_key: string }[];
    };
    const keys = [
      ...errors.rows.map((row) => row.message_key),
      ...errors.conflict_codes.map((row) => row.message_key),
    ].filter((key) => key.startsWith("timetable."));
    for (const key of keys) {
      expect(TIMETABLE_MESSAGES.en[key], `missing English for ${key}`).toBeTruthy();
      expect(TIMETABLE_MESSAGES.ml[key], `missing Malayalam for ${key}`).toBeTruthy();
    }
  });

  it("never renders a message key to the user", () => {
    // A screen that shows "timetable.conflict.teacher_double_booked" has failed
    // at the job it exists for, so no value may look like a key.
    for (const catalogue of [TIMETABLE_MESSAGES.en, TIMETABLE_MESSAGES.ml]) {
      for (const [key, value] of Object.entries(catalogue)) {
        expect(value, key).not.toMatch(/^[a-z]+\.[a-z_.]+$/);
      }
    }
  });
});

describe("ClassSchedulePage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows a loading state before the first response", () => {
    vi.mocked(fetch).mockImplementation(() => new Promise(() => {}));
    renderPage(<ClassSchedulePage />);
    expect(screen.getByRole("status")).toHaveTextContent(/Loading/i);
  });

  it("renders the day's periods", async () => {
    routeFetch();
    renderPage(<ClassSchedulePage />);
    await waitFor(() => expect(screen.getAllByTestId("session")).toHaveLength(1));
    expect(screen.getByText("P1")).toBeInTheDocument();
  });

  it("says plainly when the date is not a teaching day", async () => {
    routeFetch({
      "/timetables/current": {
        section_id: SECTION_ID,
        date: "2026-07-16",
        is_school_day: false,
        reason_key: "timetable.reason.holiday",
        timetable_id: TIMETABLE_ID,
        timetable_version: 2,
        sessions: [],
      },
    });
    renderPage(<ClassSchedulePage />);
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(/No lessons on this day/),
    );
    expect(screen.getByRole("status")).toHaveTextContent(/Holiday/);
  });

  it("marks a cancelled period rather than dropping it", async () => {
    routeFetch({
      "/timetables/current": {
        section_id: SECTION_ID,
        date: "2026-07-15",
        is_school_day: true,
        reason_key: null,
        timetable_id: TIMETABLE_ID,
        timetable_version: 2,
        sessions: [
          { ...SESSION, cancelled: true, cancellation_reason_key: "timetable.reason.cancelled" },
        ],
      },
    });
    renderPage(<ClassSchedulePage />);
    await waitFor(() => expect(screen.getByText("Cancelled")).toBeInTheDocument());
  });

  it("renders a denial as prose, never as an error code", async () => {
    routeFetch({
      "/timetables/current": {
        __status: 403,
        body: {
          code: "action_denied",
          message_key: "error.action_denied",
          request_id: "req-1",
          field_errors: [],
        },
      },
    });
    renderPage(<ClassSchedulePage />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/do not have permission/i),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("req-1");
  });

  it("renders in Malayalam when that language is stored", async () => {
    localStorage.setItem("school.language", "ml");
    routeFetch({
      "/timetables/current": {
        section_id: SECTION_ID,
        date: "2026-07-16",
        is_school_day: false,
        reason_key: "timetable.reason.holiday",
        timetable_id: TIMETABLE_ID,
        timetable_version: 2,
        sessions: [],
      },
    });
    renderPage(<ClassSchedulePage />);
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("ഈ ദിവസം ക്ലാസുകളില്ല."),
    );
  });
});

describe("WeeklyEditorPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders the week as a grid", async () => {
    routeFetch();
    renderPage(<WeeklyEditorPage />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Wed" })).toBeInTheDocument();
  });

  it("separates a blocking conflict from an advisory one", async () => {
    routeFetch({
      "/validate": {
        timetable_id: TIMETABLE_ID,
        version: 2,
        conflicts: [
          {
            code: "teacher_double_booked",
            message_key: "timetable.conflict.teacher_double_booked",
            blocking: true,
            slot_ids: [SLOT_ID],
            teacher_id: null,
            section_id: null,
            date: null,
          },
          {
            code: "teacher_not_assigned",
            message_key: "timetable.conflict.teacher_not_assigned",
            blocking: false,
            slot_ids: [SLOT_ID],
            teacher_id: null,
            section_id: null,
            date: null,
          },
        ],
      },
    });
    renderPage(<WeeklyEditorPage />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());

    screen.getByRole("button", { name: /Check for conflicts/i }).click();

    await waitFor(() => expect(screen.getAllByTestId("conflict")).toHaveLength(2));
    expect(screen.getByText("Blocks publication")).toBeInTheDocument();
    expect(screen.getByText("Worth checking")).toBeInTheDocument();
  });
});

describe("SubstitutionPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("states that a substitute's access expires", async () => {
    routeFetch();
    renderPage(<SubstitutionPage />);
    await waitFor(() =>
      expect(
        screen.getByText(/access ends at the end of that school day/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows an empty state when nothing is covered that day", async () => {
    routeFetch();
    renderPage(<SubstitutionPage />);
    await waitFor(() =>
      expect(screen.getByText(/No substitutions for this date/i)).toBeInTheDocument(),
    );
  });
});


describe("StudentSchedulePage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("marks a period whose subject the pupil does not take", async () => {
    // The distinguishing behaviour of this view. Hiding the period would leave an
    // unexplained gap; showing it unmarked would tell a pupil to attend a lesson
    // they are not in, and later mark them absent from it.
    routeFetch({
      "/student-schedule": {
        student_id: "s",
        section_id: SECTION_ID,
        date: "2026-07-15",
        is_school_day: true,
        reason_key: null,
        sessions: [
          { session: SESSION, enrolled: false },
          {
            session: { ...SESSION, timetable_session_id: "55555555-5555-4555-8555-555555555555" },
            enrolled: true,
          },
        ],
      },
    });
    renderPage(<StudentSchedulePage />);

    const field = screen.getByLabelText("Pupil");
    fireEvent.change(field, { target: { value: "s" } });

    await waitFor(() => expect(screen.getAllByTestId("session")).toHaveLength(2));
    expect(screen.getAllByText("You do not take this subject")).toHaveLength(1);
  });

  it("shows the empty state before a pupil is named", () => {
    routeFetch();
    renderPage(<StudentSchedulePage />);
    expect(screen.getByRole("status")).toHaveTextContent("Nothing to show yet");
  });
});
