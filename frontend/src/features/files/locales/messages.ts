/** en/ml strings for M12 files. */

export const FILES_MESSAGES = {
  en: {
    "nav.files_review": "Answer sheet review",
    "nav.files_view": "View evidence",
    "files.review_title": "Answer sheet quality review",
    "files.review_help":
      "Compare the compression candidate to the source, confirm readability, or request higher-fidelity reprocess. Only confirmed canonical versions can be pinned.",
    "files.review_step_status": "GET /api/v1/files/{id}/status for candidate metadata.",
    "files.review_step_confirm":
      "POST /api/v1/files/{id}/quality-confirmation with candidate_version.",
    "files.review_step_reprocess":
      "POST /api/v1/files/{id}/reprocess with profile higher_fidelity when needed.",
    "files.viewer_title": "Evidence viewer",
    "files.viewer_help":
      "Parents and students see only the confirmed canonical image via a short-lived server-minted read URL. Quarantine and candidate bytes are never exposed here.",
  },
  ml: {
    "nav.files_review": "ഉത്തരക്കടലാസ് അവലോകനം",
    "nav.files_view": "തെളിവ് കാണുക",
    "files.review_title": "ഉത്തരക്കടലാസ് ഗുണനിലവാര അവലോകനം",
    "files.review_help":
      "കംപ്രഷൻ കാൻഡിഡേറ്റ് ഉറവിടവുമായി താരതമ്യം ചെയ്ത് വായനായോഗ്യത സ്ഥിരീകരിക്കുക. സ്ഥിരീകരിച്ച കാനോനിക്കൽ മാത്രമേ പിൻ ചെയ്യാവൂ.",
    "files.review_step_status": "GET /api/v1/files/{id}/status.",
    "files.review_step_confirm": "POST quality-confirmation with candidate_version.",
    "files.review_step_reprocess": "POST reprocess with higher_fidelity when needed.",
    "files.viewer_title": "തെളിവ് വ്യൂവർ",
    "files.viewer_help":
      "രക്ഷിതാക്കൾക്കും വിദ്യാർത്ഥികൾക്കും സ്ഥിരീകരിച്ച കാനോനിക്കൽ മാത്രം — ഹ്രസ്വകാല റീഡ് URL വഴി.",
  },
} as const;
