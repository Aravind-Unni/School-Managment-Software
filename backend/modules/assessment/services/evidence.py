"""Bind quality-confirmed answer-sheet pages to a result."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import (
    Assessment,
    EvidenceBinding,
    Result,
)
from .authority import AuthorityGate
from .marks import EDITABLE_ASSESSMENT
from .wire import evidence_to_wire


@dataclass(frozen=True, slots=True)
class EvidenceService:
    """Bind ordered evidence pages via FilesPort.pin_evidence."""

    gate: AuthorityGate
    files: object
    platform: object
    clock: object

    def bind(
        self,
        context: RequestContext,
        *,
        result_id: UUID,
        expected_version: int,
        pages: list[dict],
    ) -> dict:
        """Replace working (unrevisioned) evidence bindings for a result.

        Unconfirmed files raise assessment.error.unconfirmed_evidence via
        FilesPort.pin_evidence. Does not handle: upload transport.
        """
        try:
            result = Result.objects.select_related("assessment").get(id=result_id)
        except Result.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        assessment = result.assessment
        if assessment.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if assessment.state not in EDITABLE_ASSESSMENT:
            raise StateConflict("assessment.error.invalid_transition")
        self.gate.require_assessment_action(context, action="marks.edit", assessment=assessment)
        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")
        if not pages:
            raise ValidationFailed("error.validation_failed")

        now = self.clock.now()
        created: list[EvidenceBinding] = []
        with transaction.atomic():
            locked_assessment = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked_assessment.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked = Result.objects.select_for_update().get(id=result.id)
            locked.evidence_bindings.filter(revision_id__isnull=True).delete()
            for page in pages:
                file_id = page["file_id"]
                canonical_version = page["canonical_version"]
                page_no = page["page_no"]
                binding_id = uuid.uuid4()
                ref = self.files.pin_evidence(context, file_id, canonical_version, binding_id)
                created.append(
                    EvidenceBinding.objects.create(
                        id=binding_id,
                        result=locked,
                        revision_id=None,
                        file_id=ref.file_id,
                        file_version=ref.version,
                        sha256=ref.sha256,
                        page_no=page_no,
                    )
                )
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["version", "updated_at"])
            locked_assessment.version += 1
            locked_assessment.updated_at = now
            locked_assessment.save(update_fields=["version", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.evidence_bound",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"pages": len(created)},
                )
            )
        refreshed_assessment = Assessment.objects.get(id=assessment.id)
        return {
            "bindings": [evidence_to_wire(b) for b in created],
            "version": refreshed_assessment.version,
        }

    def view(
        self,
        context: RequestContext,
        *,
        result_id: UUID,
        binding_id: UUID,
    ) -> dict:
        """Issue a short-lived read URL for one published evidence binding.

        Wrong-child / unrelated actors receive 404. Draft results never expose
        evidence to student or guardian scopes.
        """
        from datetime import timedelta
        from uuid import uuid4

        from contracts.evidence import ResourceGrant
        from contracts.scope import Relationship

        try:
            result = Result.objects.select_related("assessment").get(id=result_id)
        except Result.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if result.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        relationship = self.gate.require_evidence_view(
            context, student_id=result.student_id, school_id=result.school_id
        )
        if relationship in {Relationship.SELF, Relationship.GUARDIAN}:
            if result.status != "published":
                raise ObjectInaccessible("error.object_inaccessible")

        try:
            binding = EvidenceBinding.objects.get(id=binding_id, result=result)
        except EvidenceBinding.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc

        now = self.clock.now()
        grant = ResourceGrant(
            grant_id=uuid4(),
            school_id=result.school_id,
            actor_id=context.actor_id,
            action="evidence.view",
            resource_id=binding.file_id,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
        )
        read = self.files.issue_read(context, grant)
        revision_id = binding.revision_id or result.current_revision_id or result.id
        return {
            "read_url": read.read_url,
            "expires_at": read.expires_at.isoformat(),
            "file_id": str(binding.file_id),
            "version": binding.file_version,
            "revision_id": str(revision_id),
        }
