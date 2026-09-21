"""Scenario ids from contracts/M14 fixtures."""

from __future__ import annotations

import json
import pathlib
from uuid import UUID

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCENARIO_PATH = REPO_ROOT / "contracts" / "M14" / "fixtures" / "scenario.json"


def load_scenario() -> dict:
    """Load the frozen M14 scenario fixture."""
    return json.loads(SCENARIO_PATH.read_text())


_SCENARIO = load_scenario()
_SCHOOL_A = _SCENARIO["school_a"]
_SCHOOL_B = _SCENARIO["school_b"]
_POLICY = _SCENARIO["policy_fixture"]

SCHOOL_A = UUID(_SCHOOL_A["school_id"])
SCHOOL_B = UUID(_SCHOOL_B["school_id"])
OPERATOR_ACTOR = UUID(_SCHOOL_A["operator_actor_id"])
SCHOOL_ADMIN_ACTOR = UUID(_SCHOOL_A["school_admin_actor_id"])
UNRELATED_ACTOR = UUID(_SCHOOL_A["unrelated_actor_id"])
COMPANY_OPS_ACTOR = UUID(_SCHOOL_A["company_ops_actor_id"])
JOB_FAILED = UUID(_SCHOOL_A["job_failed"])
JOB_RUNNING = UUID(_SCHOOL_A["job_running"])
AUDIT_WITH_SECRET = UUID(_SCHOOL_A["audit_with_secret"])
BACKUP_MANIFEST_ID = UUID(_SCHOOL_A["backup_manifest_id"])
SAMPLE_OBJECT_SHA256 = _SCHOOL_A["sample_object_sha256"]
SAMPLE_FEE_TOTAL_PAISE = int(_SCHOOL_A["sample_fee_total_paise"])
JOB_FOREIGN = UUID(_SCHOOL_B["job_foreign"])
BACKUP_MANIFEST_FOREIGN = UUID(_SCHOOL_B["backup_manifest_foreign"])

SECRET_KEYS_REDACTED = frozenset(_POLICY["secret_keys_redacted"])
PRODUCTION_TARGET_LABELS = frozenset(_POLICY["production_target_labels"])
JOB_KINDS_ALLOWLIST = frozenset(_POLICY["job_kinds_allowlist"])
BACKUP_AGE_ALERT_MINUTES = int(_POLICY["backup_age_alert_minutes"])
