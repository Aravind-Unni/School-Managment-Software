"""URL patterns for M09, mounted under /api/v1/."""

from __future__ import annotations

from django.urls import path

from .api.views import (
    BorrowerLoansView,
    CatalogueImportView,
    CopyAdjustView,
    CopyCollectionView,
    LoanCollectionView,
    LoanRenewView,
    LoanReturnView,
    OverdueCollectionView,
    TitleAvailabilityView,
    TitleCollectionView,
)

app_name = "library"

urlpatterns = [
    path("library/titles", TitleCollectionView.as_view(), name="title-collection"),
    path(
        "library/titles/<uuid:title_id>/availability",
        TitleAvailabilityView.as_view(),
        name="title-availability",
    ),
    path("library/copies", CopyCollectionView.as_view(), name="copy-collection"),
    path(
        "library/copies/<uuid:copy_id>/adjust",
        CopyAdjustView.as_view(),
        name="copy-adjust",
    ),
    path("library/loans", LoanCollectionView.as_view(), name="loan-collection"),
    path(
        "library/loans/<uuid:loan_id>/return",
        LoanReturnView.as_view(),
        name="loan-return",
    ),
    path(
        "library/loans/<uuid:loan_id>/renew",
        LoanRenewView.as_view(),
        name="loan-renew",
    ),
    path(
        "library/borrowers/<uuid:person_id>/loans",
        BorrowerLoansView.as_view(),
        name="borrower-loans",
    ),
    path("library/overdues", OverdueCollectionView.as_view(), name="overdues"),
    path(
        "library/catalogue-imports",
        CatalogueImportView.as_view(),
        name="catalogue-imports",
    ),
]
