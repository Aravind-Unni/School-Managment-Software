/** en/ml strings for M13 exchange. */

export const EXCHANGE_MESSAGES = {
  en: {
    "nav.imports": "Imports",
    "nav.exports": "Exports",
    "nav.reports": "Reports",
    "nav.report_cards": "Report cards",
    "exchange.imports_title": "Import centre",
    "exchange.imports_help":
      "Upload a file, review every rejected row, then commit. Validation never changes school data; only the commit does.",
    "exchange.imports_step_template":
      "GET /api/v1/import-templates/{dataset} for the column list.",
    "exchange.imports_step_validate": "POST /api/v1/imports with the uploaded file_ref.",
    "exchange.imports_step_errors": "GET /api/v1/imports/{id}/errors for row, field and code.",
    "exchange.imports_step_commit":
      "POST /api/v1/imports/{id}/commit with an Idempotency-Key header.",
    "exchange.imports_digest_note":
      "The commit sends the digest of the file you reviewed. If the file changed, the commit is refused rather than applying bytes nobody read.",
    "exchange.exports_title": "Export centre",
    "exchange.exports_help":
      "Exports run in the background and produce a file behind a short-lived link. Columns you may not see are left out of the file, not blanked.",
    "exchange.exports_step_create": "POST /api/v1/exports with dataset, filters and fields.",
    "exchange.exports_step_poll": "GET /api/v1/exports/{id} until the state is ready.",
    "exchange.exports_step_download": "GET /api/v1/exports/{id}/download for the read URL.",
    "exchange.exports_fields_note":
      "Cells that would run as a spreadsheet formula are written as plain text.",
    "exchange.reports_title": "Reports",
    "exchange.reports_help":
      "A report snapshot records what was issued. It is never edited; a correction is issued as a new snapshot.",
    "exchange.reports_bound_revisions":
      "Each snapshot names the result revisions and policy versions it was built from.",
    "exchange.reports_superseded":
      "A replaced snapshot stays readable and points at its replacement.",
    "exchange.reports_download":
      "Downloading re-checks your permission at that moment, not when the report was made.",
    "exchange.report_cards_title": "Report cards",
    "exchange.report_cards_help":
      "Generate one card per pupil from a publication. Each card is bound to the published result revisions it used.",
    "exchange.report_cards_step_select": "Choose the publication and the pupils.",
    "exchange.report_cards_step_generate": "POST /api/v1/reportcards to enqueue one job each.",
    "exchange.report_cards_step_poll": "GET /api/v1/reportcards/{id} until the state is ready.",
    "exchange.report_cards_font_pending":
      "Malayalam text is carried in the file, but the embedded Malayalam font bundle is still awaiting approval, so a viewer without that font may not display it correctly.",
  },
  ml: {
    "nav.imports": "ഇറക്കുമതികൾ",
    "nav.exports": "കയറ്റുമതികൾ",
    "nav.reports": "റിപ്പോർട്ടുകൾ",
    "nav.report_cards": "പുരോഗതി കാർഡുകൾ",
    "exchange.imports_title": "ഇറക്കുമതി കേന്ദ്രം",
    "exchange.imports_help":
      "ഫയൽ അപ്‌ലോഡ് ചെയ്യുക, നിരസിച്ച വരികൾ പരിശോധിക്കുക, തുടർന്ന് കമ്മിറ്റ് ചെയ്യുക. പരിശോധന വിവരങ്ങൾ മാറ്റില്ല; കമ്മിറ്റ് മാത്രമേ മാറ്റൂ.",
    "exchange.imports_step_template": "GET /api/v1/import-templates/{dataset}.",
    "exchange.imports_step_validate": "POST /api/v1/imports — file_ref സഹിതം.",
    "exchange.imports_step_errors": "GET /api/v1/imports/{id}/errors.",
    "exchange.imports_step_commit": "POST /api/v1/imports/{id}/commit — Idempotency-Key സഹിതം.",
    "exchange.imports_digest_note":
      "നിങ്ങൾ പരിശോധിച്ച ഫയലിന്റെ ഡൈജസ്റ്റ് കമ്മിറ്റിനൊപ്പം പോകുന്നു. ഫയൽ മാറിയെങ്കിൽ കമ്മിറ്റ് നിരസിക്കും.",
    "exchange.exports_title": "കയറ്റുമതി കേന്ദ്രം",
    "exchange.exports_help":
      "കയറ്റുമതികൾ പശ്ചാത്തലത്തിൽ പ്രവർത്തിക്കുന്നു; ഹ്രസ്വകാല ലിങ്കിലൂടെ ഫയൽ ലഭിക്കും. അനുമതിയില്ലാത്ത കോളങ്ങൾ ഫയലിൽ ഉൾപ്പെടുത്തില്ല.",
    "exchange.exports_step_create": "POST /api/v1/exports — dataset, filters, fields.",
    "exchange.exports_step_poll": "GET /api/v1/exports/{id} — ready ആകുന്നതുവരെ.",
    "exchange.exports_step_download": "GET /api/v1/exports/{id}/download.",
    "exchange.exports_fields_note":
      "സ്‌പ്രെഡ്‌ഷീറ്റ് ഫോർമുലയായി പ്രവർത്തിക്കാവുന്ന സെല്ലുകൾ വെറും വാചകമായി എഴുതുന്നു.",
    "exchange.reports_title": "റിപ്പോർട്ടുകൾ",
    "exchange.reports_help":
      "ഒരു റിപ്പോർട്ട് സ്നാപ്പ്ഷോട്ട് നൽകിയത് എന്തെന്ന് രേഖപ്പെടുത്തുന്നു. അത് തിരുത്തില്ല; തിരുത്തൽ പുതിയ സ്നാപ്പ്ഷോട്ടായി വരും.",
    "exchange.reports_bound_revisions":
      "ഓരോ സ്നാപ്പ്ഷോട്ടും അത് ഉപയോഗിച്ച ഫല റിവിഷനുകളും നയ പതിപ്പുകളും പേരെടുത്ത് പറയുന്നു.",
    "exchange.reports_superseded":
      "മാറ്റിവെച്ച സ്നാപ്പ്ഷോട്ട് വായിക്കാവുന്നതായി തുടരും; പകരക്കാരനെ ചൂണ്ടിക്കാണിക്കും.",
    "exchange.reports_download":
      "ഡൗൺലോഡ് ചെയ്യുമ്പോൾ അപ്പോഴത്തെ അനുമതി വീണ്ടും പരിശോധിക്കുന്നു.",
    "exchange.report_cards_title": "പുരോഗതി കാർഡുകൾ",
    "exchange.report_cards_help":
      "ഒരു പ്രസിദ്ധീകരണത്തിൽ നിന്ന് ഓരോ വിദ്യാർത്ഥിക്കും ഒരു കാർഡ് ഉണ്ടാക്കുക. ഓരോ കാർഡും അത് ഉപയോഗിച്ച ഫല റിവിഷനുകളുമായി ബന്ധിപ്പിക്കുന്നു.",
    "exchange.report_cards_step_select": "പ്രസിദ്ധീകരണവും വിദ്യാർത്ഥികളും തിരഞ്ഞെടുക്കുക.",
    "exchange.report_cards_step_generate": "POST /api/v1/reportcards.",
    "exchange.report_cards_step_poll": "GET /api/v1/reportcards/{id} — ready ആകുന്നതുവരെ.",
    "exchange.report_cards_font_pending":
      "മലയാളം വാചകം ഫയലിൽ ഉണ്ട്; എന്നാൽ ഉൾച്ചേർത്ത മലയാളം ഫോണ്ട് ബണ്ടിൽ അംഗീകാരം കാത്തിരിക്കുന്നു.",
  },
} as const;
