"""Purpose allowlists, profile ids and MIME maps for M12."""

from __future__ import annotations

ANSWER_SHEET = "answer_sheet"

ALLOWED_PURPOSES = frozenset(
    {
        "answer_sheet",
        "import_csv",
        "import_xlsx",
        "report_pdf",
        "report_csv",
        "report_xlsx",
    }
)

ANSWER_SHEET_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})

PURPOSE_MIMES: dict[str, frozenset[str]] = {
    "answer_sheet": ANSWER_SHEET_MIMES,
    "import_csv": frozenset({"text/csv", "application/csv"}),
    "import_xlsx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        }
    ),
    "report_pdf": frozenset({"application/pdf"}),
    "report_csv": frozenset({"text/csv", "application/csv"}),
    "report_xlsx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        }
    ),
}

PROFILE_DEFAULT = "webp85_le2400_v1"
PROFILE_HIGHER_FIDELITY = "jpeg95_le3200_v1"

UPLOAD_TTL_SECONDS = 15 * 60
DEFAULT_MAX_BYTES = 12_582_912
