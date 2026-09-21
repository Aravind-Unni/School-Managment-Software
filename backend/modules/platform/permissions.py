"""Permission codes owned by M14. Must match ModuleRegistration and Access rules."""

PERMISSION_CODES: tuple[str, ...] = (
    "platform.read_health",
    "jobs.read",
    "jobs.retry",
    "audit.read",
    "backups.manage",
)
