"""Module policies, roles and grants written by ``install_school``.

Split from ``config/school_install.py`` by responsibility: that file installs
the school's structure; this one installs how each module behaves and who may
do what. Same idempotency rules apply.
"""

from __future__ import annotations

import uuid

from config.school_install import GRANTS_VALID_FROM, InstallReport, _stable_id

# --- module policies ------------------------------------------------------------


def _upsert(model, lookup: dict, values: dict, kind: str, report: InstallReport) -> None:
    """Create or update one policy row by its lookup keys; count real changes only."""
    row = model.objects.filter(**lookup).first()
    if row is None:
        model.objects.create(**lookup, **values)
        report.note(kind, True)
        return
    if all(getattr(row, name) == value for name, value in values.items()):
        return
    for name, value in values.items():
        setattr(row, name, value)
    row.save()
    report.note(kind, False)


def _install_policies(config, school_id, report) -> None:
    """Write each module's policy row from the config."""
    from modules.alumni.models import AlumniPolicy
    from modules.communications.models import CommunicationsPolicy
    from modules.exchange.models import ExchangePolicy
    from modules.files.models import FilesPolicy
    from modules.library.models import LibraryPolicy
    from modules.performance.models import MetricDefinition, WarningRule
    from modules.platform.models import PlatformPolicy

    library = config["library"]
    _upsert(
        LibraryPolicy,
        {"school_id": school_id},
        {
            "max_active_loans_per_borrower": library["max_active_loans_per_borrower"],
            "max_renewals_per_loan": library["max_renewals_per_loan"],
        },
        "library_policy",
        report,
    )
    files = config["files"]
    _upsert(
        FilesPolicy,
        {"school_id": school_id},
        {
            "max_bytes_per_page": int(files["max_megabytes_per_page"]) * 1024 * 1024,
            "max_batch_pages": files["max_pages_per_batch"],
            "long_edge_px": files["image_long_edge_px"],
            "grace_days": files["grace_days"],
        },
        "files_policy",
        report,
    )
    _upsert(
        CommunicationsPolicy,
        {"school_id": school_id},
        {
            "channels_enabled": list(config["communications"]["channels_enabled"]),
            "live_provider": "none",
            "sms_configure_requires_2fa": True,
        },
        "communications_policy",
        report,
    )
    alumni = config["alumni"]
    _upsert(
        AlumniPolicy,
        {"school_id": school_id},
        {
            "alumni_login_enabled": alumni["alumni_login_enabled"],
            "transfer_include_as_alumni": alumni["include_transfers_as_alumni"],
            "exportable_fields": list(alumni["exportable_fields"]),
        },
        "alumni_policy",
        report,
    )
    exchange = config["exchange"]
    _upsert(
        ExchangePolicy,
        {"school_id": school_id},
        {
            "commit_requires_2fa": exchange["commit_requires_2fa"],
            "commit_chunk_rows": exchange["commit_chunk_rows"],
        },
        "exchange_policy",
        report,
    )
    _upsert(
        PlatformPolicy,
        {"school_id": school_id},
        {"backup_age_alert_minutes": config["platform"]["backup_age_alert_minutes"]},
        "platform_policy",
        report,
    )
    _upsert(
        MetricDefinition,
        {"school_id": school_id, "code": "overall_mean", "version": 1},
        {"formula": "simple_mean_v1", "denominator": "100"},
        "metric_definition",
        report,
    )
    attendance = config["attendance"]
    rules = (
        (
            "low_attendance",
            f"{attendance['low_attendance_percent']:.2f}",
            attendance["low_attendance_minimum_days"],
        ),
        ("missing_work", str(attendance["missing_work_count"]), 1),
    )
    for code, threshold, minimum in rules:
        latest = WarningRule.objects.filter(school_id=school_id, code=code).order_by("-version")
        current = latest.first()
        if (
            current is not None
            and current.threshold == threshold
            and (current.minimum_samples == minimum)
        ):
            continue
        # Rules are versioned, never edited: warnings keep the version they used.
        WarningRule.objects.create(
            school_id=school_id,
            code=code,
            version=(current.version + 1) if current else 1,
            threshold=threshold,
            window="term",
            minimum_samples=minimum,
            exclusions=[],
        )
        report.note("warning_rule", current is None)


