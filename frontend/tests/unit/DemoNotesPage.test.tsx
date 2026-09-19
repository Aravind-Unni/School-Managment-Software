import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "@shared/i18n/LanguageContext";
import { DemoNotesPage } from "@features/demo/DemoNotesPage";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response;
}

function renderPage() {
  return render(
    <MemoryRouter>
      <LanguageProvider>
        <DemoNotesPage />
      </LanguageProvider>
    </MemoryRouter>,
  );
}

describe("DemoNotesPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders the notes returned by the API", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        items: [
          { id: "1", school_id: "s", body: "First note", version: 1, section_id: null, subject_person_id: null },
          { id: "2", school_id: "s", body: "Second note", version: 3, section_id: null, subject_person_id: null },
        ],
        next_cursor: null,
      }),
    );
    renderPage();
    await waitFor(() => expect(screen.getAllByTestId("demo-note")).toHaveLength(2));
    expect(screen.getByText("First note")).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
  });

  it("shows an empty state rather than a blank page", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ items: [], next_cursor: null }));
    renderPage();
    await waitFor(() => expect(screen.getByText("Nothing to show yet.")).toBeInTheDocument());
  });

  it("renders a denial through its message key, with the request id", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          code: "action_denied",
          message_key: "error.action_denied",
          request_id: "req-42",
          field_errors: [],
        },
        403,
      ),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("You do not have permission to do this.")).toBeInTheDocument(),
    );
    expect(screen.getByText("req-42")).toBeInTheDocument();
  });

  it("reports a network failure as transport, not as a denial", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("offline"));
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByText("Could not reach the server. Check your connection."),
      ).toBeInTheDocument(),
    );
  });

  it("offers Load more only when there is a next page", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        items: [{ id: "1", school_id: "s", body: "Only", version: 1, section_id: null, subject_person_id: null }],
        next_cursor: "cursor-1",
      }),
    );
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Load more" })).toBeInTheDocument());
  });
});
