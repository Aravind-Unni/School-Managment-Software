"""Catalogue import with duplicate ISBN/accession review."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from contracts.identity import RequestContext

from ..models import Copy, CopyState, Title
from .authority import AuthorityGate


@dataclass(frozen=True, slots=True)
class ImportService:
    """Import title/copy rows; do not auto-merge duplicates."""

    gate: AuthorityGate
    platform: object
    clock: object

    def import_rows(self, context: RequestContext, rows: list[dict]) -> dict:
        """Create clean rows; return review items for accession/ISBN collisions."""
        self.gate.require_action(context, "library.catalogue.manage")
        created_titles: list[str] = []
        created_copies: list[str] = []
        review_items: list[dict] = []

        with transaction.atomic():
            for index, row in enumerate(rows):
                accession = str(row["accession_no"]).strip()
                isbn = row.get("isbn")
                isbn = isbn.strip() if isinstance(isbn, str) and isbn.strip() else None

                if Copy.objects.filter(
                    school_id=context.school_id, accession_no=accession
                ).exists():
                    review_items.append(
                        {
                            "row_index": index,
                            "issue": "duplicate_accession",
                            "accession_no": accession,
                            "isbn": isbn,
                        }
                    )
                    continue

                if (
                    isbn
                    and Title.objects.filter(school_id=context.school_id, isbn=isbn).exists()
                ):
                    review_items.append(
                        {
                            "row_index": index,
                            "issue": "duplicate_isbn_review",
                            "accession_no": accession,
                            "isbn": isbn,
                        }
                    )
                    # Still create as a separate title/copy; ISBN is not unique.
                    # Review flag only — do not skip creation for ISBN alone.

                title = Title.objects.create(
                    school_id=context.school_id,
                    isbn=isbn,
                    name=str(row["name"]).strip(),
                    author=str(row["author"]).strip(),
                    language=str(row["language"]).strip(),
                    version=1,
                )
                created_titles.append(str(title.id))
                try:
                    copy = Copy.objects.create(
                        school_id=context.school_id,
                        title_id=title.id,
                        accession_no=accession,
                        state=CopyState.AVAILABLE,
                        version=1,
                    )
                except IntegrityError:
                    review_items.append(
                        {
                            "row_index": index,
                            "issue": "duplicate_accession",
                            "accession_no": accession,
                            "isbn": isbn,
                        }
                    )
                    continue
                created_copies.append(str(copy.id))

        return {
            "created_title_ids": created_titles,
            "created_copy_ids": created_copies,
            "review_items": review_items,
        }
