"""Permission codes owned by M09. Must match ModuleRegistration and Access rules."""

PERMISSION_CODES: tuple[str, ...] = (
    "library.catalogue.manage",
    "library.issue",
    "library.return",
    "library.renew",
    "library.read_overdues",
    "library.read_own",
)
