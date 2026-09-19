/**
 * English and Malayalam strings for M01.
 *
 * The backend returns message KEYS only, so this is the only place human-readable
 * text for this module exists. Merged into the shared catalogue by the app shell.
 *
 * The enrolment copy deliberately says a student does not need to own a phone: any
 * authenticator app on a shared or school device works, and a screen that assumes
 * personal phone ownership would exclude pupils.
 */

import type { Language } from "@shared/i18n/messages";

export const ACCESS_MESSAGES: Record<Language, Record<string, string>> = {
  en: {
    "access.login.title": "Sign in",
    "access.login.name": "Login name",
    "access.login.password": "Password",
    "access.login.submit": "Continue",
    "access.login.helper":
      "Your school gives you this login name. It is not your email address.",
    "access.challenge.title": "Enter your 6-digit code",
    "access.challenge.helper":
      "Open your authenticator app and type the current code.",
    "access.challenge.code": "6-digit code",
    "access.challenge.submit": "Verify",
    "access.challenge.lostDevice": "I do not have my authenticator",
    "access.challenge.useRecovery": "Use a recovery code instead",
    "access.challenge.recoveryCode": "Recovery code",
    "access.enrol.title": "Set up your authenticator",
    "access.enrol.intro":
      "Your school requires a second step when you sign in.",
    "access.enrol.noPhoneNote":
      "You do not need your own phone. Any authenticator app, on a shared or school device, will work. Ask your teacher if you need help.",
    "access.enrol.manualSecret":
      "Or type this key into your authenticator by hand",
    "access.enrol.manualSecretHelp":
      "Use this if you cannot scan a code. Type it exactly, ignoring spaces.",
    "access.enrol.confirmCode": "Now enter the code your app shows",
    "access.enrol.confirm": "Activate",
    "access.enrol.password": "Confirm your password",
    "access.recovery.title": "Save your recovery codes",
    "access.recovery.intro":
      "These ten codes are shown once and never again. Each one works a single time.",
    "access.recovery.warning":
      "Nobody can show them to you later, not even your school office. Keep them somewhere safe and private.",
    "access.recovery.download": "Download codes",
    "access.recovery.done": "I have saved them",
    "access.sessions.title": "Where you are signed in",
    "access.sessions.current": "This device",
    "access.sessions.lastSeen": "Last used",
    "access.sessions.revoke": "Sign out",
    "access.sessions.revoked": "Signed out",
    "access.roles.title": "Roles",
    "access.roles.name": "Role",
    "access.roles.grants": "Permissions",
    "access.roles.version": "Version",
    "access.roles.ownerRole": "Owner role",
    "access.roles.requiresTwoFactor": "Second step required",
    "access.roles.save": "Save permissions",
    "access.roles.conflict":
      "Someone else changed this role. Reload and try again.",
    "access.security.title": "Security",
    "access.security.factorActive": "Authenticator active",
    "access.security.factorNone": "No authenticator set up",
    "access.security.setUp": "Set up authenticator",
    "access.lostDevice.title": "Request help signing in",
    "access.lostDevice.intro":
      "Someone at your school must confirm who you are before your authenticator is reset. This does not happen by text message.",
    "access.lostDevice.reason": "What happened?",
    "access.lostDevice.submit": "Send request",
    "access.lostDevice.sent":
      "Your request has been sent. Someone at your school will review it.",
    "nav.security": "Security",
    "nav.roles": "Roles",
  },
  ml: {
    "access.login.title": "സൈൻ ഇൻ ചെയ്യുക",
    "access.login.name": "ലോഗിൻ പേര്",
    "access.login.password": "പാസ്‌വേഡ്",
    "access.login.submit": "തുടരുക",
    "access.login.helper":
      "നിങ്ങളുടെ സ്കൂൾ നൽകുന്ന ലോഗിൻ പേരാണിത്. ഇത് ഇമെയിൽ വിലാസമല്ല.",
    "access.challenge.title": "6 അക്ക കോഡ് നൽകുക",
    "access.challenge.helper":
      "നിങ്ങളുടെ ഓതന്റിക്കേറ്റർ ആപ്പ് തുറന്ന് ഇപ്പോഴുള്ള കോഡ് ടൈപ്പ് ചെയ്യുക.",
    "access.challenge.code": "6 അക്ക കോഡ്",
    "access.challenge.submit": "പരിശോധിക്കുക",
    "access.challenge.lostDevice": "എന്റെ ഓതന്റിക്കേറ്റർ എന്റെ കൈയിലില്ല",
    "access.challenge.useRecovery": "പകരം ഒരു വീണ്ടെടുക്കൽ കോഡ് ഉപയോഗിക്കുക",
    "access.challenge.recoveryCode": "വീണ്ടെടുക്കൽ കോഡ്",
    "access.enrol.title": "നിങ്ങളുടെ ഓതന്റിക്കേറ്റർ സജ്ജമാക്കുക",
    "access.enrol.intro":
      "സൈൻ ഇൻ ചെയ്യുമ്പോൾ രണ്ടാമത്തെ ഘട്ടം നിങ്ങളുടെ സ്കൂൾ ആവശ്യപ്പെടുന്നു.",
    "access.enrol.noPhoneNote":
      "നിങ്ങൾക്ക് സ്വന്തം ഫോൺ ആവശ്യമില്ല. പങ്കിട്ട അല്ലെങ്കിൽ സ്കൂൾ ഉപകരണത്തിലെ ഏതെങ്കിലും ഓതന്റിക്കേറ്റർ ആപ്പ് പ്രവർത്തിക്കും. സഹായം വേണമെങ്കിൽ അധ്യാപകനോട് ചോദിക്കുക.",
    "access.enrol.manualSecret":
      "അല്ലെങ്കിൽ ഈ കീ നിങ്ങളുടെ ഓതന്റിക്കേറ്ററിൽ കൈകൊണ്ട് ടൈപ്പ് ചെയ്യുക",
    "access.enrol.manualSecretHelp":
      "കോഡ് സ്കാൻ ചെയ്യാൻ കഴിയുന്നില്ലെങ്കിൽ ഇത് ഉപയോഗിക്കുക. സ്പേസുകൾ അവഗണിച്ച് കൃത്യമായി ടൈപ്പ് ചെയ്യുക.",
    "access.enrol.confirmCode": "ഇനി നിങ്ങളുടെ ആപ്പ് കാണിക്കുന്ന കോഡ് നൽകുക",
    "access.enrol.confirm": "സജീവമാക്കുക",
    "access.enrol.password": "നിങ്ങളുടെ പാസ്‌വേഡ് സ്ഥിരീകരിക്കുക",
    "access.recovery.title": "നിങ്ങളുടെ വീണ്ടെടുക്കൽ കോഡുകൾ സൂക്ഷിക്കുക",
    "access.recovery.intro":
      "ഈ പത്ത് കോഡുകൾ ഒരിക്കൽ മാത്രം കാണിക്കും, പിന്നീടൊരിക്കലും ഇല്ല. ഓരോന്നും ഒരു തവണ മാത്രം പ്രവർത്തിക്കും.",
    "access.recovery.warning":
      "പിന്നീട് ഇവ ആർക്കും നിങ്ങൾക്ക് കാണിച്ചുതരാൻ കഴിയില്ല, സ്കൂൾ ഓഫീസിനും കഴിയില്ല. സുരക്ഷിതവും സ്വകാര്യവുമായ ഒരിടത്ത് സൂക്ഷിക്കുക.",
    "access.recovery.download": "കോഡുകൾ ഡൗൺലോഡ് ചെയ്യുക",
    "access.recovery.done": "ഞാൻ ഇവ സൂക്ഷിച്ചു",
    "access.sessions.title": "നിങ്ങൾ സൈൻ ഇൻ ചെയ്തിരിക്കുന്ന ഇടങ്ങൾ",
    "access.sessions.current": "ഈ ഉപകരണം",
    "access.sessions.lastSeen": "അവസാനം ഉപയോഗിച്ചത്",
    "access.sessions.revoke": "സൈൻ ഔട്ട് ചെയ്യുക",
    "access.sessions.revoked": "സൈൻ ഔട്ട് ചെയ്തു",
    "access.roles.title": "റോളുകൾ",
    "access.roles.name": "റോൾ",
    "access.roles.grants": "അനുമതികൾ",
    "access.roles.version": "പതിപ്പ്",
    "access.roles.ownerRole": "ഉടമ റോൾ",
    "access.roles.requiresTwoFactor": "രണ്ടാമത്തെ ഘട്ടം ആവശ്യമാണ്",
    "access.roles.save": "അനുമതികൾ സംരക്ഷിക്കുക",
    "access.roles.conflict":
      "മറ്റൊരാൾ ഈ റോൾ മാറ്റി. വീണ്ടും ലോഡ് ചെയ്ത് ശ്രമിക്കുക.",
    "access.security.title": "സുരക്ഷ",
    "access.security.factorActive": "ഓതന്റിക്കേറ്റർ സജീവമാണ്",
    "access.security.factorNone": "ഓതന്റിക്കേറ്റർ സജ്ജമാക്കിയിട്ടില്ല",
    "access.security.setUp": "ഓതന്റിക്കേറ്റർ സജ്ജമാക്കുക",
    "access.lostDevice.title": "സൈൻ ഇൻ ചെയ്യാൻ സഹായം അഭ്യർത്ഥിക്കുക",
    "access.lostDevice.intro":
      "നിങ്ങളുടെ ഓതന്റിക്കേറ്റർ പുനഃസജ്ജമാക്കുന്നതിന് മുൻപ് നിങ്ങൾ ആരാണെന്ന് സ്കൂളിലെ ഒരാൾ സ്ഥിരീകരിക്കണം. ഇത് സന്ദേശം വഴി നടക്കില്ല.",
    "access.lostDevice.reason": "എന്ത് സംഭവിച്ചു?",
    "access.lostDevice.submit": "അഭ്യർത്ഥന അയയ്ക്കുക",
    "access.lostDevice.sent":
      "നിങ്ങളുടെ അഭ്യർത്ഥന അയച്ചു. സ്കൂളിലെ ഒരാൾ ഇത് പരിശോധിക്കും.",
    "nav.security": "സുരക്ഷ",
    "nav.roles": "റോളുകൾ",
  },
};
