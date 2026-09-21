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
    "nav.accounts": "Accounts & logins",
    "access.accounts.title": "Accounts and logins",
    "access.accounts.intro": "Everyone who can sign in. Parent and staff logins are usually created from Admit a student and Staff & teaching.",
    "access.accounts.search": "Search by name or login",
    "access.accounts.name": "Name",
    "access.accounts.roles": "Roles",
    "access.accounts.status": "Status",
    "access.accounts.active": "Active",
    "access.accounts.inactive": "Deactivated",
    "access.accounts.no_2fa_yet": "2FA not set up yet",
    "access.accounts.change_roles": "Roles",
    "access.accounts.reset_password": "Reset password",
    "access.accounts.deactivate": "Deactivate",
    "access.accounts.activate": "Reactivate",
    "access.accounts.create_title": "Create another login",
    "access.accounts.create_help": "For someone who is not a student, parent or staff record, e.g. a second administrator.",
    "access.accounts.create": "Create login",
    "access.accounts.done": "Done",
    "access.password.title": "Change your password",
    "access.password.current": "Current password",
    "access.password.new": "New password (at least 10 characters)",
    "access.password.repeat": "Repeat new password",
    "access.password.mismatch": "The two new passwords do not match.",
    "access.password.changed": "Password changed. Other devices have been signed out.",
    "access.password.submit": "Change password",
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
    "access.enrol.scanQr": "Scan this QR code with your authenticator app",
    "access.enrol.scanQrHelp":
      "Open Aegis, Google Authenticator, or any TOTP app and scan the code. Prefer this over typing the key.",
    "access.enrol.manualSecret":
      "Or type this key into your authenticator by hand",
    "access.enrol.manualSecretHelp":
      "Use this if you cannot scan. Spaces are only for reading — use Copy key, or type the letters ignoring spaces.",
    "access.enrol.copySecret": "Copy key",
    "access.enrol.totpProfile":
      "App settings if asked: {digits} digits, {period}-second period, SHA-1.",
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
    "nav.accounts": "അക്കൗണ്ടുകൾ",
    "access.accounts.title": "അക്കൗണ്ടുകളും ലോഗിനുകളും",
    "access.accounts.intro": "സൈൻ ഇൻ ചെയ്യാൻ കഴിയുന്ന എല്ലാവരും. രക്ഷിതാക്കളുടെയും ജീവനക്കാരുടെയും ലോഗിനുകൾ സാധാരണയായി പ്രവേശന, ജീവനക്കാർ പേജുകളിൽ നിന്നാണ് സൃഷ്ടിക്കുന്നത്.",
    "access.accounts.search": "പേരോ ലോഗിനോ ഉപയോഗിച്ച് തിരയുക",
    "access.accounts.name": "പേര്",
    "access.accounts.roles": "റോളുകൾ",
    "access.accounts.status": "നില",
    "access.accounts.active": "സജീവം",
    "access.accounts.inactive": "നിർജ്ജീവം",
    "access.accounts.no_2fa_yet": "2FA ഇനിയും സജ്ജമാക്കിയിട്ടില്ല",
    "access.accounts.change_roles": "റോളുകൾ",
    "access.accounts.reset_password": "പാസ്‌വേഡ് പുനഃസജ്ജമാക്കുക",
    "access.accounts.deactivate": "നിർജ്ജീവമാക്കുക",
    "access.accounts.activate": "വീണ്ടും സജീവമാക്കുക",
    "access.accounts.create_title": "മറ്റൊരു ലോഗിൻ സൃഷ്ടിക്കുക",
    "access.accounts.create_help": "വിദ്യാർത്ഥിയോ രക്ഷിതാവോ ജീവനക്കാരനോ അല്ലാത്തവർക്ക്, ഉദാ. രണ്ടാമത്തെ അഡ്മിനിസ്ട്രേറ്റർ.",
    "access.accounts.create": "ലോഗിൻ സൃഷ്ടിക്കുക",
    "access.accounts.done": "പൂർത്തിയായി",
    "access.password.title": "പാസ്‌വേഡ് മാറ്റുക",
    "access.password.current": "നിലവിലെ പാസ്‌വേഡ്",
    "access.password.new": "പുതിയ പാസ്‌വേഡ് (കുറഞ്ഞത് 10 അക്ഷരങ്ങൾ)",
    "access.password.repeat": "പുതിയ പാസ്‌വേഡ് വീണ്ടും",
    "access.password.mismatch": "രണ്ട് പുതിയ പാസ്‌വേഡുകളും ഒന്നല്ല.",
    "access.password.changed": "പാസ്‌വേഡ് മാറ്റി. മറ്റ് ഉപകരണങ്ങളിൽ നിന്ന് സൈൻ ഔട്ട് ചെയ്തു.",
    "access.password.submit": "പാസ്‌വേഡ് മാറ്റുക",
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
    "access.enrol.scanQr": "ഈ QR കോഡ് നിങ്ങളുടെ ഓതന്റിക്കേറ്റർ ആപ്പിൽ സ്കാൻ ചെയ്യുക",
    "access.enrol.scanQrHelp":
      "Aegis, Google Authenticator അല്ലെങ്കിൽ ഏതെങ്കിലും TOTP ആപ്പ് തുറന്ന് കോഡ് സ്കാൻ ചെയ്യുക. കീ ടൈപ്പ് ചെയ്യുന്നതിനേക്കാൾ ഇത് നല്ലതാണ്.",
    "access.enrol.manualSecret":
      "അല്ലെങ്കിൽ ഈ കീ നിങ്ങളുടെ ഓതന്റിക്കേറ്ററിൽ കൈകൊണ്ട് ടൈപ്പ് ചെയ്യുക",
    "access.enrol.manualSecretHelp":
      "സ്കാൻ ചെയ്യാൻ കഴിയുന്നില്ലെങ്കിൽ ഇത് ഉപയോഗിക്കുക. സ്പേസുകൾ വായനയ്ക്ക് മാത്രം — Copy key ഉപയോഗിക്കുക, അല്ലെങ്കിൽ സ്പേസുകൾ അവഗണിച്ച് ടൈപ്പ് ചെയ്യുക.",
    "access.enrol.copySecret": "കീ പകർത്തുക",
    "access.enrol.totpProfile":
      "ചോദിച്ചാൽ ആപ്പ് ക്രമീകരണം: {digits} അക്കങ്ങൾ, {period} സെക്കൻഡ് കാലയളവ്, SHA-1.",
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