# --- access ---------------------------------------------------------------------


def _install_roles(config, school_id, now, report) -> None:
    """Create each configured role and replace its grants; refresh the owner's.

    Grants are validated against the live catalogue, so a typo in the file is an
    error rather than a silently useless grant.
    """
    from modules.access.models import Grant, Permission, Role
    from modules.access.permissions import full_catalogue, lookup_permission

    for spec in full_catalogue():
        Permission.objects.update_or_create(
            code=spec.code,
            defaults={
                "description": spec.description,
                "requires_recent_two_factor": spec.requires_recent_two_factor,
            },
        )

    unknown: list[str] = []
    for key, role_spec in config.get("roles", {}).items():
        for entry in role_spec["grants"]:
            action = entry.split("@", 1)[0]
            if lookup_permission(action) is None:
                unknown.append(f"roles.{key}: {action}")
    if unknown:
        raise ValueError(
            "unknown permission codes in school config:\n  " + "\n  ".join(unknown)
        )

    for key, role_spec in config.get("roles", {}).items():
        role_id = _stable_id(school_id, f"role.{key}")
        wanted = {
            (entry.partition("@")[0], _scope_for(entry).value) for entry in role_spec["grants"]
        }
        role = Role.objects.filter(id=role_id).first()
        created = role is None
        if created:
            role = Role.objects.create(
                id=role_id,
                school_id=school_id,
                name=role_spec["name"],
                is_owner_role=False,
                requires_two_factor=role_spec["requires_two_factor"],
                version=1,
                created_at=now,
                updated_at=now,
            )
        else:
            held = set(Grant.objects.filter(role=role).values_list("action", "scope_type"))
            unchanged = (
                role.name == role_spec["name"]
                and role.requires_two_factor == role_spec["requires_two_factor"]
                and held == wanted
            )
            if unchanged:
                continue
            role.name = role_spec["name"]
            role.requires_two_factor = role_spec["requires_two_factor"]
            role.version += 1
            role.updated_at = now
            role.save()
        report.note("role", created)
        Grant.objects.filter(role=role).delete()
        Grant.objects.bulk_create(
            [
                Grant(
                    school_id=school_id,
                    role=role,
                    action=action,
                    scope_type=scope_value,
                    scope_id=None,
                    valid_from=GRANTS_VALID_FROM,
                    valid_to=None,
                    created_at=now,
                )
                for action, scope_value in sorted(wanted)
            ]
        )

    # Owners hold every school-scoped action, including module actions added
    # since bootstrap_owner ran.
    owner_scopes = owner_grant_scopes()
    for owner_role in Role.objects.filter(school_id=school_id, is_owner_role=True):
        held = set(Grant.objects.filter(role=owner_role).values_list("action", flat=True))
        missing = sorted(set(owner_scopes) - held)
        Grant.objects.bulk_create(
            [
                Grant(
                    school_id=school_id,
                    role=owner_role,
                    action=action,
                    scope_type=owner_scopes[action].value,
                    scope_id=None,
                    valid_from=GRANTS_VALID_FROM,
                    valid_to=None,
                    created_at=now,
                )
                for action in missing
            ]
        )
        if missing:
            report.note("owner_grants_refreshed", False)


def _scope_for(entry: str):
    """Return the scope a config grant entry names: "code@self" or school-wide."""
    from modules.access.scopes import ScopeType

    return ScopeType.SELF if entry.partition("@")[2] == "self" else ScopeType.SCHOOL


def owner_grant_scopes() -> dict:
    """Return {action: scope} for everything an owner holds.

    School-wide where the action allows it, otherwise self-scoped (e.g.
    managing one's own second factor).
    """
    from modules.access.permissions import full_catalogue
    from modules.access.scopes import ScopeType

    return {
        spec.code: ScopeType.SCHOOL
        if ScopeType.SCHOOL in spec.allowed_scopes
        else ScopeType.SELF
        for spec in full_catalogue()
    }


def role_id_for(school_id: uuid.UUID, key: str) -> uuid.UUID:
    """Return the id install_school gives the role configured under ``key``."""
    return _stable_id(school_id, f"role.{key}")
