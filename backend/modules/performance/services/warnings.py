"""Warning rule evaluation, acknowledge/dismiss and dedupe."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import (
    Projection,
    WarningHistory,
    WarningRule,
    WarningState,
)
from ..models import (
    Warning as WarningRow,
)
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class WarningService:
    """Open, acknowledge and dismiss warnings with audit/outbox."""

    gate: AuthorityGate
    platform: object
    clock: object

    def create_rule(
        self,
        context: RequestContext,
        *,
        code: str,
        threshold: str,
        window: str,
        minimum_samples: int,
        exclusions: list[str] | None = None,
    ) -> WarningRule:
        """Create the next version of a warning rule for this school."""
        self.gate.require_staff_action(context, "warnings.manage")
        prior = (
            WarningRule.objects.filter(school_id=context.school_id, code=code)
            .order_by("-version")
            .first()
        )
        version = (prior.version + 1) if prior else 1
        now = self.clock.now()
        with transaction.atomic():
            rule = WarningRule.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                code=code,
                version=version,
                threshold=threshold,
                window=window,
                minimum_samples=minimum_samples,
                exclusions=list(exclusions or []),
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="warning_rule.created",
                    resource_id=rule.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"code": code, "version": version},
                )
            )
        return rule

    def evaluate_student(
        self,
        context: RequestContext,
        student_id: UUID,
        *,
        window: str = "term",
    ) -> list[WarningRow]:
        """Open warnings from the latest projection; dedupe by fingerprint."""
        projection = Projection.objects.filter(
            school_id=context.school_id,
            student_id=student_id,
            window=window,
            subject_id=None,
        ).first()
        if projection is None:
            return []
        rules = WarningRule.objects.filter(school_id=context.school_id)
        # Latest version per code.
        latest: dict[str, WarningRule] = {}
        for rule in rules.order_by("code", "-version"):
            if rule.code not in latest:
                latest[rule.code] = rule
        opened: list[WarningRow] = []
        for rule in latest.values():
            warning = self._maybe_open(context, student_id, rule, projection)
            if warning is not None:
                opened.append(warning)
        return opened

    def _maybe_open(
        self,
        context: RequestContext,
        student_id: UUID,
        rule: WarningRule,
        projection: Projection,
    ) -> WarningRow | None:
        """Open one warning when the rule fires; None when skipped or duplicate."""
        metrics = projection.metrics_json
        fingerprint = f"{rule.code}:{student_id}:{rule.window}:{rule.version}"
        existing = WarningRow.objects.filter(
            school_id=context.school_id,
            fingerprint=fingerprint,
            state__in=[WarningState.OPEN, WarningState.ACKNOWLEDGED],
        ).first()
        if existing is not None:
            return None

        if rule.code == "low_attendance":
            att = metrics.get("attendance_percentage") or {}
            if att.get("status") == "incomplete":
                return None
            if att.get("status") != "ok" or att.get("value") is None:
                return None
            # Attendance sample floor uses eligible via status already.
            if Decimal(att["value"]) >= Decimal(rule.threshold):
                return None
            explanation = "performance.warning.low_attendance"
            source_refs = [
                f"attendance:{att['value']}",
                f"policy:{projection.source_versions.get('attendance_policy_version')}",
            ]
        elif rule.code == "missing_work":
            # Seeded assignment missing drives this; projections store under source.
            missing = int(projection.source_versions.get("missing_assignments") or 0)
            if missing < int(rule.threshold):
                return None
            explanation = "performance.warning.missing_work"
            source_refs = [f"missing:{missing}"]
        else:
            return None

        now = self.clock.now()
        with transaction.atomic():
            warning = WarningRow.objects.create(
                id=uuid4(),
                school_id=context.school_id,
                student_id=student_id,
                rule=rule,
                rule_version=rule.version,
                state=WarningState.OPEN,
                version=1,
                source_refs=source_refs,
                explanation_key=explanation,
                fingerprint=fingerprint,
                opened_at=now,
                updated_at=now,
            )
            WarningHistory.objects.create(
                id=uuid4(),
                warning=warning,
                from_state="",
                to_state=WarningState.OPEN,
                reason="opened_by_rule",
                actor_id=context.actor_id,
                at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="warning.opened",
                    resource_id=warning.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"student_id": str(student_id), "rule": rule.code},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid4(),
                    school_id=context.school_id,
                    event_type="performance.warning_opened",
                    occurred_at=now,
                    aggregate_id=warning.id,
                    aggregate_version=warning.version,
                    payload={
                        "warning_id": str(warning.id),
                        "student_id": str(student_id),
                        "rule_version": rule.version,
                    },
                    correlation_id=context.request_id,
                )
            )
        return warning

    def acknowledge(
        self,
        context: RequestContext,
        warning_id: UUID,
        *,
        reason: str,
        expected_version: int,
    ) -> WarningRow:
        """Move open → acknowledged."""
        return self._transition(
            context,
            warning_id,
            reason=reason,
            expected_version=expected_version,
            to_state=WarningState.ACKNOWLEDGED,
            allowed_from={WarningState.OPEN},
        )

    def dismiss(
        self,
        context: RequestContext,
        warning_id: UUID,
        *,
        reason: str,
        expected_version: int,
    ) -> WarningRow:
        """Move open|acknowledged → dismissed with retained reason."""
        return self._transition(
            context,
            warning_id,
            reason=reason,
            expected_version=expected_version,
            to_state=WarningState.DISMISSED,
            allowed_from={WarningState.OPEN, WarningState.ACKNOWLEDGED},
        )

    def _transition(
        self,
        context: RequestContext,
        warning_id: UUID,
        *,
        reason: str,
        expected_version: int,
        to_state: str,
        allowed_from: set[str],
    ) -> WarningRow:
        """Shared acknowledge/dismiss path with version and state checks."""
        if not reason or not reason.strip():
            raise ValidationFailed("performance.error.reason_required")
        self.gate.require_staff_action(context, "warnings.manage")
        try:
            warning = WarningRow.objects.select_related("rule").get(
                id=warning_id, school_id=context.school_id
            )
        except WarningRow.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if warning.version != expected_version:
            raise VersionConflict("error.version_conflict")
        if warning.state not in allowed_from:
            raise StateConflict("performance.error.invalid_warning_state")
        now = self.clock.now()
        with transaction.atomic():
            from_state = warning.state
            warning.state = to_state
            warning.reason = reason
            warning.version = warning.version + 1
            warning.updated_at = now
            warning.save()
            WarningHistory.objects.create(
                id=uuid4(),
                warning=warning,
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                actor_id=context.actor_id,
                at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action=f"warning.{to_state}",
                    resource_id=warning.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"reason": reason, "version": warning.version},
                )
            )
        return warning
