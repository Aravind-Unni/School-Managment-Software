"""The fixed M-id to slug mapping, straight from the B00 specification.

This is DATA. A module is not "installed" by editing settings; the host reads
MODULE_ID, looks the slug up here, and imports exactly one registration.

M00 is the placeholder demo app. It is not one of the fourteen business modules
and owns no business domain; it exists to prove the runner and the test suites.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Authoritative id -> slug map. Adding a row is a specification change.
MODULE_SLUGS: dict[str, str] = {
    "M00": "demo",
    "M01": "access",
    "M02": "registry",
    "M03": "timetable",
    "M04": "attendance",
    "M05": "assessment",
    "M06": "performance",
    "M07": "fees",
    "M08": "transport",
    "M09": "library",
    "M10": "alumni",
    "M11": "communications",
    "M12": "files",
    "M13": "exchange",
    "M14": "platform",
}

#: The fourteen business modules, excluding the M00 placeholder.
BUSINESS_MODULE_IDS: tuple[str, ...] = tuple(
    module_id for module_id in sorted(MODULE_SLUGS) if module_id != "M00"
)


@dataclass(frozen=True, slots=True)
class ModuleAddress:
    """Where a module's code lives, derived from its id."""

    id: str
    slug: str

    @property
    def django_app(self) -> str:
        """Return the dotted Django app path for this module."""
        return f"modules.{self.slug}"

    @property
    def registration_path(self) -> str:
        """Return the dotted path to the module's REGISTRATION object."""
        return f"modules.{self.slug}.registration"

    @property
    def frontend_feature_dir(self) -> str:
        """Return the frontend feature directory for this module."""
        return f"frontend/src/features/{self.slug}"

    @property
    def contract_dir(self) -> str:
        """Return the contracts directory for this module."""
        return f"contracts/{self.id}"


def address_for(module_id: str) -> ModuleAddress:
    """Return the ModuleAddress for an id such as ``"M04"``.

    Raises KeyError with the valid set listed, because a typo'd MODULE_ID is the
    single most common developer mistake with this runner.
    """
    normalised = module_id.strip().upper()
    if normalised not in MODULE_SLUGS:
        raise KeyError(
            f"unknown MODULE_ID {module_id!r}; valid ids are {', '.join(sorted(MODULE_SLUGS))}"
        )
    return ModuleAddress(id=normalised, slug=MODULE_SLUGS[normalised])


def slug_for(module_id: str) -> str:
    """Return just the slug for an id."""
    return address_for(module_id).slug


def id_for_slug(slug: str) -> str:
    """Return the id owning a slug.

    Raises KeyError when the slug is not a known module, which is how the
    architecture check catches a stray directory under backend/modules/.
    """
    for module_id, candidate in MODULE_SLUGS.items():
        if candidate == slug:
            return module_id
    raise KeyError(f"unknown module slug {slug!r}")
