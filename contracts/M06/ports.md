# M06 service ports — FROZEN under school-contracts-v7

What M06 **provides** and what it **consumes**. Dependencies are Protocols from
`backend/contracts/ports.py`, bound to deterministic fakes in standalone.

---

## 1. Provided: `PerformancePort`

```python
@runtime_checkable
class PerformancePort(Protocol):
    """Dashboards, warnings and interventions. Owned by M06."""

    def get_dashboard(
        self,
        context: RequestContext,
        subject_id: UUID | None,
        scope: str,
        window: str,
    ) -> DashboardDTO:
        """Return metrics, warnings, source freshness and definition versions.

        Cohort distributions hide identifiable peers. Topic metrics without
        tagged item data return status=insufficient_data.
        """

    def get_interventions(
        self,
        context: RequestContext,
        student_id: UUID,
        cursor: str | None = None,
    ) -> InterventionPage:
        """Return interventions visible to the actor for one pupil."""
```

DTO shapes match `schemas/dtos.schema.json`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `performance.read` | Dashboard / own-child academic summaries |
| `warnings.manage` | Create rules; acknowledge/dismiss warnings |
| `interventions.manage` | Create/update interventions |
| `meetings.record` | Record parent–teacher meetings |
| `observations.read_sensitive` | Restricted behavior/participation notes |

### `RegistryPort` — M02 (fake)

`get_student`, `get_roster`, `get_relationships`, `get_teaching_assignments`.

### `AssessmentPort` — M05 (FakeAssessment in standalone)

`get_published_results`, `get_assignment_summary`. Draft never returned to
student/guardian scopes.

### `AttendancePort` — M04 (FakeAttendance in standalone)

`get_summary` with period unit; incomplete unmarked distinct from low percentage.

### `PlatformPort` — M14 (test adapter)

`record_audit`, `append_event`, `enqueue` for `performance.rebuild_projections`
(requires real broker/worker).

### `ClockPort`

Every timestamp.

---

## 3. Workflow (module-local)

1. Seed metric definitions + warning rules (versioned).
2. Build/rebuild projections from Assessment + Attendance reads and events.
3. Evaluate rules → open warnings (deduped) with source_refs.
4. Staff acknowledge/dismiss; create interventions/meetings/resources.
5. Dashboard reads projections + open warnings; guardian export omits sensitive observations.
