"""Initial harness audit/outbox tables."""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Creates harness_audit_record and harness_outbox_event."""

    initial = True
    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="HarnessAuditRecord",
            fields=[
                ("audit_id", models.UUIDField(primary_key=True, serialize=False)),
                ("school_id", models.UUIDField(db_index=True)),
                ("actor_id", models.UUIDField()),
                ("action", models.CharField(max_length=128)),
                ("resource_id", models.UUIDField(db_index=True)),
                ("occurred_at", models.DateTimeField()),
                ("request_id", models.CharField(db_index=True, max_length=64)),
                ("before", models.JSONField(default=dict)),
                ("after", models.JSONField(default=dict)),
            ],
            options={"db_table": "harness_audit_record"},
        ),
        migrations.CreateModel(
            name="HarnessOutboxEvent",
            fields=[
                ("event_id", models.UUIDField(primary_key=True, serialize=False)),
                ("school_id", models.UUIDField(db_index=True)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("occurred_at", models.DateTimeField()),
                ("aggregate_id", models.UUIDField(db_index=True)),
                ("aggregate_version", models.IntegerField()),
                ("payload", models.JSONField(default=dict)),
                ("envelope_version", models.IntegerField()),
                ("published_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "harness_outbox_event"},
        ),
        migrations.AddIndex(
            model_name="harnessauditrecord",
            index=models.Index(
                fields=["school_id", "action"], name="harness_aud_school__0a1b2c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="harnessoutboxevent",
            index=models.Index(
                fields=["school_id", "event_type"], name="harness_out_school__3d4e5f_idx"
            ),
        ),
    ]
