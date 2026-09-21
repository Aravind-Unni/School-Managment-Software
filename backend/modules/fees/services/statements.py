"""Statements, overdue list and daily collection reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.pagination import encode_cursor
from contracts.values import SCHOOL_TIMEZONE, school_date

from ..models import Allocation, Charge, Credit, Payment, RefundRecord, Reversal
from .authority import AuthorityGate
from .ledger import compute_balance
from .wire import balance_to_wire


@dataclass(frozen=True, slots=True)
class StatementService:
    """Read-side ledger views."""

    gate: AuthorityGate
    registry: object
    clock: object

    def get_statement(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None,
    ) -> dict:
        """Return ledger entries and totals for one student."""
        self.gate.require_statement_read(context, student_id)
        on = as_of or school_date(self.clock.now())
        student = self.registry.get_student(context, student_id)
        entries: list[dict] = []
        for charge in Charge.objects.filter(
            school_id=context.school_id, student_id=student_id
        ).order_by("posted_at"):
            entries.append(
                {
                    "entry_type": "charge",
                    "id": str(charge.id),
                    "amount_paise": charge.amount_paise,
                    "posted_at": charge.posted_at.isoformat(),
                    "description_key": charge.description_key or "fees.charge",
                    "related_id": None,
                    # What a cashier needs to take a payment against this charge.
                    "balance_paise": charge.balance_paise,
                    "due_date": charge.due_date.isoformat(),
                    "status": charge.status,
                }
            )
        for payment in Payment.objects.filter(
            school_id=context.school_id, student_id=student_id, reversed=False
        ).order_by("posted_at"):
            entries.append(
                {
                    "entry_type": "payment",
                    "id": str(payment.id),
                    "amount_paise": payment.amount_paise,
                    "posted_at": payment.posted_at.isoformat(),
                    "description_key": "fees.payment",
                    "related_id": None,
                }
            )
        for credit in Credit.objects.filter(
            school_id=context.school_id, student_id=student_id
        ).order_by("posted_at"):
            entries.append(
                {
                    "entry_type": "credit",
                    "id": str(credit.id),
                    "amount_paise": credit.amount_paise,
                    "posted_at": credit.posted_at.isoformat(),
                    "description_key": "fees.credit",
                    "related_id": str(credit.charge_id) if credit.charge_id else None,
                }
            )
        for refund in RefundRecord.objects.filter(
            school_id=context.school_id, student_id=student_id
        ).order_by("posted_at"):
            entries.append(
                {
                    "entry_type": "refund",
                    "id": str(refund.id),
                    "amount_paise": refund.amount_paise,
                    "posted_at": refund.posted_at.isoformat(),
                    "description_key": "fees.refund",
                    "related_id": None,
                }
            )
        for reversal in Reversal.objects.filter(
            school_id=context.school_id, payment__student_id=student_id
        ).order_by("posted_at"):
            entries.append(
                {
                    "entry_type": "reversal",
                    "id": str(reversal.id),
                    "amount_paise": reversal.payment.amount_paise,
                    "posted_at": reversal.posted_at.isoformat(),
                    "description_key": "fees.reversal",
                    "related_id": str(reversal.payment_id),
                }
            )
        for allocation in Allocation.objects.filter(
            school_id=context.school_id,
            payment__student_id=student_id,
            reversed=False,
        ).order_by("id"):
            entries.append(
                {
                    "entry_type": "allocation",
                    "id": str(allocation.id),
                    "amount_paise": allocation.amount_paise,
                    "posted_at": allocation.payment.posted_at.isoformat(),
                    "description_key": "fees.allocation",
                    "related_id": str(allocation.charge_id),
                }
            )
        entries.sort(key=lambda e: e["posted_at"])
        balance = compute_balance(school_id=context.school_id, student_id=student_id, as_of=on)
        wire = balance_to_wire(balance)
        return {
            "student_id": str(student_id),
            "as_of": on.isoformat(),
            "entries": entries,
            "totals": wire,
            "balance": wire,
            "student_display_name": student.display_name,
            "admission_no": student.admission_no,
        }

    def list_overdue(
        self,
        context: RequestContext,
        *,
        as_of: date | None,
        cursor: str | None,
    ) -> dict:
        """List open overdue charge balances for the school."""
        self.gate.require_staff_read(context)
        on = as_of or school_date(self.clock.now())
        qs = Charge.objects.filter(
            school_id=context.school_id, balance_paise__gt=0, due_date__lte=on
        ).order_by("due_date", "id")
        if cursor:
            qs = qs.filter(id__gt=UUID(cursor))
        page = list(qs[:50])
        items = []
        for charge in page:
            try:
                student = self.registry.get_student(context, charge.student_id)
                name = student.display_name
            except Exception:
                name = None
            items.append(
                {
                    "student_id": str(charge.student_id),
                    "charge_id": str(charge.id),
                    "amount_paise": charge.amount_paise,
                    "balance_paise": charge.balance_paise,
                    "due_date": charge.due_date.isoformat(),
                    "display_name": name,
                }
            )
        next_cursor = encode_cursor({"id": str(page[-1].id)}) if len(page) == 50 else None
        return {"items": items, "next_cursor": next_cursor}

    def daily_collections(self, context: RequestContext, collection_date: date) -> dict:
        """Sum non-reversed payments whose Asia/Kolkata civil date matches."""
        self.gate.require_staff_read(context)
        tz = ZoneInfo(SCHOOL_TIMEZONE)
        start = datetime(
            collection_date.year,
            collection_date.month,
            collection_date.day,
            tzinfo=tz,
        )
        end = start + timedelta(days=1)
        payments = Payment.objects.filter(
            school_id=context.school_id,
            reversed=False,
            posted_at__gte=start.astimezone(ZoneInfo("UTC")),
            posted_at__lt=end.astimezone(ZoneInfo("UTC")),
        )
        by_method: dict[str, int] = {}
        total = 0
        count = 0
        for payment in payments:
            by_method[payment.method] = by_method.get(payment.method, 0) + payment.amount_paise
            total += payment.amount_paise
            count += 1
        return {
            "collection_date": collection_date.isoformat(),
            "total_paise": total,
            "payment_count": count,
            "by_method": by_method,
        }

    def get_balance(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None,
    ):
        """FeesPort.get_balance with statement-read authorization."""
        self.gate.require_statement_read(context, student_id)
        on = as_of or school_date(self.clock.now())
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return compute_balance(school_id=context.school_id, student_id=student_id, as_of=on)
