"""Install the school's buses and bus fees from the config file's [transport].

Each bus gets a fee plan (marked as transport, carrying the part-month rule)
under one "Bus fee" head, and the bus remembers its plan so adding a pupil
needs only the bus. Changing a bus's fee in the file creates a new plan for
new pupils; pupils already on the bus keep the plan they joined under.

Idempotent: buses are matched by name; nothing is ever deleted (a bus removed
from the file stays, and can be set inactive).
Does not handle: routes and stops (one name per bus), or per-pupil fees.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

PART_MONTH_RULES = ("daily", "full")
TRANSPORT_HEAD = "TRANSPORT"


def validate_transport(config: dict[str, Any]) -> list[str]:
    """Return problems with the [transport] section (empty when fine or absent)."""
    transport = config.get("transport") or {}
    problems = []
    if transport and transport.get("part_month", "daily") not in PART_MONTH_RULES:
        problems.append("transport.part_month must be 'daily' or 'full'")
    labels = [bus["label"] for bus in transport.get("buses", [])]
    if len(labels) != len(set(labels)):
        problems.append("transport.buses labels must be unique")
    for bus in transport.get("buses", []):
        if int(bus.get("monthly_fee", transport.get("monthly_fee", 0))) <= 0:
            problems.append(f"bus {bus['label']!r} needs a monthly_fee above 0")
    return problems


def install_transport(
    config: dict[str, Any], school_id: uuid.UUID, now: datetime, report
) -> None:
    """Create or update buses and their fee plans. Assumes a transaction."""
    from django.db.models import Max

    from modules.fees.models import FeeHead, FeePlan
    from modules.transport.models import Bus

    transport = config.get("transport") or {}
    buses = transport.get("buses", [])
    if not buses:
        return
    rule = transport.get("part_month", "daily")
    head, created = FeeHead.objects.get_or_create(
        school_id=school_id,
        code=TRANSPORT_HEAD,
        defaults={"label_key": "Bus fee", "version": 1},
    )
    report.note("fee_head", created)
    for spec in buses:
        amount = int(spec.get("monthly_fee", transport.get("monthly_fee"))) * 100
        bus = Bus.objects.filter(school_id=school_id, label=spec["label"]).first()
        if bus is None:
            bus = Bus.objects.create(
                school_id=school_id, label=spec["label"], active=True, version=1
            )
            report.note("bus", True)
        if bus.fee_plan_id and bus.monthly_fee_paise == amount:
            plan = FeePlan.objects.filter(id=bus.fee_plan_id).first()
            if plan is not None and (plan.applicability or {}).get("proration") == rule:
                continue
        latest = FeePlan.objects.filter(school_id=school_id).aggregate(Max("version"))
        version = (latest["version__max"] or 0) + 1
        plan = FeePlan.objects.create(
            school_id=school_id,
            version=version,
            applicability={"kind": "transport", "bus": spec["label"], "proration": rule},
            schedule=[{"fee_head_id": str(head.id), "amount_paise": amount, "due_date": ""}],
        )
        bus.fee_plan_id = plan.id
        bus.monthly_fee_paise = amount
        bus.version += 1
        bus.save(update_fields=["fee_plan_id", "monthly_fee_paise", "version"])
        report.note("bus_fee_plan", True)
