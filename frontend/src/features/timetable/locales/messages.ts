/**
 * English and Malayalam strings for M03.
 *
 * The backend returns message KEYS only, so this is the only place human-readable
 * text for this module exists. Merged over the shared catalogue by useMessages.
 *
 * Every conflict code and every timetable.error.* key the frozen contract can
 * return has an entry here. A key without one renders as itself, which is visible
 * in a screenshot -- but a schedule screen that shows a reviewer
 * "timetable.conflict.teacher_double_booked" has failed at the job it exists for.
 */

import type { Language } from "@shared/i18n/messages";

export const TIMETABLE_MESSAGES: Record<Language, Record<string, string>> = {
  en: {
    "nav.timetable_editor": "Timetable planner",
    "planner.title": "Timetable planner",
    "planner.class": "Class",
    "planner.no_timetable": "There is no timetable for this year yet. Run install_school to create the bell schedule.",
    "planner.editing_draft": "Editing a draft. Nothing changes for teachers until you publish.",
    "planner.editing_published": "Showing the published timetable in force since",
    "planner.unsaved": "unsaved changes",
    "planner.clashes": "clashes to fix",
    "planner.who_teaches": "Who teaches this class",
    "planner.per_week": "a week",
    "planner.teacher_for": "Teacher for",
    "planner.no_teacher": "No teacher yet",
    "planner.add_subject": "Add a subject to this class",
    "planner.teacher_load_hint": "The number after each name is that teacher's periods a week across the school. Changing a teacher takes effect today and moves this class's periods to them.",
    "planner.teacher_saved": "Teacher updated.",
    "planner.day": "Day",
    "planner.period": "Period",
    "planner.free": "Free",
    "planner.clash_with": "Also in",
    "planner.busy_in": "Busy in",
    "planner.make_free": "Make it a free period",
    "planner.takes_effect": "Takes effect from",
    "planner.save_draft": "Save draft",
    "planner.draft_saved": "Draft saved.",
    "planner.publish": "Publish timetable",
    "planner.published": "Timetable published.",
    "planner.fix_clashes": "Fix the clashes marked in red first",
    "nav.timetable_substitutions": "Substitutions",
    "nav.timetable_class": "Class schedule",
    "nav.timetable_teacher": "My schedule",
    "nav.timetable_student": "Pupil schedule",

    "timetable.editor.title": "Weekly timetable",
    "timetable.editor.draft": "Draft",
    "timetable.editor.published": "Published",
    "timetable.editor.superseded": "Superseded",
    "timetable.editor.effectiveFrom": "Effective from",
    "timetable.editor.effectiveTo": "Effective to",
    "timetable.editor.openEnded": "No end date",
    "timetable.editor.period": "Period",
    "timetable.editor.section": "Class",
    "timetable.editor.subject": "Subject",
    "timetable.editor.teacher": "Teacher",
    "timetable.editor.room": "Room",
    "timetable.editor.free": "Free",
    "timetable.editor.checkConflicts": "Check for conflicts",
    "timetable.editor.noConflicts": "No conflicts. This version can be published.",
    "timetable.editor.conflicts": "Conflicts",
    "timetable.editor.blocking": "Blocks publication",
    "timetable.editor.advisory": "Worth checking",
    "timetable.editor.publish": "Publish",
    "timetable.editor.publishPreview": "Before you publish",
    "timetable.editor.publishExplains":
      "Publishing makes this the school's schedule from the effective date. The version in force until then is kept and stays readable.",
    "timetable.editor.published_ok": "Published. It takes effect from {date}.",
    "timetable.editor.supersedes": "Replaces the version in force until {date}.",
    "timetable.editor.versions": "Versions",

    "timetable.schedule.title": "Class schedule",
    "timetable.schedule.teacherTitle": "My schedule",
    "timetable.schedule.studentTitle": "Pupil schedule",
    "timetable.schedule.student": "Pupil",
    "timetable.schedule.date": "Date",
    "timetable.schedule.today": "Today",
    "timetable.schedule.notSchoolDay": "No lessons on this day.",
    "timetable.schedule.cancelled": "Cancelled",
    "timetable.schedule.substituteFor": "Covered by another teacher",
    "timetable.schedule.notEnrolled": "You do not take this subject",
    "timetable.schedule.show": "Show",

    "timetable.substitution.title": "Substitutions",
    "timetable.substitution.assign": "Assign a substitute",
    "timetable.substitution.substitute": "Substitute",
    "timetable.substitution.reason": "Reason",
    "timetable.substitution.validUntil": "Valid until",
    "timetable.substitution.expires":
      "A substitute's access ends at the end of that school day. It is not a standing permission.",
    "timetable.substitution.assigned": "Substitute assigned.",
    "timetable.substitution.withdraw": "Withdraw",
    "timetable.substitution.withdrawn": "Withdrawn.",
    "timetable.substitution.none": "No substitutions for this date.",

    "timetable.reason.holiday": "Holiday",
    "timetable.reason.exam": "Examination",
    "timetable.reason.event": "School event",
    "timetable.reason.no_periods": "Not a teaching day",
    "timetable.reason.cancelled": "Cancelled",
    "timetable.reason.unavailable": "Teacher unavailable",

    "timetable.conflict.teacher_double_booked":
      "This teacher is timetabled for two classes at the same time.",
    "timetable.conflict.section_double_booked":
      "This class is timetabled for two lessons at the same time.",
    "timetable.conflict.teacher_unavailable":
      "This teacher is recorded as unavailable during this period.",
    "timetable.conflict.period_overlap": "Two periods on this day overlap.",
    "timetable.conflict.slot_references_unknown_period":
      "A lesson refers to a period this version no longer has.",
    "timetable.conflict.section_unknown_to_registry":
      "This class is not in the school register.",
    "timetable.conflict.teacher_not_assigned":
      "The register has no teaching assignment for this teacher, class and subject.",

    "timetable.error.not_draft": "A published timetable cannot be edited. Create a new version.",
    "timetable.error.already_published": "This version has already been published.",
    "timetable.error.conflicts_present": "Resolve the conflicts before publishing.",
    "timetable.error.effective_from_not_after_effective":
      "A new version must start after the one currently in force.",
    "timetable.error.no_effective_timetable": "No timetable has been published for this date.",
    "timetable.error.date_is_holiday": "That date is a holiday, so it has no lessons.",
    "timetable.error.session_cancelled": "That lesson has been cancelled.",
    "timetable.error.substitution_exists": "That period already has a substitute.",
    "timetable.error.period_end_not_after_start": "A period must end after it starts.",
    "timetable.error.period_overlap": "Two periods on the same day overlap.",
    "timetable.error.duplicate_period": "Two periods on the same day have the same code.",
    "timetable.error.unknown_slot_code": "A lesson refers to a period that is not defined.",
    "timetable.error.duplicate_slot": "This class already has a lesson in that period.",
    "timetable.error.effective_to_before_from": "The end date is before the start date.",
    "timetable.error.unknown_section": "That class is not in the school register.",
    "timetable.error.unavailability_end_not_after_start":
      "The interval must end after it starts.",
    "timetable.error.slot_not_taught_on_date": "That lesson is not taught on that weekday.",
    "timetable.error.date_outside_effective_range":
      "That date is outside the published timetable.",
    "timetable.error.substitute_same_as_assigned":
      "A teacher cannot be their own substitute.",
    "timetable.error.valid_until_after_session_day":
      "A substitute's access cannot last beyond that school day.",
    "timetable.error.valid_until_before_session_end":
      "A substitute's access must last until the lesson ends.",
    "timetable.error.to_date_before_from_date": "The end date is before the start date.",
    "timetable.error.range_too_wide": "Choose a shorter range of dates.",
  },
  ml: {
    "nav.timetable_editor": "ടൈംടേബിൾ ആസൂത്രണം",
    "planner.title": "ടൈംടേബിൾ ആസൂത്രണം",
    "planner.class": "ക്ലാസ്",
    "planner.no_timetable": "ഈ വർഷത്തേക്ക് ടൈംടേബിൾ ഇല്ല.",
    "planner.editing_draft": "ഡ്രാഫ്റ്റ് തിരുത്തുന്നു. പ്രസിദ്ധീകരിക്കുന്നതുവരെ അധ്യാപകർക്ക് മാറ്റമില്ല.",
    "planner.editing_published": "പ്രസിദ്ധീകരിച്ച ടൈംടേബിൾ, നിലവിൽ വന്നത്",
    "planner.unsaved": "സംരക്ഷിക്കാത്ത മാറ്റങ്ങൾ",
    "planner.clashes": "പരിഹരിക്കേണ്ട കൂട്ടിമുട്ടലുകൾ",
    "planner.who_teaches": "ഈ ക്ലാസിൽ ആര് എന്ത് പഠിപ്പിക്കുന്നു",
    "planner.per_week": "ആഴ്ചയിൽ",
    "planner.teacher_for": "അധ്യാപകൻ:",
    "planner.no_teacher": "അധ്യാപകനില്ല",
    "planner.add_subject": "ഈ ക്ലാസിൽ വിഷയം ചേർക്കുക",
    "planner.teacher_load_hint": "പേരിന് ശേഷമുള്ള സംഖ്യ ആ അധ്യാപകന്റെ ആഴ്ചയിലെ ആകെ പീരിയഡുകൾ.",
    "planner.teacher_saved": "അധ്യാപകനെ മാറ്റി.",
    "planner.day": "ദിവസം",
    "planner.period": "പീരിയഡ്",
    "planner.free": "ഒഴിവ്",
    "planner.clash_with": "കൂടാതെ",
    "planner.busy_in": "തിരക്കിൽ:",
    "planner.make_free": "ഒഴിവ് പീരിയഡ് ആക്കുക",
    "planner.takes_effect": "നിലവിൽ വരുന്നത്",
    "planner.save_draft": "ഡ്രാഫ്റ്റ് സംരക്ഷിക്കുക",
    "planner.draft_saved": "ഡ്രാഫ്റ്റ് സംരക്ഷിച്ചു.",
    "planner.publish": "ടൈംടേബിൾ പ്രസിദ്ധീകരിക്കുക",
    "planner.published": "ടൈംടേബിൾ പ്രസിദ്ധീകരിച്ചു.",
    "planner.fix_clashes": "ചുവപ്പിൽ കാണിച്ച കൂട്ടിമുട്ടലുകൾ ആദ്യം പരിഹരിക്കുക",
    "nav.timetable_substitutions": "പകരം അധ്യാപകർ",
    "nav.timetable_class": "ക്ലാസ് സമയക്രമം",
    "nav.timetable_teacher": "എന്റെ സമയക്രമം",
    "nav.timetable_student": "വിദ്യാർഥിയുടെ സമയക്രമം",

    "timetable.editor.title": "ആഴ്ചത്തെ സമയക്രമം",
    "timetable.editor.draft": "കരട്",
    "timetable.editor.published": "പ്രസിദ്ധീകരിച്ചു",
    "timetable.editor.superseded": "പഴയത്",
    "timetable.editor.effectiveFrom": "പ്രാബല്യത്തിൽ വരുന്ന തീയതി",
    "timetable.editor.effectiveTo": "അവസാന തീയതി",
    "timetable.editor.openEnded": "അവസാന തീയതി ഇല്ല",
    "timetable.editor.period": "പിരീഡ്",
    "timetable.editor.section": "ക്ലാസ്",
    "timetable.editor.subject": "വിഷയം",
    "timetable.editor.teacher": "അധ്യാപകൻ",
    "timetable.editor.room": "മുറി",
    "timetable.editor.free": "ഒഴിവ്",
    "timetable.editor.checkConflicts": "പൊരുത്തക്കേടുകൾ പരിശോധിക്കുക",
    "timetable.editor.noConflicts":
      "പൊരുത്തക്കേടുകളില്ല. ഈ പതിപ്പ് പ്രസിദ്ധീകരിക്കാം.",
    "timetable.editor.conflicts": "പൊരുത്തക്കേടുകൾ",
    "timetable.editor.blocking": "പ്രസിദ്ധീകരണം തടയുന്നു",
    "timetable.editor.advisory": "പരിശോധിക്കേണ്ടത്",
    "timetable.editor.publish": "പ്രസിദ്ധീകരിക്കുക",
    "timetable.editor.publishPreview": "പ്രസിദ്ധീകരിക്കുന്നതിന് മുമ്പ്",
    "timetable.editor.publishExplains":
      "പ്രസിദ്ധീകരിച്ചാൽ ആ തീയതി മുതൽ ഇതാണ് സ്കൂളിന്റെ സമയക്രമം. അതുവരെ പ്രാബല്യത്തിലുള്ള പതിപ്പ് നിലനിർത്തും, വായിക്കാനും കഴിയും.",
    "timetable.editor.published_ok": "പ്രസിദ്ധീകരിച്ചു. {date} മുതൽ പ്രാബല്യത്തിൽ.",
    "timetable.editor.supersedes": "{date} വരെ പ്രാബല്യത്തിലുള്ള പതിപ്പിന് പകരം.",
    "timetable.editor.versions": "പതിപ്പുകൾ",

    "timetable.schedule.title": "ക്ലാസ് സമയക്രമം",
    "timetable.schedule.teacherTitle": "എന്റെ സമയക്രമം",
    "timetable.schedule.studentTitle": "വിദ്യാർഥിയുടെ സമയക്രമം",
    "timetable.schedule.student": "വിദ്യാർഥി",
    "timetable.schedule.date": "തീയതി",
    "timetable.schedule.today": "ഇന്ന്",
    "timetable.schedule.notSchoolDay": "ഈ ദിവസം ക്ലാസുകളില്ല.",
    "timetable.schedule.cancelled": "റദ്ദാക്കി",
    "timetable.schedule.substituteFor": "മറ്റൊരു അധ്യാപകൻ എടുക്കുന്നു",
    "timetable.schedule.notEnrolled": "ഈ വിഷയം നിങ്ങൾ പഠിക്കുന്നില്ല",
    "timetable.schedule.show": "കാണിക്കുക",

    "timetable.substitution.title": "പകരം അധ്യാപകർ",
    "timetable.substitution.assign": "പകരം അധ്യാപകനെ നിയോഗിക്കുക",
    "timetable.substitution.substitute": "പകരം അധ്യാപകൻ",
    "timetable.substitution.reason": "കാരണം",
    "timetable.substitution.validUntil": "സാധുത",
    "timetable.substitution.expires":
      "പകരം അധ്യാപകന്റെ അനുമതി ആ സ്കൂൾ ദിവസം അവസാനിക്കുമ്പോൾ തീരും. ഇത് സ്ഥിരമായ അനുമതിയല്ല.",
    "timetable.substitution.assigned": "പകരം അധ്യാപകനെ നിയോഗിച്ചു.",
    "timetable.substitution.withdraw": "പിൻവലിക്കുക",
    "timetable.substitution.withdrawn": "പിൻവലിച്ചു.",
    "timetable.substitution.none": "ഈ തീയതിയിൽ പകരം അധ്യാപകരില്ല.",

    "timetable.reason.holiday": "അവധി",
    "timetable.reason.exam": "പരീക്ഷ",
    "timetable.reason.event": "സ്കൂൾ പരിപാടി",
    "timetable.reason.no_periods": "ക്ലാസ് ദിവസമല്ല",
    "timetable.reason.cancelled": "റദ്ദാക്കി",
    "timetable.reason.unavailable": "അധ്യാപകൻ ലഭ്യമല്ല",

    "timetable.conflict.teacher_double_booked":
      "ഈ അധ്യാപകന് ഒരേ സമയം രണ്ട് ക്ലാസുകൾ നൽകിയിരിക്കുന്നു.",
    "timetable.conflict.section_double_booked":
      "ഈ ക്ലാസിന് ഒരേ സമയം രണ്ട് പിരീഡുകൾ നൽകിയിരിക്കുന്നു.",
    "timetable.conflict.teacher_unavailable":
      "ഈ പിരീഡിൽ അധ്യാപകൻ ലഭ്യമല്ലെന്ന് രേഖപ്പെടുത്തിയിട്ടുണ്ട്.",
    "timetable.conflict.period_overlap": "ഈ ദിവസത്തെ രണ്ട് പിരീഡുകൾ ഒന്നിച്ചു വരുന്നു.",
    "timetable.conflict.slot_references_unknown_period":
      "ഈ പതിപ്പിൽ ഇല്ലാത്ത പിരീഡിനെ ഒരു ക്ലാസ് പരാമർശിക്കുന്നു.",
    "timetable.conflict.section_unknown_to_registry":
      "ഈ ക്ലാസ് സ്കൂൾ രജിസ്റ്ററിൽ ഇല്ല.",
    "timetable.conflict.teacher_not_assigned":
      "ഈ അധ്യാപകന്, ക്ലാസിന്, വിഷയത്തിന് രജിസ്റ്ററിൽ നിയമനം രേഖപ്പെടുത്തിയിട്ടില്ല.",

    "timetable.error.not_draft":
      "പ്രസിദ്ധീകരിച്ച സമയക്രമം തിരുത്താനാകില്ല. പുതിയ പതിപ്പ് ഉണ്ടാക്കുക.",
    "timetable.error.already_published": "ഈ പതിപ്പ് നേരത്തെ പ്രസിദ്ധീകരിച്ചതാണ്.",
    "timetable.error.conflicts_present":
      "പ്രസിദ്ധീകരിക്കുന്നതിന് മുമ്പ് പൊരുത്തക്കേടുകൾ പരിഹരിക്കുക.",
    "timetable.error.effective_from_not_after_effective":
      "പുതിയ പതിപ്പ് ഇപ്പോഴത്തെ പതിപ്പിന് ശേഷമേ ആരംഭിക്കാവൂ.",
    "timetable.error.no_effective_timetable":
      "ഈ തീയതിയിലേക്ക് സമയക്രമം പ്രസിദ്ധീകരിച്ചിട്ടില്ല.",
    "timetable.error.date_is_holiday": "ആ ദിവസം അവധിയാണ്, ക്ലാസുകളില്ല.",
    "timetable.error.session_cancelled": "ആ പിരീഡ് റദ്ദാക്കിയിട്ടുണ്ട്.",
    "timetable.error.substitution_exists": "ആ പിരീഡിന് ഇതിനകം പകരം അധ്യാപകനുണ്ട്.",
    "timetable.error.period_end_not_after_start":
      "പിരീഡ് ആരംഭത്തിന് ശേഷമേ അവസാനിക്കാവൂ.",
    "timetable.error.period_overlap": "ഒരേ ദിവസത്തെ രണ്ട് പിരീഡുകൾ ഒന്നിച്ചു വരുന്നു.",
    "timetable.error.duplicate_period":
      "ഒരേ ദിവസത്തെ രണ്ട് പിരീഡുകൾക്ക് ഒരേ കോഡാണ്.",
    "timetable.error.unknown_slot_code":
      "നിർവചിക്കാത്ത പിരീഡിനെ ഒരു ക്ലാസ് പരാമർശിക്കുന്നു.",
    "timetable.error.duplicate_slot": "ആ പിരീഡിൽ ഈ ക്ലാസിന് ഇതിനകം ഒരു വിഷയമുണ്ട്.",
    "timetable.error.effective_to_before_from": "അവസാന തീയതി ആരംഭ തീയതിക്ക് മുമ്പാണ്.",
    "timetable.error.unknown_section": "ആ ക്ലാസ് സ്കൂൾ രജിസ്റ്ററിൽ ഇല്ല.",
    "timetable.error.unavailability_end_not_after_start":
      "ഇടവേള ആരംഭത്തിന് ശേഷമേ അവസാനിക്കാവൂ.",
    "timetable.error.slot_not_taught_on_date": "ആ ആഴ്ചദിവസം ഈ പിരീഡ് ഇല്ല.",
    "timetable.error.date_outside_effective_range":
      "ആ തീയതി പ്രസിദ്ധീകരിച്ച സമയക്രമത്തിന് പുറത്താണ്.",
    "timetable.error.substitute_same_as_assigned":
      "ഒരു അധ്യാപകന് സ്വയം പകരക്കാരനാകാൻ കഴിയില്ല.",
    "timetable.error.valid_until_after_session_day":
      "പകരം അധ്യാപകന്റെ അനുമതി ആ സ്കൂൾ ദിവസത്തിനപ്പുറം നീട്ടാനാകില്ല.",
    "timetable.error.valid_until_before_session_end":
      "ക്ലാസ് തീരുന്നതുവരെ പകരം അധ്യാപകന്റെ അനുമതി നിലനിൽക്കണം.",
    "timetable.error.to_date_before_from_date": "അവസാന തീയതി ആരംഭ തീയതിക്ക് മുമ്പാണ്.",
    "timetable.error.range_too_wide": "കുറച്ച് ദിവസങ്ങളുടെ പരിധി തിരഞ്ഞെടുക്കുക.",
  },
};
