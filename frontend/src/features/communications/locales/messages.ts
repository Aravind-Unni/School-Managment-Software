/** en/ml strings for M11 communications. */

export const COMMUNICATIONS_MESSAGES = {
  en: {
    "nav.notices": "Notices",
    "nav.templates": "Message templates",
    "nav.deliveries": "Deliveries",
    "communications.notices_title": "Notice composer",
    "communications.notices_help":
      "Draft notices via POST /api/v1/notices; publish with expected_version to snapshot the audience. In-app notices stay available when SMS is down.",
    "communications.templates_title": "Bilingual templates",
    "communications.templates_help":
      "English and Malayalam templates share a key. Unicode Malayalam is preserved through render and the fake provider.",
    "communications.deliveries_title": "Delivery status",
    "communications.deliveries_help":
      "Track queued, accepted, failed and unknown states. Timeout reconciles via provider lookup before any resend.",
  },
  ml: {
    "nav.notices": "അറിയിപ്പുകൾ",
    "nav.templates": "സന്ദേശ ടെംപ്ലേറ്റുകൾ",
    "nav.deliveries": "ഡെലിവറികൾ",
    "communications.notices_title": "അറിയിപ്പ് രചന",
    "communications.notices_help":
      "POST /api/v1/notices വഴി ഡ്രാഫ്റ്റ്; expected_version ഉപയോഗിച്ച് പ്രസിദ്ധീകരിക്കുക. SMS തകരാറിലായാലും ഇൻ-ആപ്പ് അറിയിപ്പ് ലഭ്യമാണ്.",
    "communications.templates_title": "ദ്വിഭാഷാ ടെംപ്ലേറ്റുകൾ",
    "communications.templates_help":
      "ഇംഗ്ലീഷും മലയാളവും ഒരേ കീ പങ്കിടുന്നു. മലയാള യൂണികോഡ് സംരക്ഷിക്കപ്പെടുന്നു.",
    "communications.deliveries_title": "ഡെലിവറി നില",
    "communications.deliveries_help":
      "queued, accepted, failed, unknown നിലകൾ. ടൈംഔട്ടിന് ശേഷം വീണ്ടും അയയ്ക്കുന്നതിന് മുമ്പ് lookup.",
  },
} as const;
